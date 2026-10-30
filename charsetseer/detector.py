# -*- coding: utf-8 -*-
"""编码检测引擎。

检测流程遵循"证据强度由高到低、逐级收敛"的原则：

1. **BOM 指纹** —— 有 BOM 就是硬证据，直接定案。
2. **纯 ASCII** —— 无歧义，UTF-8 兼容。
3. **UTF-8 严格验证** —— UTF-8 有自校验特性，随机字节能合法解码的概率极低。
4. **多候选语言学打分** —— 对每个候选编码严格解码，再用字符分布与
   汉字常用度给结果"像不像人话"打分。

最后一步是 CharsetSeer 相对朴素方案的核心差异：它不仅问"能不能解"，
还追问"解出来像不像这门语言的正常文本"。
"""

from __future__ import annotations

import math
import unicodedata
from typing import Dict, List, Optional, Sequence, Tuple

from .models import Candidate, Detection
from .tables import (
    ALLOWED_CONTROLS,
    ARABIC_HIGH,
    ARABIC_LOW,
    BOM_SIGNATURES,
    CANDIDATES,
    CJK_COMPAT_HIGH,
    CJK_COMPAT_LOW,
    CJK_EXT_A_HIGH,
    CJK_EXT_A_LOW,
    CJK_PUNCT,
    CJK_UNIFIED_HIGH,
    CJK_UNIFIED_LOW,
    CYRILLIC_HIGH,
    CYRILLIC_LOW,
    DBCS_LEAD_RANGES,
    DBCS_TRAIL_LOW_ALLOWED,
    GREEK_HIGH,
    GREEK_LOW,
    HANGUL_HIGH,
    HANGUL_LOW,
    HEBREW_HIGH,
    HEBREW_LOW,
    JAMO_HIGH,
    JAMO_LOW,
    KANA_HIGH,
    KANA_LOW,
    PRIVATE_USE_HIGH,
    PRIVATE_USE_LOW,
    REPLACEMENT_CHAR,
    SCORE_WEIGHTS,
    SCRIPT_AFFINITY,
    SCRIPT_TARGETS,
    MIN_TARGET_RATIO,
    SPARSE_PENALTY,
    ZH_TOP_FREQ,
    ZH_TOP_FREQ_BOOST,
    ZH_EXPECTED_TOP_RATIO,
    CODEC_PRIOR,
    RU_TOP_FREQ,
    RU_FREQ_BOOST,
    RU_EXPECTED_TOP_RATIO,
    SPECIAL_CHARS,
    SPECIAL_CHARS_BOOST,
    PREFERENCE_ORDER,
    SINGLE_BYTE_CODECS,
    SINGLE_BYTE_PENALTY,
    HANZI_FAMILIARITY_BOOST,
    THAI_HIGH,
    THAI_LOW,
    common_hanzi,
)

#: 检测时读取的最大样本字节数。编码判别不需要全文，前 256 KB 足够
#: 代表整份文件的语言特征，同时保证大目录下扫描依然迅速。
SAMPLE_LIMIT = 256 * 1024

#: 文本预览长度
PREVIEW_LIMIT = 200


