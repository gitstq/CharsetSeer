#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编码检测准确率基准测试。

用法::

    python3 scripts/benchmark.py            # 运行全部用例
    python3 scripts/benchmark.py --verbose  # 逐条显示

任何人都可以运行这个脚本来复现 README 中声称的准确率，
不需要额外依赖，也不需要联网。
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from charsetseer import detect  # noqa: E402

#: (用例名, 期望编码集合, 编码方式, 文本)
#: 期望用集合表示，因为部分编码彼此等价（例如 latin-1 与 cp1252
#: 在 0xE0-0xFF 区间给出相同字符），判定其中任意一个都算正确。
CASES = [
    ("UTF-8 简体中文", {"utf-8"}, "utf-8",
     "中文编码检测是一件非常实用的事情，能够帮助开发者快速定位乱码问题的根源。"),
    ("GB18030 简体中文", {"gb18030"}, "gb18030",
     "中文编码检测是一件非常实用的事情，能够帮助开发者快速定位乱码问题的根源。"),
    ("GB18030 长文本", {"gb18030"}, "gb18030",
     "我们经常会遇到这样的情况：一个文件在别人的电脑上打开是正常的，"
     "但是在自己的电脑上打开却是一堆乱码。这通常是因为文件的编码方式和打开时"
     "使用的编码方式不一致。解决这个问题的最好办法，就是先准确地判断出文件"
     "真正的编码，然后再用正确的编码去打开它。"),
    ("Big5 繁體中文", {"big5"}, "big5",
     "繁體中文編碼檢測是一個非常實用的工具，可以幫助開發者快速定位亂碼問題。"),
    ("Big5 短文本", {"big5"}, "big5", "繁體中文測試\n"),
    ("Shift_JIS 日文", {"shift_jis"}, "shift_jis",
     "これは日本語のテキストです。文字化けを検出して修復することができます。"),
    ("Shift_JIS 短文本", {"shift_jis"}, "shift_jis", "日本語\n"),
    ("EUC-KR 韩文", {"euc_kr"}, "euc_kr",
     "이것은 한국어 텍스트입니다. 인코딩을 감지하고 복구할 수 있습니다."),
    ("UTF-8 俄文", {"utf-8"}, "utf-8",
     "Это русский текст для проверки определения кодировки символов."),
    ("CP1251 俄文", {"cp1251"}, "cp1251",
     "Это русский текст для проверки определения кодировки символов."),
    ("UTF-8 阿拉伯文", {"utf-8"}, "utf-8",
     "هذا نص عربي لاختبار اكتشاف ترميز الأحرف."),
    ("UTF-8 希腊文", {"utf-8"}, "utf-8",
     "Αυτό είναι ένα ελληνικό κείμενο για δοκιμή."),
    ("CP1252 西欧文", {"cp1252"}, "cp1252",
     "Smart quotes “like this” and — dashes cost €5"),
    ("Latin-1 法文", {"latin-1", "cp1252"}, "latin-1",
     "Ceci est un texte français avec des accents éàü"),
    ("GB18030 极短文本", {"gb18030"}, "gb18030", "张三"),
    ("UTF-8 混合内容", {"utf-8"}, "utf-8",
     "Server 配置：端口 8080，路径 /var/log/app.log，状态 OK\n"),
    ("ASCII", {"ascii"}, "ascii", "Hello world, plain ascii text file."),
]

#: BOM 用例单独处理（需要先编码再拼 BOM）
BOM_CASES = [
    ("UTF-8 BOM", "utf-8-sig", b"\xef\xbb\xbf", "utf-8"),
    ("UTF-16LE BOM", "utf-16-le", b"\xff\xfe", "utf-16-le"),
    ("UTF-16BE BOM", "utf-16-be", b"\xfe\xff", "utf-16-be"),
]


def main(argv=None) -> int:
    """运行基准测试并打印结果。"""
    argv = argv or []
    verbose = "--verbose" in argv or "-v" in argv

    print("=" * 74)
    print("CharsetSeer 编码检测准确率基准")
    print("=" * 74)
    print()
    print("%-22s %-12s %-12s %8s" % ("用例", "期望", "判定", "置信度"))
    print("-" * 74)

    passed = 0
    total = 0

    for name, expected, codec, text in CASES:
        data = text.encode(codec)
        result = detect(data)
        total += 1
        hit = result.encoding in expected
        passed += hit
        print("%-22s %-12s %-12s %8.2f  %s" % (
            name, "/".join(sorted(expected)), result.encoding,
            result.confidence, "✅" if hit else "❌",
        ))

    for name, expected, bom, codec in BOM_CASES:
        data = bom + "带 BOM 的示例文本".encode(codec)
        result = detect(data)
        total += 1
        hit = result.encoding == expected
        passed += hit
        print("%-22s %-12s %-12s %8.2f  %s" % (
            name, expected, result.encoding, result.confidence,
            "✅" if hit else "❌",
        ))

    print("-" * 74)
    rate = passed / total * 100
    print("结果：%d/%d 通过（%.1f%%）" % (passed, total, rate))
    print()

    if verbose:
        print("说明：")
        print("  · 部分编码互相等价（如 latin-1 与 cp1252 在 0xE0-0xFF 区间"),
        print("    给出相同字符），判定其中任意一个均记为正确。")
        print("  · BOM 用例为硬证据，置信度恒为 1.00。")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
