# -*- coding: utf-8 -*-
"""CharsetSeer 的数据模型。

所有对外返回的结构都定义在这里，便于 CLI、库调用与报告模块共享
同一套字段，也方便用户在类型提示下做二次开发。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence


@dataclass(frozen=True)
class Detection:
    """一次编码检测的完整结论。

    Attributes:
        encoding: 判定出的最佳编码名（Python codecs 命名）。
        confidence: 置信度，0.0 - 1.0。
        language: 推测的语言归属，如 ``zh-hans`` / ``ja``。
        has_bom: 原始数据是否带 BOM。
        bom_encoding: 若带 BOM，BOM 声明的编码。
        score: 内部打分，用于候选排序与调试。
        byte_length: 参与检测的字节数。
        text_preview: 按判定编码解码后的文本预览（可能为空）。
    """

    encoding: str
    confidence: float
    language: str = "unknown"
    has_bom: bool = False
    bom_encoding: Optional[str] = None
    score: float = 0.0
    byte_length: int = 0
    text_preview: str = ""

    def to_dict(self) -> Dict[str, object]:
        """转换为可 JSON 序列化的字典。"""
        return {
            "encoding": self.encoding,
            "confidence": round(self.confidence, 4),
            "language": self.language,
            "has_bom": self.has_bom,
            "bom_encoding": self.bom_encoding,
            "score": round(self.score, 4),
            "byte_length": self.byte_length,
            "text_preview": self.text_preview,
        }


@dataclass(frozen=True)
class Candidate:
    """单个候选编码的评分明细，主要用于 ``--explain`` 调试输出。"""

    encoding: str
    score: float
    confidence: float
    language: str
    decodable: bool
    category_counts: Dict[str, int] = field(default_factory=dict)
    hanzi_familiarity: float = 0.0

    def to_dict(self) -> Dict[str, object]:
        """转换为可 JSON 序列化的字典。"""
        return {
            "encoding": self.encoding,
            "score": round(self.score, 4),
            "confidence": round(self.confidence, 4),
            "language": self.language,
            "decodable": self.decodable,
            "categories": dict(sorted(self.category_counts.items())),
            "hanzi_familiarity": round(self.hanzi_familiarity, 4),
        }


@dataclass(frozen=True)
class RepairResult:
    """乱码修复的结果。

    Attributes:
        ok: 是否找到了可信的修复方案。
        original: 原始（乱码）文本。
        repaired: 修复后的文本；未修复时等于 ``original``。
        wrong_encoding: 推测当初误用的编码。
        true_encoding: 推测的真实编码。
        confidence: 修复置信度，0.0 - 1.0。
        steps: 修复链路描述，便于审计。
    """

    ok: bool
    original: str
    repaired: str
    wrong_encoding: Optional[str] = None
    true_encoding: Optional[str] = None
    confidence: float = 0.0
    steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        """转换为可 JSON 序列化的字典。"""
        return {
            "ok": self.ok,
            "original": self.original,
            "repaired": self.repaired,
            "wrong_encoding": self.wrong_encoding,
            "true_encoding": self.true_encoding,
            "confidence": round(self.confidence, 4),
            "steps": list(self.steps),
        }


@dataclass(frozen=True)
class FileReport:
    """单文件的检测报告，供 ``scan`` 汇总使用。"""

    path: str
    size: int
    detection: Optional[Detection] = None
    error: Optional[str] = None

    @property
    def encoding(self) -> str:
        """检测到的编码；失败时返回 ``unknown``。"""
        return self.detection.encoding if self.detection else "unknown"

    @property
    def confidence(self) -> float:
        """检测置信度；失败时为 0.0。"""
        return self.detection.confidence if self.detection else 0.0

    def to_dict(self) -> Dict[str, object]:
        """转换为可 JSON 序列化的字典。"""
        return {
            "path": self.path,
            "size": self.size,
            "encoding": self.encoding,
            "confidence": round(self.confidence, 4),
            "error": self.error,
        }


@dataclass(frozen=True)
class ConvertResult:
    """单次转码操作的执行结果。"""

    path: str
    source_encoding: str
    target_encoding: str
    changed: bool
    written: int
    backup_path: Optional[str] = None
    dry_run: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        """转换为可 JSON 序列化的字典。"""
        return {
            "path": self.path,
            "source_encoding": self.source_encoding,
            "target_encoding": self.target_encoding,
            "changed": self.changed,
            "written": self.written,
            "backup_path": self.backup_path,
            "dry_run": self.dry_run,
            "error": self.error,
        }


def detection_rows(reports: Sequence[FileReport]) -> List[Dict[str, object]]:
    """把一组文件报告压平为表格行。"""
    return [r.to_dict() for r in reports]