def classify_char(ch: str) -> str:
    """把单个字符归入语言学类别。

    类别决定了它在打分表中的权重：正常文字加分，控制符 / 私用区 /
    替换字符等"不该出现在正常文本里"的字符重罚。
    """
    code = ord(ch)

    if code in ALLOWED_CONTROLS:
        return "space"
    if code == REPLACEMENT_CHAR:
        return "replacement"
    if code < 0x20 or code == 0x7F or 0x80 <= code <= 0x9F:
        return "control"
    if PRIVATE_USE_LOW <= code <= PRIVATE_USE_HIGH:
        return "private"

    if CJK_UNIFIED_LOW <= code <= CJK_UNIFIED_HIGH:
        return "cjk"
    if CJK_EXT_A_LOW <= code <= CJK_EXT_A_HIGH:
        return "rare_cjk"
    if CJK_COMPAT_LOW <= code <= CJK_COMPAT_HIGH:
        return "rare_cjk"
    if KANA_LOW <= code <= KANA_HIGH:
        return "kana"
    if HANGUL_LOW <= code <= HANGUL_HIGH:
        return "hangul"
    if JAMO_LOW <= code <= JAMO_HIGH:
        return "jamo"
    if CYRILLIC_LOW <= code <= CYRILLIC_HIGH:
        return "cyrillic"
    if GREEK_LOW <= code <= GREEK_HIGH:
        return "greek"
    if THAI_LOW <= code <= THAI_HIGH:
        return "thai"
    if ARABIC_LOW <= code <= ARABIC_HIGH:
        return "arabic"
    if HEBREW_LOW <= code <= HEBREW_HIGH:
        return "hebrew"

    if ch in CJK_PUNCT:
        return "cjk_punct"
    if code < 0x80:
        if ch.isspace():
            return "space"
        if ch.isdigit():
            return "digit"
        if ch.isalpha():
            return "latin"
        return "punct"

    if ch.isspace():
        return "space"
    if unicodedata.category(ch) == "Cn":
        return "unassigned"
    if ch.isalpha():
        return "latin"
    if ch.isdigit():
        return "digit"
    return "symbol"


def _byte_shape_ok(data: bytes, codec_name: str) -> bool:
    """用双字节编码的字节结构特征做快速排除。

    例如 EUC-JP / EUC-KR 的次字节必须 >= 0xA1，一旦样本中出现
    ``0xA1..0xFE`` 后紧跟 ``0x40..0x7E`` 的字节对，即可判定不是 EUC 系列。
    这一步不依赖解码，可在毫秒级排除大量候选。
    """
    ranges = DBCS_LEAD_RANGES.get(codec_name)
    if ranges is None:
        return True
    trail_low_allowed = DBCS_TRAIL_LOW_ALLOWED.get(codec_name, True)

    i = 0
    n = len(data)
    while i < n:
        byte_value = data[i]
        is_lead = any(lo <= byte_value <= hi for lo, hi in ranges)
        if not is_lead:
            i += 1
            continue
        if i + 1 >= n:
            return False
        trail = data[i + 1]
        if not trail_low_allowed and 0x40 <= trail <= 0x7E:
            return False
        i += 2
    return True


def infer_script(text: str) -> str:
    """根据解码结果推断文本的语言归属（用于 ``auto`` 型编码）。

    与 :func:`guess_language` 的区别：这个结果会**参与打分**，因此阈值
    取 4 —— 短样本同样需要被正确归类，而猜测错误的代价由后续加权吸收。
    """
    if not text:
        return "la"
    counts: Dict[str, int] = {}
    for ch in text[:8192]:
        category = classify_char(ch)
        counts[category] = counts.get(category, 0) + 1

    # 假名与韩文音节是"独有信号"：简体中文文本不会出现假名，
    # 中日文共用的汉字则无法区分。因此只要出现哪怕两个假名/韩文音节，
    # 就足以推翻"这是中文"的判断 —— 阈值取 2 而非 4，是为了照顾短文本。
    if counts.get("kana", 0) >= 2:
        return "ja"
    if counts.get("hangul", 0) + counts.get("jamo", 0) >= 2:
        return "ko"
    if counts.get("cyrillic", 0) >= 4:
        return "ru"
    if counts.get("cjk", 0) >= 4:
        return "zh-hans"
    if counts.get("arabic", 0) >= 4:
        return "ar"
    if counts.get("hebrew", 0) >= 4:
        return "he"
    if counts.get("greek", 0) >= 4:
        return "el"
    return "la"


def resolve_script(script: str, text: str) -> str:
    """把 ``auto`` 解析为实际语言归属。"""
    if script == "auto":
        return infer_script(text)
    return script


