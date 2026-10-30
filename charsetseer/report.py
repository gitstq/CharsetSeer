# -*- coding: utf-8 -*-
"""报告渲染。

同一份检测结果需要三种形态：给人看的表格、给程序消费的 JSON、
以及能直接粘进 Excel / 表格软件的 CSV。渲染层只做格式化，不做判断。
"""

from __future__ import annotations

import csv
import json
import sys
from typing import Any, Dict, List, Optional, Sequence

from .models import (
    Candidate,
    ConvertResult,
    Detection,
    FileReport,
    RepairResult,
)

#: 置信度的文字化描述，便于快速扫读
def confidence_label(value: float) -> str:
    """把置信度映射为可读等级。"""
    if value >= 0.95:
        return "确定"
    if value >= 0.80:
        return "很高"
    if value >= 0.60:
        return "较高"
    if value >= 0.40:
        return "一般"
    return "偏低"


def _bar(value: float, width: int = 12) -> str:
    """用字符条可视化置信度。"""
    filled = int(round(max(0.0, min(1.0, value)) * width))
    return "█" * filled + "░" * (width - filled)


def render_detection_text(detection: Detection, path: Optional[str] = None) -> str:
    """渲染单个检测结果为多行文本。"""
    lines: List[str] = []
    if path:
        lines.append("📄 文件：%s" % path)
    lines.append("🔤 编码：%s" % detection.encoding)
    lines.append("📊 置信度：%.2f (%s)  %s" % (
        detection.confidence, confidence_label(detection.confidence), _bar(detection.confidence)
    ))
    lines.append("🌐 语言：%s" % detection.language)
    if detection.has_bom:
        lines.append("📌 BOM：有（%s）" % detection.bom_encoding)
    else:
        lines.append("📌 BOM：无")
    lines.append("📦 字节数：%d" % detection.byte_length)
    if detection.text_preview:
        preview = detection.text_preview.replace("\r", " ").replace("\n", " ")
        lines.append("👀 预览：%s" % preview)
    return "\n".join(lines)


def render_candidates_text(candidates: Sequence[Candidate]) -> str:
    """渲染候选明细表（``--explain``）。"""
    if not candidates:
        return ""
    header = "%-14s %10s %10s %8s %10s" % ("编码", "得分", "置信度", "可解码", "汉字熟悉度")
    lines = [header, "-" * len(header)]
    for candidate in sorted(candidates, key=lambda c: (not c.decodable, -c.score)):
        score = "N/A" if candidate.score == float("-inf") else "%.3f" % candidate.score
        lines.append(
            "%-14s %10s %10.2f %8s %10.2f"
            % (
                candidate.encoding,
                score,
                candidate.confidence,
                "是" if candidate.decodable else "否",
                candidate.hanzi_familiarity,
            )
        )
    return "\n".join(lines)


def render_table(reports: Sequence[FileReport]) -> str:
    """渲染扫描结果为对齐的文本表格。"""
    if not reports:
        return "（没有匹配的文件）"

    rows: List[List[str]] = []
    for report in reports:
        if report.error:
            rows.append([report.path, "-", "-", "-", report.error])
        else:
            rows.append([
                report.path,
                report.encoding,
                "%.2f" % report.confidence,
                confidence_label(report.confidence),
                "%d" % report.size,
            ])

    headers = ["文件", "编码", "置信度", "等级", "字节"]
    widths = [len(h) for h in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], _display_width(cell))

    def _fmt(cells: Sequence[str]) -> str:
        parts = []
        for index, cell in enumerate(cells):
            padding = widths[index] - _display_width(cell)
            parts.append(cell + " " * padding)
        return "  ".join(parts).rstrip()

    lines = [_fmt(headers), "  ".join("-" * w for w in widths)]
    lines.extend(_fmt(row) for row in rows)
    return "\n".join(lines)


def _display_width(text: str) -> int:
    """按终端显示宽度计算字符串长度（CJK 占两格）。"""
    width = 0
    for ch in text:
        code = ord(ch)
        if (
            0x1100 <= code <= 0x115F
            or 0x2E80 <= code <= 0xA4CF
            or 0xAC00 <= code <= 0xD7A3
            or 0xF900 <= code <= 0xFAFF
            or 0xFE30 <= code <= 0xFE6F
            or 0xFF00 <= code <= 0xFF60
            or 0xFFE0 <= code <= 0xFFE6
        ):
            width += 2
        else:
            width += 1
    return width


def render_json(payload: Any, indent: int = 2) -> str:
    """渲染为 JSON 字符串。"""
    return json.dumps(payload, ensure_ascii=False, indent=indent)


def render_csv(reports: Sequence[FileReport]) -> str:
    """渲染为 CSV 文本。"""
    buffer = _StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["path", "encoding", "confidence", "language", "has_bom", "size", "error"])
    for report in reports:
        detection = report.detection
        writer.writerow([
            report.path,
            report.encoding,
            "%.4f" % report.confidence,
            detection.language if detection else "",
            "yes" if (detection and detection.has_bom) else "no",
            report.size,
            report.error or "",
        ])
    return buffer.getvalue()


class _StringIO:
    """极简字符串缓冲区，避免为一次性渲染引入 io 语义负担。"""

    def __init__(self) -> None:
        self._parts: List[str] = []

    def write(self, text: str) -> int:
        self._parts.append(text)
        return len(text)

    def getvalue(self) -> str:
        return "".join(self._parts)


def render_repair_text(result: RepairResult) -> str:
    """渲染乱码修复结果。"""
    lines: List[str] = []
    if result.ok:
        lines.append("✅ 已修复（置信度 %.2f）" % result.confidence)
        lines.append("🔁 误用编码：%s -> 真实编码：%s" % (result.wrong_encoding, result.true_encoding))
        lines.append("📝 修复前：%s" % _one_line(result.original))
        lines.append("✨ 修复后：%s" % _one_line(result.repaired))
        for step in result.steps:
            lines.append("   · %s" % step)
    else:
        lines.append("❎ 未发现可信的修复方案（文本可能本身正常，或字节已不可逆丢失）")
        lines.append("📝 原文：%s" % _one_line(result.original))
    return "\n".join(lines)


def render_convert_text(result: ConvertResult) -> str:
    """渲染转码结果。"""
    if result.error:
        return "❌ %s：%s" % (result.path, result.error)
    flag = "🔍 dry-run" if result.dry_run else ("✅ 已写入" if result.changed else "⏭️  无需变更")
    text = "%s %s：%s -> %s（%d 字节）" % (
        flag, result.path, result.source_encoding, result.target_encoding, result.written
    )
    if result.backup_path:
        text += "  [备份：%s]" % result.backup_path
    return text


def _one_line(text: str, limit: int = 120) -> str:
    """把文本压成单行便于展示。"""
    flat = text.replace("\r", " ").replace("\n", " ")
    if len(flat) > limit:
        return flat[:limit] + " …"
    return flat


def emit(text: str, stream=None) -> None:
    """输出结果到指定流（默认 stdout）。"""
    stream = stream or sys.stdout
    stream.write(text + "\n")


def detection_payload(detection: Detection, path: Optional[str] = None) -> Dict[str, Any]:
    """构造单个检测结果的 JSON 载荷。"""
    payload = detection.to_dict()
    if path is not None:
        payload = {"path": path, **payload}
    return payload


def repair_payload(result: RepairResult) -> Dict[str, Any]:
    """构造修复结果的 JSON 载荷。"""
    return result.to_dict()


def convert_payload(result: ConvertResult) -> Dict[str, Any]:
    """构造转码结果的 JSON 载荷。"""
    return result.to_dict()
