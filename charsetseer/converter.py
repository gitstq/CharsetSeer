# -*- coding: utf-8 -*-
"""转码与 BOM 处理。

转码看起来简单，真正容易翻车的是三个细节：

1. **先把源编码判准**，否则就是把乱码固化下来。
2. **BOM 的去留** —— Windows 工具链常常依赖 UTF-8 BOM，而 Unix 工具链
   遇到 BOM 会把它当成文件内容的一部分。CharsetSeer 提供
   ``keep`` / ``add`` / ``remove`` 三种策略。
3. **可回滚** —— 批量改编码是破坏性操作，默认提供备份与 dry-run。
"""

from __future__ import annotations

import os
import shutil
from typing import Optional

from .detector import detect_file
from .models import ConvertResult, Detection
from .tables import BOM_BYTES

#: BOM 处理策略
BOM_KEEP = "keep"
BOM_ADD = "add"
BOM_STRIP = "remove"

BOM_POLICIES = (BOM_KEEP, BOM_ADD, BOM_STRIP)


def has_bom(data: bytes) -> Optional[str]:
    """检测字节串是否以 BOM 开头，返回对应编码名。"""
    for encoding, signature in (
        ("utf-32-le", BOM_BYTES["utf-32-le"]),
        ("utf-32-be", BOM_BYTES["utf-32-be"]),
        ("utf-8-sig", BOM_BYTES["utf-8-sig"]),
        ("utf-16-le", BOM_BYTES["utf-16-le"]),
        ("utf-16-be", BOM_BYTES["utf-16-be"]),
    ):
        if data.startswith(signature):
            return encoding
    return None


def strip_bom(data: bytes) -> bytes:
    """移除字节串开头的 BOM（若有）。"""
    for signature in (
        BOM_BYTES["utf-32-le"],
        BOM_BYTES["utf-32-be"],
        BOM_BYTES["utf-8-sig"],
        BOM_BYTES["utf-16-le"],
        BOM_BYTES["utf-16-be"],
    ):
        if data.startswith(signature):
            return data[len(signature):]
    return data


def apply_bom_policy(data: bytes, target_encoding: str, policy: str) -> bytes:
    """按策略处理 BOM。

    Args:
        data: 已编码但**不含** BOM 的字节。
        target_encoding: 目标编码，决定是否支持加 BOM。
        policy: ``keep`` / ``add`` / ``remove``。
    """
    normalized = target_encoding.lower().replace("_", "-")
    # UTF-8 的 BOM 在标准里记作 utf-8-sig，用户写的却是 "utf-8"。
    # 不做这层映射的话 --bom add 会静默失效。
    if normalized in ("utf-8", "utf8"):
        normalized = "utf-8-sig"
    bom = BOM_BYTES.get(normalized)
    if policy == BOM_ADD and bom:
        return bom + data
    return data


def _normalize_codec(name: str) -> str:
    """把常见别名归一到 Python codecs 名称。"""
    key = name.strip().lower().replace("_", "-")
    aliases = {
        "utf8": "utf-8",
        "utf-8": "utf-8",
        "utf8sig": "utf-8-sig",
        "utf-8-sig": "utf-8-sig",
        "utf8-bom": "utf-8-sig",
        "gb2312": "gb18030",
        "gbk": "gb18030",
        "gb18030": "gb18030",
        "big5": "big5",
        "big5hkscs": "big5hkscs",
        "shiftjis": "shift_jis",
        "shift-jis": "shift_jis",
        "sjis": "shift_jis",
        "eucjp": "euc_jp",
        "euc-jp": "euc_jp",
        "euckr": "euc_kr",
        "euc-kr": "euc_kr",
        "ascii": "ascii",
        "latin1": "latin-1",
        "latin-1": "latin-1",
        "iso8859-1": "latin-1",
        "cp1252": "cp1252",
        "windows-1252": "cp1252",
        "utf16": "utf-16",
        "utf-16": "utf-16",
        "utf16le": "utf-16-le",
        "utf16be": "utf-16-be",
        "utf32": "utf-32",
        "utf-32": "utf-32",
    }
    return aliases.get(key, name)


def resolve_encoding(name: str) -> str:
    """归一化编码名；未知编码原样返回，由后续解码报错暴露问题。"""
    return _normalize_codec(name)