def score_text(text: str, script: str, codec_name: str) -> Tuple[float, Dict[str, int], float]:
    """给解码结果打"像不像人话"的分。

    打分分两遍进行：

    **第一遍**统计字符类别分布，据此判断"主导文字是否成立" ——
    一个自称俄语的编码如果只解出零星几个西里尔字母、其余全是 ASCII，
    那它几乎肯定是把西欧重音字母误读成了西里尔。

    **第二遍**才是真正的加权求和，并且会依据第一遍的结论削弱
    不成立的语言契合度奖励。

    Returns:
        (平均得分, 各类别计数, 汉字常用度)
    """
    affinity = SCRIPT_AFFINITY.get(script, {})
    common = common_hanzi(codec_name)
    counts: Dict[str, int] = {}
    categories: List[str] = []
    cjk_total = 0
    cjk_common = 0
    cjk_top_freq = 0
    cyrillic_total = 0
    cyrillic_top = 0

    special_chars, special_weight = SPECIAL_CHARS.get(codec_name, (None, 0.0))
    special_hits = 0

    for ch in text:
        category = classify_char(ch)
        categories.append(category)
        counts[category] = counts.get(category, 0) + 1
        if special_chars and ch in special_chars:
            special_hits += 1
        if category == "cjk":
            cjk_total += 1
            if ch in common:
                cjk_common += 1
            if ch in ZH_TOP_FREQ:
                cjk_top_freq += 1
        elif category == "cyrillic":
            cyrillic_total += 1
            if ch in RU_TOP_FREQ:
                cyrillic_top += 1

    length = max(1, len(text))

    # ---- 主导文字一致性检查 ----------------------------------------------
    targets = SCRIPT_TARGETS.get(script, ())
    if targets:
        target_ratio = sum(counts.get(t, 0) for t in targets) / length
    else:
        target_ratio = 1.0
    sparse = bool(targets) and target_ratio < MIN_TARGET_RATIO

    # ---- 加权求和 ----------------------------------------------------------
    total_score = 0.0
    for category in categories:
        weight = SCORE_WEIGHTS.get(category, 0.0)
        boost = affinity.get(category, 0.0)
        if sparse and category in targets:
            # 零星出现的目标文字不足以支撑语言判定，取消契合度奖励
            boost = 0.0
        if weight > 0:
            weight *= (1.0 + boost)
        else:
            weight *= (1.0 - max(0.0, boost)) if boost > 0 else (1.0 + abs(boost))
        total_score += weight

    average = total_score / length
    familiarity = (cjk_common / cjk_total) if cjk_total else 0.0

    cjk_ratio = cjk_total / length

    # 汉字常用度加成：区分"真中文"与"乱码汉字"的决定性证据。
    if cjk_total > 0 and common:
        average += HANZI_FAMILIARITY_BOOST * (familiarity - 0.45) * cjk_ratio

    # 高频字加成：最强的一条证据。
    #
    # 日语文本同样含汉字，但日语有自己的强特征 —— 假名。当假名占比足够
    # 时跳过这条判据，避免用中文字频去误判日文。
    if cjk_total >= 1:
        kana_ratio = counts.get("kana", 0) / length
        if not (script == "ja" and kana_ratio >= 0.10):
            top_ratio = cjk_top_freq / cjk_total
            # 样本量很小时（例如只有两三个汉字）统计不可靠，按数量线性
            # 缩放置信度，既不放弃这条强判据，也不让它过度左右结果。
            scale = min(1.0, cjk_total / 8.0)
            average += ZH_TOP_FREQ_BOOST * (top_ratio - ZH_EXPECTED_TOP_RATIO) * cjk_ratio * scale

    # 专属字符加成：只有该编码才能解出的字符，是最直接的身份证据
    if special_hits:
        average += SPECIAL_CHARS_BOOST * (special_hits / length) * special_weight

    # 俄语字母频率加成：区分 cp1251 / koi8-r 这类"都能解出西里尔"的编码
    if cyrillic_total >= 12:
        top_ratio = cyrillic_top / cyrillic_total
        cyrillic_ratio = cyrillic_total / length
        average += RU_FREQ_BOOST * (top_ratio - RU_EXPECTED_TOP_RATIO) * cyrillic_ratio

    # 稀疏惩罚：目标文字只是零星出现时整体降权
    if sparse:
        average *= SPARSE_PENALTY

    # 单字节编码几乎总能解码成功，必须靠更强的语言学证据才能胜出
    if codec_name in SINGLE_BYTE_CODECS:
        average *= SINGLE_BYTE_PENALTY

    # 先验加成放在最后：它是"证据同等时"的裁决项，不应被前面的
    # 惩罚系数缩放掉。
    average += CODEC_PRIOR.get(codec_name, 0.0)

    return average, counts, familiarity


