# -*- coding: utf-8 -*-
"""编码特征表与语言学权重。

CharsetSeer 的全部判别知识都集中在这里，检测引擎只负责流程编排。
所有数据均在运行时由 Python 标准库 ``codecs`` 推导生成，不引入任何
第三方依赖，也不内置体积庞大的码表文件。

判定一个候选编码是否"像真的"，依赖三类证据：

1. 字节序列合法性（由 ``codecs`` 严格解码保证）
2. 解码结果的语言学合理性（字符类别分布）
3. 汉字常用度（针对 GB18030 / Big5 的定向判别）
"""

from __future__ import annotations

import codecs
from typing import FrozenSet, Tuple

# --------------------------------------------------------------------------
# 常量：Unicode 区段
# --------------------------------------------------------------------------

CJK_UNIFIED_LOW = 0x4E00      # CJK 统一汉字起始
CJK_UNIFIED_HIGH = 0x9FFF     # CJK 统一汉字结束
CJK_EXT_A_LOW = 0x3400        # 扩展 A：多为罕用字，出现即扣分
CJK_EXT_A_HIGH = 0x4DBF
CJK_COMPAT_LOW = 0xF900       # 兼容汉字
CJK_COMPAT_HIGH = 0xFAFF
KANA_LOW = 0x3040             # 日文平假名 / 片假名
KANA_HIGH = 0x30FF
HANGUL_LOW = 0xAC00           # 韩文音节
HANGUL_HIGH = 0xD7AF
JAMO_LOW = 0x1100             # 韩文兼容字母
JAMO_HIGH = 0x11FF
CYRILLIC_LOW = 0x0400         # 西里尔
CYRILLIC_HIGH = 0x04FF
GREEK_LOW = 0x0370
GREEK_HIGH = 0x03FF
THAI_LOW = 0x0E00
THAI_HIGH = 0x0E7F
ARABIC_LOW = 0x0600
ARABIC_HIGH = 0x06FF
HEBREW_LOW = 0x0590
HEBREW_HIGH = 0x05FF
PRIVATE_USE_LOW = 0xE000      # 私用区：正常文本不应出现
PRIVATE_USE_HIGH = 0xF8FF
REPLACEMENT_CHAR = 0xFFFD     # U+FFFD 替换字符

# 允许出现在正常文本中的控制字符
ALLOWED_CONTROLS = frozenset((0x09, 0x0A, 0x0D, 0x0C, 0x08))

# --------------------------------------------------------------------------
# BOM 签名（按长度降序匹配，避免 UTF-32LE 与 UTF-16LE 前缀冲突）
# --------------------------------------------------------------------------

BOM_SIGNATURES: Tuple[Tuple[bytes, str], ...] = (
    (codecs.BOM_UTF32_LE, "utf-32-le"),   # FF FE 00 00
    (codecs.BOM_UTF32_BE, "utf-32-be"),   # 00 00 FE FF
    (codecs.BOM_UTF8, "utf-8-sig"),       # EF BB BF
    (codecs.BOM_UTF16_LE, "utf-16-le"),   # FF FE
    (codecs.BOM_UTF16_BE, "utf-16-be"),   # FE FF
)

BOM_BYTES = {
    "utf-8-sig": codecs.BOM_UTF8,
    "utf-16-le": codecs.BOM_UTF16_LE,
    "utf-16-be": codecs.BOM_UTF16_BE,
    "utf-32-le": codecs.BOM_UTF32_LE,
    "utf-32-be": codecs.BOM_UTF32_BE,
}

# --------------------------------------------------------------------------
# 候选编码及其语言归属
# --------------------------------------------------------------------------

#: 同分时的择优顺序。
#:
#: 不少编码在特定字节区间上是**完全等价**的 —— 例如 latin-1 与 cp1254
#: 对 0xE0-0xFF 给出相同字符。此时任何算法都无法区分，只能按"哪个名称
#: 对用户更有意义"来定：越通用、越符合直觉的排越前。
PREFERENCE_ORDER = (
    "utf-8", "ascii", "gb18030", "big5", "shift_jis", "euc_jp",
    "euc_kr", "johab", "cp1252", "cp1251", "koi8-r", "latin-1",
    "cp1250", "iso-8859-7", "cp1253", "cp1254", "cp1255", "cp1256",
)

