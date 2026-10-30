# -*- coding: utf-8 -*-
"""目录扫描。

批量处理的第一步是把"该看哪些文件"说清楚。扫描器提供按扩展名、
glob 模式与目录排除的过滤能力，并跳过体积异常的文件（例如几个 GB
的日志或二进制产物），避免批量检测被单个大文件拖垮。
"""

from __future__ import annotations

import fnmatch
import os
from typing import Iterable, List, Optional, Sequence

from .detector import detect_file
from .models import Detection, FileReport

#: 超过该体积的文件默认跳过（可通过 max_size 覆盖）
DEFAULT_MAX_SIZE = 32 * 1024 * 1024

#: 常见的二进制扩展名：编码检测对它们没有意义
BINARY_EXTENSIONS = frozenset(
    {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svgz",
        ".mp3", ".mp4", ".avi", ".mkv", ".mov", ".flac", ".wav", ".ogg",
        ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".jar",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".so", ".dll", ".dylib", ".exe", ".bin", ".o", ".a", ".class",
        ".pyc", ".pyo", ".wasm", ".ttf", ".otf", ".woff", ".woff2", ".eot",
    }
)

#: 默认跳过的目录名
DEFAULT_EXCLUDE_DIRS = frozenset(
    {".git", ".svn", ".hg", "node_modules", "__pycache__", ".venv", "venv",
     "dist", "build", ".idea", ".vscode", ".mypy_cache", ".pytest_cache"}
)


def is_probably_binary(path: str) -> bool:
    """按扩展名判断是否可能是二进制文件。"""
    return os.path.splitext(path)[1].lower() in BINARY_EXTENSIONS


def iter_files(
    root: str,
    include: Optional[Sequence[str]] = None,
    exclude: Optional[Sequence[str]] = None,
    exclude_dirs: Optional[Iterable[str]] = None,
    max_size: int = DEFAULT_MAX_SIZE,
    skip_binary: bool = True,
    follow_symlinks: bool = False,
):
    """遍历目录下的文件，按规则过滤后逐个产出路径。

    Args:
        root: 根目录。
        include: glob 白名单（匹配文件名），为空表示不过滤。
        exclude: glob 黑名单。
        exclude_dirs: 需要跳过的目录名集合。
        max_size: 跳过的体积上限。
        skip_binary: 是否跳过典型二进制扩展名。
        follow_symlinks: 是否跟随符号链接。
    """
    excluded_dirs = set(exclude_dirs) if exclude_dirs else set(DEFAULT_EXCLUDE_DIRS)
    include_patterns = list(include) if include else []
    exclude_patterns = list(exclude) if exclude else []

    if os.path.isfile(root):
        yield root
        return

    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        dirnames[:] = [d for d in dirnames if d not in excluded_dirs]
        for filename in sorted(filenames):
            if include_patterns and not any(
                fnmatch.fnmatch(filename, pattern) for pattern in include_patterns
            ):
                continue
            if any(fnmatch.fnmatch(filename, pattern) for pattern in exclude_patterns):
                continue
            full_path = os.path.join(dirpath, filename)
            if skip_binary and is_probably_binary(full_path):
                continue
            try:
                if os.path.getsize(full_path) > max_size:
                    continue
                if not os.path.isfile(full_path):
                    continue
            except OSError:
                continue
            yield full_path


def scan_file(path: str, explain: bool = False):
    """扫描单个文件并生成报告。"""
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        return FileReport(path=path, size=0, error="无法访问：%s" % exc)
    try:
        detection: Detection
        detection, _candidates = detect_file(path, explain=explain)
    except OSError as exc:
        return FileReport(path=path, size=size, error="读取失败：%s" % exc)
    return FileReport(path=path, size=size, detection=detection)


def scan_directory(
    root: str,
    include: Optional[Sequence[str]] = None,
    exclude: Optional[Sequence[str]] = None,
    exclude_dirs: Optional[Iterable[str]] = None,
    max_size: int = DEFAULT_MAX_SIZE,
    skip_binary: bool = True,
    limit: Optional[int] = None,
) -> List[FileReport]:
    """扫描目录，返回每个文件的检测报告。"""
    reports: List[FileReport] = []
    for path in iter_files(
        root,
        include=include,
        exclude=exclude,
        exclude_dirs=exclude_dirs,
        max_size=max_size,
        skip_binary=skip_binary,
    ):
        reports.append(scan_file(path))
        if limit is not None and len(reports) >= limit:
            break
    return reports


def summarize(reports: Sequence[FileReport]) -> dict:
    """对扫描结果做聚合统计，输出编码分布。"""
    distribution: dict = {}
    errors = 0
    total_bytes = 0
    for report in reports:
        if report.error:
            errors += 1
            continue
        total_bytes += report.size
        key = report.encoding
        bucket = distribution.setdefault(key, {"count": 0, "bytes": 0})
        bucket["count"] += 1
        bucket["bytes"] += report.size

    ordered = sorted(distribution.items(), key=lambda item: item[1]["count"], reverse=True)
    return {
        "files": len(reports),
        "errors": errors,
        "total_bytes": total_bytes,
        "distribution": [
            {"encoding": key, "count": value["count"], "bytes": value["bytes"]}
            for key, value in ordered
        ],
    }