def _confidence_from_scores(scores: Sequence[Tuple[str, float]]) -> float:
    """由候选分数分布推导置信度。

    同时考虑"绝对质量"与"领先幅度"：

    - 领先幅度越大，越确信（用 tanh 平滑映射到 0.5 - 1.0）
    - 最高分本身若为负（说明所有候选都不像），整体置信度下调
    """
    if not scores:
        return 0.0
    ordered = sorted(scores, key=lambda item: item[1], reverse=True)
    best = ordered[0][1]
    second = ordered[1][1] if len(ordered) > 1 else best - 1.0

    gap = best - second
    margin = 0.5 + 0.5 * math.tanh(gap / 1.6)

    # 绝对质量因子：best <= 0 表示连最优候选都很糟糕
    quality = 1.0 / (1.0 + math.exp(-(best - 0.2) * 2.2))
    confidence = margin * (0.45 + 0.55 * quality)
    return max(0.05, min(1.0, confidence))


def _is_pure_ascii(data: bytes) -> bool:
    """判断是否为纯 ASCII 数据。"""
    return all(byte_value < 0x80 for byte_value in data)


def _match_bom(data: bytes) -> Optional[str]:
    """匹配 BOM 签名，返回声明的编码。"""
    for signature, encoding in BOM_SIGNATURES:
        if data.startswith(signature):
            return encoding
    return None


def _decode_strict(data: bytes, codec_name: str) -> Optional[str]:
    """严格解码，失败返回 ``None``。"""
    try:
        return data.decode(codec_name)
    except (UnicodeDecodeError, LookupError):
        return None


def detect_bytes(data: bytes, explain: bool = False) -> Tuple[Detection, List[Candidate]]:
    """检测一段字节的编码。

    Args:
        data: 原始字节。
        explain: 是否保留全部候选明细（用于 ``--explain``）。

    Returns:
        (检测结论, 候选明细列表)
    """
    if not data:
        return (
            Detection(
                encoding="utf-8",
                confidence=0.2,
                language="unknown",
                score=0.0,
                byte_length=0,
                text_preview="",
            ),
            [],
        )

    sample = data[:SAMPLE_LIMIT]
    byte_length = len(data)
    candidates: List[Candidate] = []

    # ---- 阶段 1：BOM 指纹 -------------------------------------------------
    bom_encoding = _match_bom(sample)
    if bom_encoding:
        text = _decode_strict(sample, bom_encoding) or ""
        return (
            Detection(
                encoding=bom_encoding,
                confidence=1.0,
                language=guess_language(text),
                has_bom=True,
                bom_encoding=bom_encoding,
                score=0.0,
                byte_length=byte_length,
                text_preview=text[:PREVIEW_LIMIT],
            ),
            [],
        )

    # ---- 阶段 2：纯 ASCII -------------------------------------------------
    if _is_pure_ascii(sample):
        return (
            Detection(
                encoding="ascii",
                confidence=0.99,
                language="en",
                has_bom=False,
                score=0.0,
                byte_length=byte_length,
                text_preview=sample[:PREVIEW_LIMIT].decode("ascii", "replace"),
            ),
            [],
        )

    # ---- 阶段 3 & 4：候选解码 + 语言学打分 --------------------------------
    scored: List[Tuple[str, float]] = []
    for codec_name, script in CANDIDATES:
        if not _byte_shape_ok(sample, codec_name):
            candidates.append(
                Candidate(
                    encoding=codec_name,
                    score=float("-inf"),
                    confidence=0.0,
                    language=script,
                    decodable=False,
                )
            )
            continue

        text = _decode_strict(sample, codec_name)
        if text is None:
            candidates.append(
                Candidate(
                    encoding=codec_name,
                    score=float("-inf"),
                    confidence=0.0,
                    language=script,
                    decodable=False,
                )
            )
            continue

        # auto 型编码（UTF-8）：先看清里面装的是什么语言，再按该语言打分
        effective_script = resolve_script(script, text)
        average, counts, familiarity = score_text(text, effective_script, codec_name)

        # UTF-8 自校验加成：能严格解码且含多字节序列，本身就是强证据
        if codec_name == "utf-8" and any(byte_value >= 0x80 for byte_value in sample):
            multibyte = sum(1 for byte_value in sample if byte_value >= 0xC0)
            if multibyte:
                average += 1.2

        scored.append((codec_name, average))
        candidates.append(
            Candidate(
                encoding=codec_name,
                score=average,
                confidence=0.0,
                language=script,
                decodable=True,
                category_counts=counts,
                hanzi_familiarity=familiarity,
            )
        )

    if not scored:
        # 所有候选都无法解码：退化到 latin-1（永不失败）并给出低置信度
        text = sample.decode("latin-1")
        return (
            Detection(
                encoding="latin-1",
                confidence=0.1,
                language="unknown",
                score=0.0,
                byte_length=byte_length,
                text_preview=text[:PREVIEW_LIMIT],
            ),
            candidates,
        )

    def _preference(name: str) -> int:
        """同分择优：越通用的编码名排越前。"""
        try:
            return PREFERENCE_ORDER.index(name)
        except ValueError:
            return len(PREFERENCE_ORDER)

    ordered_scored = sorted(scored, key=lambda item: (-item[1], _preference(item[0])))
    confidence = _confidence_from_scores(ordered_scored)
    best_name = ordered_scored[0][0]
    best_score = ordered_scored[0][1]
    script_of_best = dict(CANDIDATES).get(best_name, "unknown")
    text = _decode_strict(sample, best_name) or ""

    for candidate in candidates:
        if candidate.encoding == best_name:
            object.__setattr__(candidate, "confidence", confidence)
            break

    detection = Detection(
        encoding=best_name,
        confidence=confidence,
        language=guess_language(text, script_of_best),
        has_bom=False,
        score=best_score,
        byte_length=byte_length,
        text_preview=text[:PREVIEW_LIMIT],
    )
    if not explain:
        candidates = []
    return detection, candidates