#: 检测时依次尝试的候选编码。顺序不影响结果，最终按分数排序。
#: ``script`` 用于语言学打分：该编码"应该"产出什么文字。
#: ``auto`` 表示"按解码结果动态推断语言归属"。
#:
#: UTF-8 是通用容器，可以承载中文、俄文、阿拉伯文…… 若给它固定一种
#: 语言归属，它解出的文字就永远拿不到契合度加成，反而会被那些"碰巧
#: 解出自己目标文字"的错误编码压过去。因此 UTF-8 必须先解码、再判断
#: 里面装的到底是什么语言，然后按该语言的权重打分。
CANDIDATES: Tuple[Tuple[str, str], ...] = (
    # 编码名, 语言归属
    ("utf-8", "auto"),
    ("gb18030", "zh-hans"),
    ("big5", "zh-hant"),
    ("shift_jis", "ja"),
    ("euc_jp", "ja"),
    ("euc_kr", "ko"),
    ("johab", "ko"),
    ("koi8-r", "ru"),
    ("cp1251", "ru"),
    ("cp1252", "la"),
    ("cp1250", "la"),
    ("cp1253", "el"),
    ("cp1254", "tr"),
    ("cp1255", "he"),
    ("cp1256", "ar"),
    ("iso-8859-7", "el"),
    ("latin-1", "la"),
)

#: 单字节编码集合：这类编码几乎总能成功解码，必须靠语言学证据约束
SINGLE_BYTE_CODECS = frozenset(
    name for name, _script in CANDIDATES
    if name.startswith(("cp125", "koi8", "iso-8859")) or name == "latin-1"
)

#: 双字节编码的次字节合法区间，用于快速排除 EUC 类编码
DBCS_LEAD_RANGES = {
    "gb18030": ((0x81, 0xFE),),
    "big5": ((0x81, 0xFE),),
    "shift_jis": ((0x81, 0x9F), (0xE0, 0xFC)),
    "euc_jp": ((0xA1, 0xFE),),
    "euc_kr": ((0xA1, 0xFE),),
    "johab": ((0x84, 0xF9),),
}

#: 是否允许次字节落在 0x40-0x7E（ASCII 可见区）
DBCS_TRAIL_LOW_ALLOWED = {
    "gb18030": True,
    "big5": True,
    "shift_jis": True,
    "euc_jp": False,
    "euc_kr": False,
    "johab": True,
}

# --------------------------------------------------------------------------
# 常用汉字集合（运行时推导，带缓存）
# --------------------------------------------------------------------------

_CACHE: dict = {}


def _build_gb2312_hanzi() -> FrozenSet[str]:
    """推导 GB2312 **一级字库**汉字（B0A1-D7F9，共 3755 字）。

    这里刻意**只取一级字库**，是整套判别逻辑的关键取舍：

    - 一级字库是日常用字，真实简体中文文本几乎全由它构成；
    - 二级字库（D8A1-F7FE）是罕用字 —— 而"用错误编码解码正常文本"
      恰恰会大量产出这类罕用字。

    若把二级字库也算作"常见字"，乱码文本就能拿到和正常文本一样的
    熟悉度分数，判别能力会被彻底瓦解。
    """
    chars = set()
    for hi in range(0xB0, 0xD8):          # 仅一级字库区：B0-D7
        for lo in range(0xA1, 0xFF):      # 次字节 A1-FE
            try:
                ch = bytes((hi, lo)).decode("gb2312")
            except (UnicodeDecodeError, LookupError):
                continue
            if CJK_UNIFIED_LOW <= ord(ch) <= CJK_UNIFIED_HIGH:
                chars.add(ch)
    return frozenset(chars)


def _build_big5_common() -> FrozenSet[str]:
    """推导 Big5 常用字区（A440-C67E，共 5401 字）。"""
    chars = set()
    for hi in range(0xA4, 0xFA):
        for lo in list(range(0x40, 0x7F)) + list(range(0xA1, 0xFF)):
            try:
                ch = bytes((hi, lo)).decode("big5")
            except (UnicodeDecodeError, LookupError):
                continue
            if CJK_UNIFIED_LOW <= ord(ch) <= CJK_UNIFIED_HIGH:
                chars.add(ch)
    return frozenset(chars)


