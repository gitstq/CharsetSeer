# -*- coding: utf-8 -*-
"""乱码（Mojibake）检测与修复。

乱码的本质是**编码被误读**：一段字节本来是 A 编码，却被当成 B 编码解码，
于是屏幕上出现"鏂囧瓧""æ–‡å—""ÖÐÎÄ""Ã©"这类鬼画符。

只要误读过程没有丢失字节，乱码就是**可逆**的：

    text.encode(误用的编码) -> bytes.decode(真正的编码)

难点在于：如何自动判定当初误用了哪个编码、真实编码又是什么，以及如何
确认修复结果确实"更像人话"。CharsetSeer 的做法是枚举所有合理的
(误用编码, 真实编码) 组合，用与检测引擎同一套语言学打分函数挑最优解，
并支持多轮修复以处理"被反复错误转码"的文本。
"""

from __future__ import annotations

import re
from typing import FrozenSet, List, Optional, Sequence, Tuple

from .detector import classify_char, score_text
from .models import RepairResult
from .tables import CJK_UNIFIED_HIGH, CJK_UNIFIED_LOW, ZH_TOP_FREQ, common_hanzi

#: 可能被"误用"的编码（即当初拿去解码的那个错误编码）
WRONG_CANDIDATES: Tuple[str, ...] = (
    "cp1252",
    "latin-1",
    "gb18030",
    "big5",
    "shift_jis",
    "euc-kr",
    "cp1251",
    "koi8-r",
    "mac_roman",
)

#: 可能的"真实"编码
TRUE_CANDIDATES: Tuple[str, ...] = (
    "utf-8",
    "gb18030",
    "big5",
    "shift_jis",
    "euc-jp",
    "euc-kr",
)

#: 单字节编码误解 UTF-8 后高频出现的"特征字符"
MOJIBAKE_HINT_CHARS = frozenset(
    "ÃÂâ€™“”–—ØÐÎÑÖÕÔÓÒÈÉÊËÌÍÎÏðñòóôõöøùúûüýÿ€"
    "æçëïðß÷¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿"
)

#: 典型乱码片段正则：latin1 系误解 UTF-8 的指纹
_MOJIBAKE_PATTERNS = (
    re.compile(r"Ã[\u0080-\u00bf]"),          # Ã© Ã¨ Ã¼ ...
    re.compile(r"â€[\u2018\u2019\u201c\u201d\u2013\u2014]", re.UNICODE),  # â€™ â€œ
    re.compile(r"â€"),                         # 兜底
    re.compile(r"[\u00d0\u00d1][\u0080-\u00bf]"),  # Ð... Ñ... （GBK 误 latin1）
    re.compile(r"Î[\u0080-\u00bf]"),           # Î... （GBK 误 latin1）
    re.compile(r"æ[\u0080-\u009f][\u0080-\u00bf]"),  # æ–‡ （日文/中文 UTF-8 误 latin1）
    re.compile(r"[\u00c0-\u00ff]{4,}"),        # 连续 4 个以上重音字母
)

#: 分数提升超过该阈值才认为修复有效，避免"越修越糟"
MIN_IMPROVEMENT = 0.35

#: 最大修复轮数（处理被反复错误转码的文本）
MAX_ROUNDS = 3


_COMMON_UNION_CACHE: Optional[FrozenSet[str]] = None


def _common_union() -> FrozenSet[str]:
    """GB2312 一级字库与 Big5 常用字的并集（惰性缓存）。"""
    global _COMMON_UNION_CACHE
    if _COMMON_UNION_CACHE is None:
        _COMMON_UNION_CACHE = common_hanzi("utf-8")
    return _COMMON_UNION_CACHE