def guess_language(text: str, hint: str = "unknown") -> str:
    """根据解码结果的字符构成推测语言归属。

    仅用于展示与归档，不影响编码判定本身。
    """
    if not text:
        return hint if hint != "any" else "unknown"

    counts: Dict[str, int] = {}
    for ch in text[:4096]:
        category = classify_char(ch)
        counts[category] = counts.get(category, 0) + 1

    kana = counts.get("kana", 0)
    hangul = counts.get("hangul", 0) + counts.get("jamo", 0)
    cyrillic = counts.get("cyrillic", 0)
    cjk = counts.get("cjk", 0)

    # 阈值取 4 而非更大的值：短文件（一行配置、一句日志）同样需要
    # 给出语言提示，过高的阈值会让绝大多数短样本都退化成 en。
    # 假名/韩文音节是独有信号，出现两个即可定性（见 infer_script 注释）
    if kana >= 2:
        return "ja"
    if hangul >= 2:
        return "ko"
    if cyrillic >= 4:
        return "ru"
    if cjk >= 4:
        if hint == "zh-hant":
            return "zh-hant"
        if hint == "zh-hans":
            return "zh-hans"
        # 用标点做简繁倾向的弱判断，仅作提示，不作为编码判据
        traditional_markers = sum(text[:4096].count(ch) for ch in "「」『』")
        simplified_markers = sum(text[:4096].count(ch) for ch in "“”‘’")
        if traditional_markers > simplified_markers:
            return "zh-hant"
        return "zh-hans"
    return "en"


def detect(data: bytes) -> Detection:
    """检测字节串编码，返回结论对象。"""
    return detect_bytes(data)[0]


def detect_file(path: str, explain: bool = False) -> Tuple[Detection, List[Candidate]]:
    """检测单个文件的编码。"""
    with open(path, "rb") as handle:
        data = handle.read()
    return detect_bytes(data, explain=explain)