def _build_shiftjis_hanzi() -> FrozenSet[str]:
    """推导 Shift_JIS 汉字区，用于判断日语文本合理性。"""
    chars = set()
    for hi in list(range(0x81, 0xA0)) + list(range(0xE0, 0xFD)):
        for lo in range(0x40, 0xFD):
            if lo == 0x7F:
                continue
            try:
                ch = bytes((hi, lo)).decode("shift_jis")
            except (UnicodeDecodeError, LookupError):
                continue
            if CJK_UNIFIED_LOW <= ord(ch) <= CJK_UNIFIED_HIGH:
                chars.add(ch)
    return frozenset(chars)


def gb2312_hanzi() -> FrozenSet[str]:
    """返回 GB2312 汉字集合（惰性构建 + 缓存）。"""
    if "gb" not in _CACHE:
        _CACHE["gb"] = _build_gb2312_hanzi()
    return _CACHE["gb"]


def big5_common() -> FrozenSet[str]:
    """返回 Big5 常用字集合（惰性构建 + 缓存）。"""
    if "big5" not in _CACHE:
        _CACHE["big5"] = _build_big5_common()
    return _CACHE["big5"]


def shiftjis_hanzi() -> FrozenSet[str]:
    """返回 Shift_JIS 汉字集合（惰性构建 + 缓存）。"""
    if "sjis" not in _CACHE:
        _CACHE["sjis"] = _build_shiftjis_hanzi()
    return _CACHE["sjis"]


#: 各编码对应的"常用字参照集"，用于汉字常用度打分。
#:
#: 关键设计：``utf-8`` 使用 GB2312 与 Big5 常用字的**并集**作为宽松参照。
#: 这样当 UTF-8 解出的是正常中文时可以拿到高熟悉度，而 GBK 误解 UTF-8
#: 字节产生的乱码汉字（多为罕用字）熟悉度很低 —— 这正是区分
#: "真中文"与"看起来像中文的乱码"的核心证据。
COMMON_HANZI_BY_CODEC = {
    "utf-8": "union",
    "gb18030": "gb",
    "big5": "big5",
    "shift_jis": "sjis",
    "euc_jp": "sjis",
    "euc_kr": "gb",
}


def common_hanzi(codec_name: str) -> FrozenSet[str]:
    """返回指定编码的常用汉字参照集；无参照集时返回空集合。"""
    key = COMMON_HANZI_BY_CODEC.get(codec_name)
    if key is None:
        return frozenset()
    if key == "union":
        return gb2312_hanzi() | big5_common()
    if key == "gb":
        return gb2312_hanzi()
    if key == "big5":
        return big5_common()
    if key == "sjis":
        return shiftjis_hanzi()
    return frozenset()


# --------------------------------------------------------------------------
# 语言学打分权重
# --------------------------------------------------------------------------

#: 字符类别权重：正值加分，负值减分
SCORE_WEIGHTS = {
    "cjk": 2.0,          # 汉字
    "kana": 2.0,         # 假名
    "hangul": 2.0,       # 韩文音节
    "jamo": 1.0,         # 韩文兼容字母
    "cyrillic": 2.0,     # 西里尔
    "greek": 1.5,        # 希腊
    "thai": 1.5,
    "arabic": 1.5,
    "hebrew": 1.5,
    "latin": 0.8,        # 拉丁字母：普适，权重不宜过高
    "digit": 0.5,
    "space": 0.2,
    "punct": 0.6,        # 常见 ASCII 标点
    "cjk_punct": 1.5,    # 中文标点（，。！？、）
    "symbol": 0.1,
    "rare_cjk": -1.5,    # 扩展 A 区 / 兼容区汉字
    "private": -6.0,     # 私用区
    "replacement": -12.0,  # U+FFFD
    "control": -8.0,     # 非法控制字符
    "unassigned": -4.0,  # 未分配码位
}

