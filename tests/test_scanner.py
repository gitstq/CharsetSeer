# -*- coding: utf-8 -*-
"""目录扫描与 CLI 的单元测试。"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from charsetseer import scan_directory, summarize  # noqa: E402
from charsetseer.cli import main  # noqa: E402
from charsetseer.report import render_csv, render_json, render_table  # noqa: E402

ZH = "中文编码检测工具"
JA = "これは日本語のテキストです"


class ScannerTestCase(unittest.TestCase):
    """构造一个混合编码的临时目录。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, True)
        self._write("zh_gbk.txt", ZH.encode("gb18030"))
        self._write("zh_utf8.txt", ZH.encode("utf-8"))
        self._write("ja_sjis.txt", JA.encode("shift_jis"))
        self._write("plain.txt", b"just ascii here")
        with open(os.path.join(self.tmpdir, "logo.png"), "wb") as handle:
            handle.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

    def _write(self, name: str, data: bytes) -> str:
        path = os.path.join(self.tmpdir, name)
        with open(path, "wb") as handle:
            handle.write(data)
        return path


class TestScan(ScannerTestCase):
    """目录扫描。"""

    def test_scan_finds_text_files(self):
        reports = scan_directory(self.tmpdir)
        names = sorted(os.path.basename(r.path) for r in reports)
        self.assertIn("zh_gbk.txt", names)
        self.assertIn("zh_utf8.txt", names)

    def test_binary_skipped_by_default(self):
        reports = scan_directory(self.tmpdir)
        names = [os.path.basename(r.path) for r in reports]
        self.assertNotIn("logo.png", names)

    def test_detected_encodings(self):
        reports = {os.path.basename(r.path): r for r in scan_directory(self.tmpdir)}
        self.assertEqual(reports["zh_gbk.txt"].encoding, "gb18030")
        self.assertEqual(reports["zh_utf8.txt"].encoding, "utf-8")
        self.assertEqual(reports["ja_sjis.txt"].encoding, "shift_jis")
        self.assertEqual(reports["plain.txt"].encoding, "ascii")

    def test_include_filter(self):
        reports = scan_directory(self.tmpdir, include=["*.txt"])
        self.assertTrue(all(r.path.endswith(".txt") for r in reports))

    def test_exclude_filter(self):
        reports = scan_directory(self.tmpdir, exclude=["ja_*"])
        names = [os.path.basename(r.path) for r in reports]
        self.assertNotIn("ja_sjis.txt", names)

    def test_limit(self):
        self.assertEqual(len(scan_directory(self.tmpdir, limit=2)), 2)

    def test_summarize(self):
        stats = summarize(scan_directory(self.tmpdir))
        self.assertEqual(stats["files"], 4)
        self.assertEqual(stats["errors"], 0)
        self.assertTrue(stats["distribution"])


class TestReport(ScannerTestCase):
    """报告渲染。"""

    def test_table_non_empty(self):
        reports = scan_directory(self.tmpdir)
        self.assertIn("zh_gbk.txt", render_table(reports))

    def test_csv_header(self):
        csv_text = render_csv(scan_directory(self.tmpdir))
        self.assertTrue(csv_text.startswith("path,encoding,confidence"))

    def test_json_parsable(self):
        payload = {"a": 1}
        self.assertEqual(json.loads(render_json(payload))["a"], 1)

    def test_empty_table(self):
        self.assertIn("没有匹配", render_table([]))


class TestCLI(unittest.TestCase):
    """命令行端到端。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, True)
        self.zh = os.path.join(self.tmpdir, "zh.txt")
        with open(self.zh, "wb") as handle:
            handle.write(ZH.encode("gb18030"))

    @staticmethod
    def read(path: str) -> bytes:
        """读取文件字节（确保句柄被关闭，避免 ResourceWarning）。"""
        with open(path, "rb") as handle:
            return handle.read()

    def _run(self, argv):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(argv)
        return code, buffer.getvalue()

    def test_detect_text(self):
        code, out = self._run(["detect", self.zh])
        self.assertEqual(code, 0)
        self.assertIn("gb18030", out)

    def test_detect_json(self):
        code, out = self._run(["detect", "--format", "json", self.zh])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["encoding"], "gb18030")

    def test_detect_explain(self):
        code, out = self._run(["detect", "--explain", self.zh])
        self.assertEqual(code, 0)
        self.assertIn("可解码", out)

    def test_detect_missing_file(self):
        code, _out = self._run(["detect", "/nonexistent/file.txt"])
        self.assertEqual(code, 2)

    def test_scan_text(self):
        code, out = self._run(["scan", self.tmpdir])
        self.assertEqual(code, 0)
        self.assertIn("zh.txt", out)

    def test_scan_csv(self):
        code, out = self._run(["scan", self.tmpdir, "--format", "csv"])
        self.assertEqual(code, 0)
        self.assertIn("path,encoding", out)

    def test_convert_dry_run(self):
        code, out = self._run(["convert", self.zh, "--to", "utf-8", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("dry-run", out)
        # dry-run 不应改动文件
        self.assertEqual(self.read(self.zh), ZH.encode("gb18030"))

    def test_convert_apply(self):
        code, _out = self._run(["convert", self.zh, "--to", "utf-8"])
        self.assertEqual(code, 0)
        self.assertEqual(self.read(self.zh).decode("utf-8"), ZH)

    def test_bom_command(self):
        code, out = self._run(["bom", self.zh])
        self.assertEqual(code, 0)
        self.assertIn("BOM", out)

    def test_codecs_command(self):
        code, out = self._run(["codecs"])
        self.assertEqual(code, 0)
        self.assertIn("gb18030", out)

    def test_fix_command(self):
        broken = ZH.encode("utf-8").decode("latin-1")
        code, out = self._run(["fix", broken])
        self.assertEqual(code, 0)
        self.assertIn(ZH, out)

    def test_no_command_prints_help(self):
        code, out = self._run([])
        self.assertEqual(code, 0)
        self.assertIn("usage", out.lower())

    def test_version(self):
        # argparse 的 --version 会走 parser.exit()，表现为 SystemExit(0)
        with self.assertRaises(SystemExit) as ctx:
            self._run(["--version"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
