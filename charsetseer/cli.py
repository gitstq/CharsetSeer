# -*- coding: utf-8 -*-
"""命令行接口。

设计取向：**默认只读，破坏性操作必须显式声明**。``detect`` / ``scan`` /
``fix`` 都只是"看"，只有 ``convert`` 会写盘 —— 而它默认也要求你显式
给出目标编码，并额外提供 ``--dry-run`` 与 ``--backup``。
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional, Sequence

from . import __version__
from .converter import BOM_POLICIES, convert_file, has_bom, resolve_encoding
from .detector import detect_bytes, detect_file
from .mojibake import mojibake_likelihood, repair
from .report import (
    convert_payload,
    detection_payload,
    emit,
    render_candidates_text,
    render_convert_text,
    render_csv,
    render_detection_text,
    render_json,
    render_repair_text,
    render_table,
    repair_payload,
)
from .scanner import iter_files, scan_directory, scan_file, summarize

#: 输出格式选项
FORMATS = ("text", "json", "csv")


def _read_stdin_bytes() -> bytes:
    """从标准输入读取全部字节。"""
    return sys.stdin.buffer.read()


def _read_stdin_text() -> str:
    """从标准输入读取文本（UTF-8，失败回退 latin-1）。"""
    data = _read_stdin_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def build_parser() -> argparse.ArgumentParser:
    """构造命令行解析器。"""
    parser = argparse.ArgumentParser(
        prog="charsetseer",
        description="CharsetSeer — 零依赖 · 离线优先的字符编码检测与乱码修复引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  charsetseer detect README.md\n"
            "  charsetseer detect --explain data.csv\n"
            "  charsetseer scan ./src --include '*.py' --format json\n"
            "  charsetseer fix 'æ–‡å—åŒ–'\n"
            "  charsetseer convert ./docs --to utf-8 --backup --dry-run\n"
        ),
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    subparsers = parser.add_subparsers(dest="command", metavar="{detect,scan,fix,convert,bom,codecs}")

    # ---- detect -----------------------------------------------------------
    detect_parser = subparsers.add_parser("detect", help="检测文件或标准输入的编码")
    detect_parser.add_argument("paths", nargs="*", metavar="PATH", help="文件路径；省略或 '-' 表示读取标准输入")
    detect_parser.add_argument("--explain", action="store_true", help="输出全部候选编码的打分明细")
    detect_parser.add_argument("--format", choices=("text", "json"), default="text", help="输出格式")
    detect_parser.add_argument("--preview", type=int, default=200, help="文本预览长度（默认 200）")

    # ---- scan -------------------------------------------------------------
    scan_parser = subparsers.add_parser("scan", help="批量扫描目录下的文件编码")
    scan_parser.add_argument("root", metavar="DIR", help="要扫描的目录")
    scan_parser.add_argument("--include", action="append", default=None, metavar="GLOB",
                             help="只扫描匹配的文件名，可重复指定")
    scan_parser.add_argument("--exclude", action="append", default=None, metavar="GLOB",
                             help="排除匹配的文件名，可重复指定")
    scan_parser.add_argument("--max-size", type=int, default=32 * 1024 * 1024,
                             help="跳过超过该体积的文件（字节，默认 32MB）")
    scan_parser.add_argument("--limit", type=int, default=None, help="最多扫描多少个文件")
    scan_parser.add_argument("--summary", action="store_true", help="额外输出编码分布汇总")
    scan_parser.add_argument("--format", choices=FORMATS, default="text", help="输出格式")

    # ---- fix --------------------------------------------------------------
    fix_parser = subparsers.add_parser("fix", help="修复乱码文本")
    fix_parser.add_argument("text", nargs="?", default=None, help="待修复的文本；省略则读取标准输入")
    fix_parser.add_argument("--file", default=None, metavar="PATH", help="从文件读取待修复文本（按 UTF-8 读取，失败回退 latin-1）")
    fix_parser.add_argument("--aggressive", action="store_true", help="即使提升不明显也强制尝试修复")
    fix_parser.add_argument("--in-place", action="store_true", help="配合 --file 直接把修复结果写回文件")
    fix_parser.add_argument("--format", choices=("text", "json"), default="text", help="输出格式")

    # ---- convert ----------------------------------------------------------
    convert_parser = subparsers.add_parser("convert", help="批量转码")
    convert_parser.add_argument("paths", nargs="+", metavar="PATH", help="文件或目录")
    convert_parser.add_argument("--to", required=True, metavar="ENC", help="目标编码，如 utf-8 / gbk / utf-8-sig")
    convert_parser.add_argument("--from", dest="source", default=None, metavar="ENC",
                                help="源编码；省略则自动检测")
    convert_parser.add_argument("--bom", choices=BOM_POLICIES, default="keep",
                                help="BOM 策略：keep(保留) / add(添加) / remove(移除)")
    convert_parser.add_argument("--backup", action="store_true", help="写入前生成 .bak 备份")
    convert_parser.add_argument("--dry-run", action="store_true", help="只报告将要发生的变更，不写盘")
    convert_parser.add_argument("--include", action="append", default=None, metavar="GLOB",
                                help="目录模式下只处理匹配的文件名")
    convert_parser.add_argument("--exclude", action="append", default=None, metavar="GLOB",
                                help="目录模式下排除匹配的文件名")
    convert_parser.add_argument("--on-error", choices=("strict", "replace", "ignore"), default="replace",
                                help="编解码失败时的处理策略（默认 replace）")
    convert_parser.add_argument("--format", choices=("text", "json"), default="text", help="输出格式")

    # ---- bom --------------------------------------------------------------
    bom_parser = subparsers.add_parser("bom", help="检测文件是否带 BOM")
    bom_parser.add_argument("paths", nargs="+", metavar="PATH", help="文件路径")
    bom_parser.add_argument("--format", choices=("text", "json"), default="text", help="输出格式")

    # ---- codecs -----------------------------------------------------------
    subparsers.add_parser("codecs", help="列出支持的编码与别名")

    return parser


def _cmd_detect(args: argparse.Namespace) -> int:
    """执行 detect 子命令。"""
    paths: List[str] = list(args.paths) or ["-"]
    payloads = []
    for path in paths:
        if path == "-":
            data = _read_stdin_bytes()
            detection, candidates = detect_bytes(data, explain=args.explain)
            label = "<stdin>"
        else:
            if not os.path.exists(path):
                emit("❌ 文件不存在：%s" % path, stream=sys.stderr)
                return 2
            detection, candidates = detect_file(path, explain=args.explain)
            label = path

        if args.format == "json":
            payload = detection_payload(detection, path=label)
            if args.explain:
                payload["candidates"] = [c.to_dict() for c in candidates]
            payloads.append(payload)
        else:
            emit(render_detection_text(detection, path=None if path == "-" else path))
            if args.explain and candidates:
                emit("")
                emit(render_candidates_text(candidates))
            emit("")

    if args.format == "json":
        emit(render_json(payloads if len(payloads) != 1 else payloads[0]))
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    """执行 scan 子命令。"""
    if not os.path.exists(args.root):
        emit("❌ 路径不存在：%s" % args.root, stream=sys.stderr)
        return 2

    reports = scan_directory(
        args.root,
        include=args.include,
        exclude=args.exclude,
        max_size=args.max_size,
        limit=args.limit,
    )

    if args.format == "json":
        payload = {
            "root": args.root,
            "files": [r.to_dict() for r in reports],
        }
        if args.summary:
            payload["summary"] = summarize(reports)
        emit(render_json(payload))
        return 0

    if args.format == "csv":
        emit(render_csv(reports))
        return 0

    emit(render_table(reports))
    if args.summary:
        stats = summarize(reports)
        emit("")
        emit("📈 汇总：%d 个文件，%d 个错误，共 %d 字节" % (
            stats["files"], stats["errors"], stats["total_bytes"]))
        emit("%-14s %8s" % ("编码", "文件数"))
        for item in stats["distribution"]:
            emit("%-14s %8d" % (item["encoding"], item["count"]))
    return 0


def _cmd_fix(args: argparse.Namespace) -> int:
    """执行 fix 子命令。"""
    if args.file:
        with open(args.file, "rb") as handle:
            raw = handle.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        source_path = args.file
    elif args.text is not None:
        text = args.text
        source_path = None
    else:
        text = _read_stdin_text()
        source_path = None

    likelihood = mojibake_likelihood(text)
    result = repair(text, aggressive=args.aggressive)

    if args.in_place:
        if not source_path:
            emit("❌ --in-place 需要配合 --file 使用", stream=sys.stderr)
            return 2
        if not result.ok:
            emit("❎ 未找到可信修复方案，文件保持不变")
            return 1
        with open(source_path, "w", encoding="utf-8") as handle:
            handle.write(result.repaired)
        emit("✅ 已写回：%s" % source_path)
        return 0

    if args.format == "json":
        payload = repair_payload(result)
        payload["mojibake_likelihood"] = round(likelihood, 4)
        emit(render_json(payload))
        return 0

    emit("🔎 乱码可能性：%.2f" % likelihood)
    emit(render_repair_text(result))
    return 0 if result.ok else 1


def _cmd_convert(args: argparse.Namespace) -> int:
    """执行 convert 子命令。"""
    target = resolve_encoding(args.to)
    source = resolve_encoding(args.source) if args.source else None

    targets: List[str] = []
    for path in args.paths:
        if os.path.isdir(path):
            targets.extend(iter_files(path, include=args.include, exclude=args.exclude))
        elif os.path.exists(path):
            targets.append(path)
        else:
            emit("❌ 路径不存在：%s" % path, stream=sys.stderr)
            return 2

    if not targets:
        emit("（没有匹配的文件）")
        return 0

    results = [
        convert_file(
            path,
            target_encoding=target,
            source_encoding=source,
            backup=args.backup,
            dry_run=args.dry_run,
            bom_policy=args.bom,
            fallback=args.on_error,
        )
        for path in targets
    ]

    if args.format == "json":
        emit(render_json([convert_payload(r) for r in results]))
        return 0

    changed = 0
    failed = 0
    for result in results:
        emit(render_convert_text(result))
        if result.error:
            failed += 1
        elif result.changed:
            changed += 1
    emit("")
    emit("📦 共 %d 个文件：%d 个变更，%d 个失败%s" % (
        len(results), changed, failed, "（dry-run，未写盘）" if args.dry_run else ""))
    return 1 if failed else 0


def _cmd_bom(args: argparse.Namespace) -> int:
    """执行 bom 子命令。"""
    payloads = []
    for path in args.paths:
        if not os.path.exists(path):
            emit("❌ 文件不存在：%s" % path, stream=sys.stderr)
            return 2
        with open(path, "rb") as handle:
            data = handle.read()
        encoding = has_bom(data)
        if args.format == "json":
            payloads.append({"path": path, "has_bom": bool(encoding), "bom_encoding": encoding})
        else:
            if encoding:
                emit("📌 %s：带 BOM（%s）" % (path, encoding))
            else:
                emit("➖ %s：无 BOM" % path)
    if args.format == "json":
        emit(render_json(payloads if len(payloads) != 1 else payloads[0]))
    return 0


def _cmd_codecs(args: argparse.Namespace) -> int:
    """执行 codecs 子命令。"""
    emit("支持的编码与别名：")
    emit("  UTF 系列：utf-8 / utf8 / utf-8-sig / utf8-bom / utf-16 / utf-16-le / utf-16-be / utf-32")
    emit("  中文：gb18030（兼容 gbk / gb2312）/ big5 / big5hkscs")
    emit("  日文：shift_jis（别名 sjis / shift-jis）/ euc-jp")
    emit("  韩文：euc-kr / johab")
    emit("  西里尔：cp1251 / koi8-r")
    emit("  西欧：cp1252（windows-1252）/ latin-1（iso-8859-1）/ cp1250")
    emit("  其他：cp1253(希腊) / cp1254(土耳其) / cp1255(希伯来) / cp1256(阿拉伯)")
    emit("")
    emit("检测引擎会自动评估以上候选，无需手动指定。")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """命令行入口。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    handlers = {
        "detect": _cmd_detect,
        "scan": _cmd_scan,
        "fix": _cmd_fix,
        "convert": _cmd_convert,
        "bom": _cmd_bom,
        "codecs": _cmd_codecs,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