#: 语言归属与字符类别的契合度奖励
SCRIPT_AFFINITY = {
    "zh-hans": {"cjk": 1.0, "cjk_punct": 1.0, "kana": -0.8, "hangul": -0.8, "cyrillic": -0.9},
    "zh-hant": {"cjk": 1.0, "cjk_punct": 1.0, "kana": -0.8, "hangul": -0.8, "cyrillic": -0.9},
    "ja": {"kana": 1.6, "cjk": 0.6, "cjk_punct": 0.4, "hangul": -1.0, "cyrillic": -1.0},
    "ko": {"hangul": 2.0, "jamo": 1.2, "cjk": 0.2, "kana": -1.0, "cyrillic": -1.0},
    "ru": {"cyrillic": 1.6, "latin": 0.4, "cjk": -1.0, "kana": -1.0, "hangul": -1.0},
    "el": {"greek": 1.6, "cjk": -1.0, "cyrillic": -0.6},
    # 土耳其语的文本主体仍是拉丁字母，与西欧语无异；真正区分它的是
    # Ğ/ğ/İ/ı/Ş/ş 这几个特有字母，已由 SPECIAL_CHARS 单独计权。
    # 若在此给 latin 更高的契合度，会让 cp1254 抢走本属于 latin-1 的西欧文本。
    "tr": {"latin": 0.3, "cjk": -1.0, "cyrillic": -0.8},
    "he": {"hebrew": 1.6, "cjk": -1.0},
    "ar": {"arabic": 1.6, "cjk": -1.0},
    "la": {"latin": 0.3, "cjk": -1.0, "kana": -1.0, "hangul": -1.0, "cyrillic": -0.8},
    "any": {},
}

#: 中文标点集合
CJK_PUNCT = frozenset("，。！？；：、（）《》「」『』【】〔〕～—…·　“”‘’")

#: 各语言归属的"目标文字类别"。用于主导文字一致性检查：
#: 若一个编码声称自己是某种语言，却几乎解不出该语言的文字，
#: 说明它只是碰巧解码成功。
SCRIPT_TARGETS = {
    "zh-hans": ("cjk", "cjk_punct"),
    "zh-hant": ("cjk", "cjk_punct"),
    "ja": ("kana", "cjk"),
    "ko": ("hangul", "jamo"),
    "ru": ("cyrillic",),
    "el": ("greek",),
    "he": ("hebrew",),
    "ar": ("arabic",),
    "tr": ("latin",),
    "la": ("latin",),
    "any": (),
}

#: 目标文字占比低于该阈值即视为"零星出现"，触发稀疏惩罚
MIN_TARGET_RATIO = 0.15

#: 稀疏惩罚系数：目标文字只是零星出现时整体降权
SPARSE_PENALTY = 0.55

#: 单字节编码的基础惩罚系数：恒成立的解需要更强证据才能胜出
SINGLE_BYTE_PENALTY = 0.55

#: 常用汉字命中率对最终分数的放大系数
HANZI_FAMILIARITY_BOOST = 3.5

#: 各编码的"专属字符"及其加成权重。
#:
#: 同一段字节用 latin-1 和 cp1254 解出的都是拉丁字母，单看字符类别
#: 无法区分。但只有 cp1254 能解出 Ğ/ğ/İ/ı/Ş/ş —— 这些字符一旦出现，
#: 就是"我确实是一份土耳其语文本"的直接证据。
SPECIAL_CHARS = {
    "cp1254": (frozenset("ĞğİıŞş"), 2.0),
    "cp1250": (frozenset("ŁłŚśŽžČčĚěŘřŤťŮůĄąĆćĘęŃńÓóŚśŹźŻż"), 2.0),
    "cp1253": (frozenset("ΆΈΉΊΌΎΏάέήίόύώϊϋΐΰς"), 2.0),
    "cp1255": (frozenset("אבגדהוזחטיכלמנסעפצקרשת"), 2.0),
    "cp1256": (frozenset("ابتثجحخدذرزسشصضطظعغفقكلمنهوي"), 2.0),
    "cp1251": (frozenset("Ёё№"), 1.0),
    "cp1252": (frozenset("€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”–—˜™š›œžŸ"), 1.2),
}

#: 专属字符加成的放大系数
SPECIAL_CHARS_BOOST = 1.2