def naturalness(text: str) -> float:
    """语言中立的"文本自然度"评分（约 -2.0 ~ 1.0，越高越像正常文本）。

    为什么不能直接用检测引擎的 :func:`~charsetseer.detector.score_text`？
    因为那套权重是为**区分编码**设计的：汉字权重远高于拉丁字母 ——
    毕竟"能解出汉字"是区分 GBK 与 ASCII 的关键特征。

    但修复场景要比较的是**不同语言的正常文本**："Café déjà vu" 与
    "Caf泰 d泰j淌 vu" 谁更正常？此时再沿用汉字高权重，就会系统性地
    偏爱任何"能解出汉字"的错误修复。

    自然度只问两件事：

    1. 字符里有多少是"不该出现的"（控制符、替换字符、私用区、罕用汉字）
    2. 其余字符里有多少属于各自语言的常见字

    它不预设任何语言偏好，因此对中文、法文、俄文一视同仁。
    """
    if not text:
        return 0.0

    common_union = _common_union()
    good = 0
    bad = 0
    rare = 0

    for ch in text:
        category = classify_char(ch)
        if category in ("control", "replacement", "private", "unassigned", "rare_cjk"):
            bad += 1
            continue
        if category == "cjk":
            if ch in ZH_TOP_FREQ:
                good += 1
            elif ch in common_union:
                # 不在超高频表，但仍属于 GB2312 一级字库 / Big5 常用字 ——
                # 正常文本里的普通用字，不能算作乱码特征。
                #
                # 没有这层兜底，"编码检测工具" 这类常用但非超高频的字
                # 会被误判成乱码汉字，导致修复越修越糟。
                good += 1
            else:
                # 罕用汉字：正常文本极少出现，乱码却大量产生
                rare += 1
            continue
        good += 1

    total = max(1, len(text))
    return (
        good / total
        - 1.5 * (rare / total)
        - 2.0 * (bad / total)
    )


def _text_score(text: str) -> float:
    """给一段文本打"正常度"分，用于比较修复前后的优劣。

    自然度单独使用有一个盲区：用 latin-1 误读的 UTF-8 文本
    （如 ``ä¸­æ`` ）同样由合法拉丁字符构成，自然度并不低。
    因此必须再扣除乱码特征分 —— 两项合起来才能同时识别
    "字符非法"和"字符合法但组合不像人话"两类乱码。
    """
    if not text:
        return 0.0
    return naturalness(text) - 2.0 * mojibake_likelihood(text)


def mojibake_likelihood(text: str) -> float:
    """估算一段文本是乱码的可能性（0.0 - 1.0）。

    综合三类证据：

    1. 正则指纹（``â€™`` / ``Ã©`` / ``Ð`` 等典型序列）
    2. 重音字母、罕用汉字的异常占比
    3. 汉字"常用度"——正常中文几乎全由常用字构成，乱码则充满罕用字
    """
    if not text:
        return 0.0

    evidence = 0.0
    sample = text[:4096]
    length = max(1, len(sample))

    # 1) 正则指纹
    pattern_hits = 0
    for pattern in _MOJIBAKE_PATTERNS:
        pattern_hits += len(pattern.findall(sample))
    if pattern_hits:
        evidence += min(1.0, pattern_hits / (length * 0.05)) * 0.55

    # 2) 特征字符占比
    hint_count = sum(1 for ch in sample if ch in MOJIBAKE_HINT_CHARS)
    hint_ratio = hint_count / length
    if hint_ratio > 0.02:
        evidence += min(1.0, hint_ratio / 0.25) * 0.25

    # 3) 汉字常用度异常
    hanzi = [ch for ch in sample if CJK_UNIFIED_LOW <= ord(ch) <= CJK_UNIFIED_HIGH]
    if len(hanzi) >= 8:
        common = common_hanzi("utf-8")
        familiar = sum(1 for ch in hanzi if ch in common) / len(hanzi)
        if familiar < 0.55:
            evidence += (0.55 - familiar) / 0.55 * 0.45

    # 4) 控制字符与替换字符
    bad = sum(1 for ch in sample if classify_char(ch) in ("replacement", "control"))
    if bad:
        evidence += min(1.0, bad / (length * 0.02)) * 0.4

    return max(0.0, min(1.0, evidence))