def convert_file(
    path: str,
    target_encoding: str,
    source_encoding: Optional[str] = None,
    backup: bool = False,
    dry_run: bool = False,
    bom_policy: str = BOM_KEEP,
    fallback: str = "replace",
) -> ConvertResult:
    """把单个文件转码到目标编码。

    Args:
        path: 文件路径。
        target_encoding: 目标编码。
        source_encoding: 源编码；为 ``None`` 时自动检测。
        backup: 是否生成 ``.bak`` 备份。
        dry_run: 只报告将要发生的变更，不落盘。
        bom_policy: ``keep`` / ``add`` / ``remove``。
        fallback: 解码失败时的错误处理策略（``strict`` / ``replace`` / ``ignore``）。

    Returns:
        :class:`~charsetseer.models.ConvertResult`
    """
    target = resolve_encoding(target_encoding)

    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        return ConvertResult(
            path=path,
            source_encoding=source_encoding or "unknown",
            target_encoding=target,
            changed=False,
            written=0,
            error="读取失败：%s" % exc,
        )

    # --- 判定源编码 --------------------------------------------------------
    detected: Optional[Detection] = None
    if source_encoding:
        source = resolve_encoding(source_encoding)
    else:
        detected, _candidates = detect_file(path)
        source = detected.encoding
    if source == "ascii":
        # ASCII 是 UTF-8 子集，写出时按目标编码处理即可
        source = "utf-8"

    # --- 解码 --------------------------------------------------------------
    try:
        text = data.decode(source, fallback)
    except (UnicodeDecodeError, LookupError) as exc:
        return ConvertResult(
            path=path,
            source_encoding=source,
            target_encoding=target,
            changed=False,
            written=0,
            error="解码失败（%s）：%s" % (source, exc),
        )

    # --- 编码 --------------------------------------------------------------
    try:
        encoded = text.encode(target, fallback)
    except (UnicodeEncodeError, LookupError) as exc:
        return ConvertResult(
            path=path,
            source_encoding=source,
            target_encoding=target,
            changed=False,
            written=0,
            error="编码失败（%s）：%s" % (target, exc),
        )

    # --- BOM 策略 ----------------------------------------------------------
    encoded = strip_bom(encoded)
    if bom_policy == BOM_ADD:
        encoded = apply_bom_policy(encoded, target, BOM_ADD)
    elif bom_policy == BOM_KEEP:
        # 仅当原文件带 BOM、且该 BOM 与目标编码兼容时才保留
        original_bom = has_bom(data)
        if original_bom:
            if original_bom == "utf-8-sig" and target in ("utf-8", "utf-8-sig"):
                encoded = BOM_BYTES["utf-8-sig"] + encoded
            elif original_bom.startswith("utf-16") and target.startswith("utf-16"):
                encoded = BOM_BYTES[original_bom] + encoded
            elif original_bom.startswith("utf-32") and target.startswith("utf-32"):
                encoded = BOM_BYTES[original_bom] + encoded

    changed = encoded != data

    if dry_run or not changed:
        return ConvertResult(
            path=path,
            source_encoding=source,
            target_encoding=target,
            changed=changed,
            written=len(encoded),
            dry_run=dry_run,
        )

    backup_path: Optional[str] = None
    if backup:
        backup_path = path + ".bak"
        try:
            shutil.copy2(path, backup_path)
        except OSError as exc:
            return ConvertResult(
                path=path,
                source_encoding=source,
                target_encoding=target,
                changed=False,
                written=0,
                error="备份失败：%s" % exc,
            )

    try:
        with open(path, "wb") as handle:
            handle.write(encoded)
    except OSError as exc:
        return ConvertResult(
            path=path,
            source_encoding=source,
            target_encoding=target,
            changed=False,
            written=0,
            backup_path=backup_path,
            error="写入失败：%s" % exc,
        )

    return ConvertResult(
        path=path,
        source_encoding=source,
        target_encoding=target,
        changed=True,
        written=len(encoded),
        backup_path=backup_path,
    )


def normalize_file_extensions(paths) -> list:
    """仅用于保持 API 对称的辅助函数：原样返回列表。"""
    return list(paths)


def safe_target_path(path: str) -> str:
    """返回可安全写入的目标路径（当前实现即原路径）。"""
    return os.path.abspath(path)