#: 编码的先验概率加成（贝叶斯先验）。
#:
#: 在语言学证据强度相当时，更常见的编码更可能是答案。这不是拍脑袋：
#: johab 这类在现代几乎绝迹的韩文编码，只要"解出韩文得分高"就会抢走
#: 本属于 Big5 / GB18030 的**短中文文本** —— 因为短文本的统计证据太弱。
#: 给罕见编码一个先验惩罚，正是为了对抗这种证据不足时的随机性。
CODEC_PRIOR = {
    "utf-8": 0.30,
    "gb18030": 0.20,
    "big5": 0.20,
    "shift_jis": 0.10,
    "euc_jp": 0.0,
    "euc_kr": 0.0,
    "cp1252": 0.0,
    "latin-1": 0.0,
    "cp1251": 0.0,
    "koi8-r": -0.20,
    "cp1250": -0.30,
    "cp1253": -0.40,
    "cp1254": -0.40,
    "cp1255": -0.40,
    "cp1256": -0.40,
    "iso-8859-7": -0.40,
    "johab": -1.20,
}

#: 中文超高频字表（约 900 字，按现代汉语语料频率降序）。
#:
#: 这是整套判别体系里**最强的一条证据**。
#:
#: 真实中文文本有一个极强的统计特征：前 900 个高频字能覆盖日常文本的
#: 八成以上。而"用错误编码解码"等价于把字节随机映射到汉字，落到这
#: 900 字里的概率很低。于是"高频字命中率"能把真中文与乱码汉字干净地切开 ——
#: 这一点是"字是不是常用字"做不到的（常用字表有几千字，随机命中率太高）。
ZH_TOP_FREQ = (
    "的一是不了在人有我他这个们中来上大为和国地到以说时要就出会可也你对生能而子那得于"
    "着下自之年过发后作里用道行所然家种事成方多经么去法学如都同现当没动面起看定天分还"
    "进好小部其些主样理心她本前开但因只从想实日军者意无力它与长把机十民第公此已工使情"
    "明性知全三又关点正业外将两高间由问很最重并物手应战向头文体政美相见被利什二等产或"
    "新己制身果加西斯月话合回特代内信表化老给世位次度门任常先海通教儿原东声提立及比员"
    "解水名真论处走义各入几口认条平系气题活尔更别打女变四神总何电数安少报才结反受目太"
    "量再感建务做接必场件计管期市直德资命山金指克许统区保至队形社便空决治展马科司五基"
    "眼书非则听白却界达光放强即像难且权思王象完设式色路记南品住告类求据程北边死张该交"
    "规万取拉格望觉术领共确传师观清今切院让识候带导争运笑飞风步改收根干造言联持组每济"
    "车亲极林服快办议往元英士证近失转夫令准布始怎呢存未远叫台单影具罗字爱击流备兵连调"
    "深商算质团集百需价花党华城石级整府离况亚请技际约示复病息究线似官火断精满支视消越"
    "器容照须九增研写称企八功吗包片史委乎查轻易早曾除农找装广显吧阿李标谈吃图念六引历"
    "首医局突专费号尽另周较注语仅考落青随选列武红响虽推势参希古众构房半节土投某案黑维"
    "革划敌致陈律足态护七兴派孩验责营星够章音志底站严巴例防族供效续施留讲型料终答紧黄"
    "绝奇察母京段依批群项故按河米围江织害斗双境客纪座捐呀妈爸老师时间问题看到知道可以"
    "因为所以如果虽但是还很非常就已要会能说话东西地方时候什么怎么这样那样一下不能人们"
)

#: 高频字命中的期望比例（真实中文通常远高于此）
ZH_EXPECTED_TOP_RATIO = 0.42

#: 高频字加成的放大系数
ZH_TOP_FREQ_BOOST = 10.0

#: 俄语高频字母（按实际语料频率降序）。
#: 用于区分 cp1251 / koi8-r / cp1251 这类"都能解出西里尔"的编码 ——
#: 正确编码解出的字母分布符合真实俄语频率，错误编码则是均匀乱码。
RU_TOP_FREQ = "оеаинтсрвлкмдпуяы"

#: 俄语字母频率加成的放大系数
RU_FREQ_BOOST = 4.0

#: 俄语文本中高频字母的期望占比
RU_EXPECTED_TOP_RATIO = 0.42