def looks_like_mojibake(text: str, threshold: float = 0.30) -> bool:
    """判断文本是否像乱码。"""
    return mojibake_likelihood(text) >= threshold


def _try_single_fix(text: str, wrong: str, true: str) -> Optional[str]:
    """尝试用一组 (误用编码, 真实编码) 修复文本。"""
    if wrong == true:
        return None
    try:
        raw = text.encode(wrong)
    except (UnicodeEncodeError, LookupError):
        return None
    try:
        fixed = raw.decode(true)
    except (UnicodeDecodeError, LookupError):
        return None
    if not fixed or fixed == text:
        return None
    return fixed


def repair(text: str, max_rounds: int = MAX_ROUNDS, aggressive: bool = False) -> RepairResult:
    """自动修复乱码文本。

    Args:
        text: 待修复的文本。
        max_rounds: 最大修复轮数，处理被多次错误转码的文本。
        aggressive: 强制修复。默认只在结果明显更优时才修复。

    Returns:
        :class:`~charsetseer.models.RepairResult`
    """
    if not text:
        return RepairResult(ok=False, original=text, repaired=text)

    original = text
    current = text
    steps: List[str] = []
    used_pairs: List[Tuple[str, str]] = []

    base_score = _text_score(current)

    for _round in range(max_rounds):
        best_fixed: Optional[str] = None
        best_score = _text_score(current)
        best_pair: Optional[Tuple[str, str]] = None

        for wrong in WRONG_CANDIDATES:
            for true in TRUE_CANDIDATES:
                fixed = _try_single_fix(current, wrong, true)
                if fixed is None:
                    continue
                candidate_score = _text_score(fixed)
                if candidate_score > best_score + MIN_IMPROVEMENT:
                    best_score = candidate_score
                    best_fixed = fixed
                    best_pair = (wrong, true)

        if best_fixed is None or best_pair is None:
            break

        wrong, true = best_pair
        used_pairs.append(best_pair)
        steps.append(
            "第 %d 轮：以 %s 重新编码 -> 以 %s 解码（语言学得分 %.2f -> %.2f）"
            % (_round + 1, wrong, true, _text_score(current), best_score)
        )
        current = best_fixed

    if not used_pairs:
        if not aggressive:
            return RepairResult(ok=False, original=original, repaired=original)
        # 激进模式：即便没有明显提升，也尝试最强的一次单轮转换
        fallback = _try_single_fix(original, "latin-1", "utf-8")
        if fallback:
            return RepairResult(
                ok=True,
                original=original,
                repaired=fallback,
                wrong_encoding="latin-1",
                true_encoding="utf-8",
                confidence=0.3,
                steps=["激进模式：latin-1 -> utf-8（得分未显著提升，结果供人工确认）"],
            )
        return RepairResult(ok=False, original=original, repaired=original)

    final_score = _text_score(current)
    improvement = final_score - base_score
    confidence = max(0.3, min(0.99, 0.5 + improvement / 6.0))
    if len(used_pairs) > 1:
        # 多轮修复的确定性略低
        confidence *= 0.9

    wrong, true = used_pairs[0]
    return RepairResult(
        ok=True,
        original=original,
        repaired=current,
        wrong_encoding=wrong,
        true_encoding=true,
        confidence=confidence,
        steps=steps,
    )


def repair_bytes(data: bytes, preferred: Optional[str] = None) -> RepairResult:
    """修复一段字节：先用 ``preferred``（或 latin-1）解码再修复。

    适用于已经确定"这份文件是乱码"但不知道原始字节编码的场景。
    """
    codec = preferred or "latin-1"
    try:
        text = data.decode(codec)
    except (UnicodeDecodeError, LookupError):
        text = data.decode("latin-1", "replace")
    return repair(text)
