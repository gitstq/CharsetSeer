# -*- coding: utf-8 -*-
"""CharsetSeer — 零依赖 · 离线优先的字符编码检测与乱码修复引擎。

核心 API::

    from charsetseer import detect, detect_file, repair, convert_file

    result = detect(raw_bytes)
    print(result.encoding, result.confidence)

设计原则：

- **零依赖**：仅使用 Python 标准库，无第三方包、无模型文件、无网络请求。
- **离线优先**：所有判定在本地完成，适合内网、CI 与隐私敏感场景。
- **可逆优先**：乱码修复只在证据充分时执行，绝不猜测式改写。
"""

from __future__ import annotations

from .converter import (
    BOM_KEEP,
    convert_file,
    has_bom,
    resolve_encoding,
    strip_bom,
)
from .detector import SAMPLE_LIMIT, detect, detect_bytes, detect_file, guess_language
from .models import (
    Candidate,
    ConvertResult,
    Detection,
    FileReport,
    RepairResult,
)
from .mojibake import (
    looks_like_mojibake,
    mojibake_likelihood,
    naturalness,
    repair,
    repair_bytes,
)
from .scanner import scan_directory, scan_file, summarize
from .tables import CANDIDATES

__version__ = "1.0.0"
__all__ = [
    "__version__",
    # 检测
    "detect",
    "detect_bytes",
    "detect_file",
    "guess_language",
    "SAMPLE_LIMIT",
    "CANDIDATES",
    # 乱码修复
    "repair",
    "repair_bytes",
    "mojibake_likelihood",
    "looks_like_mojibake",
    "naturalness",
    # 转码
    "convert_file",
    "resolve_encoding",
    "has_bom",
    "strip_bom",
    "BOM_KEEP",
    # 扫描
    "scan_directory",
    "scan_file",
    "summarize",
    # 模型
    "Detection",
    "Candidate",
    "RepairResult",
    "FileReport",
    "ConvertResult",
]
