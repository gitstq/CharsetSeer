# -*- coding: utf-8 -*-
"""转码与 BOM 处理的单元测试。

转码是 CharsetSeer 里唯一会**写盘**的功能，因此这里的重点是：
dry-run 真的不写盘、备份真的生成、内容真的无损、BOM 策略真的生效。
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from charsetseer import convert_file, has_bom, resolve_encoding  # noqa: E402
from charsetseer.converter import strip_bom  # noqa: E402

TEXT = "中文编码检测工具：让乱码无处遁形。"


class ConverterTestCase(unittest.TestCase):
    """提供临时文件脚手架。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, True)

    def make_file(self, name: str, data: bytes) -> str:
        path = os.path.join(self.tmpdir, name)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    @staticmethod
    def read(path: str) -> bytes:
        """读取文件字节（确保句柄被关闭，避免 ResourceWarning）。"""
        with open(path, "rb") as handle:
            return handle.read()


class TestConvert(ConverterTestCase):
    """转码正确性。"""

    def test_gbk_to_utf8(self):
        path = self.make_file("a.txt", TEXT.encode("gb18030"))
        result = convert_file(path, "utf-8")
        self.assertTrue(result.changed)
        self.assertEqual(result.source_encoding, "gb18030")
        self.assertEqual(self.read(path).decode("utf-8"), TEXT)

    def test_utf8_to_gbk(self):
        path = self.make_file("b.txt", TEXT.encode("utf-8"))
        result = convert_file(path, "gb18030")
        self.assertTrue(result.changed)
        self.assertEqual(self.read(path).decode("gb18030"), TEXT)

    def test_explicit_source_encoding(self):
        path = self.make_file("c.txt", TEXT.encode("gb18030"))
        result = convert_file(path, "utf-8", source_encoding="gb18030")
        self.assertEqual(result.source_encoding, "gb18030")
        self.assertTrue(result.changed)

    def test_no_change_when_already_target(self):
        path = self.make_file("d.txt", TEXT.encode("utf-8"))
        result = convert_file(path, "utf-8")
        self.assertFalse(result.changed)

    def test_dry_run_does_not_write(self):
        path = self.make_file("e.txt", TEXT.encode("gb18030"))
        before = self.read(path)
        result = convert_file(path, "utf-8", dry_run=True)
        self.assertTrue(result.dry_run)
        self.assertEqual(self.read(path), before)

    def test_backup_created(self):
        path = self.make_file("f.txt", TEXT.encode("gb18030"))
        result = convert_file(path, "utf-8", backup=True)
        self.assertIsNotNone(result.backup_path)
        self.assertTrue(os.path.exists(result.backup_path))
        self.assertEqual(self.read(result.backup_path), TEXT.encode("gb18030"))

    def test_missing_file_returns_error(self):
        result = convert_file(os.path.join(self.tmpdir, "nope.txt"), "utf-8")
        self.assertIsNotNone(result.error)

    def test_roundtrip_preserves_text(self):
        path = self.make_file("g.txt", TEXT.encode("utf-8"))
        convert_file(path, "gb18030")
        convert_file(path, "utf-8")
        self.assertEqual(self.read(path).decode("utf-8"), TEXT)


class TestBOM(ConverterTestCase):
    """BOM 策略。"""

    def test_has_bom_detects_utf8_sig(self):
        self.assertEqual(has_bom(b"\xef\xbb\xbfabc"), "utf-8-sig")

    def test_has_bom_returns_none(self):
        self.assertIsNone(has_bom(b"abc"))

    def test_strip_bom(self):
        self.assertEqual(strip_bom(b"\xef\xbb\xbfabc"), b"abc")

    def test_add_bom(self):
        path = self.make_file("h.txt", TEXT.encode("utf-8"))
        convert_file(path, "utf-8", bom_policy="add")
        self.assertEqual(has_bom(self.read(path)), "utf-8-sig")

    def test_remove_bom(self):
        path = self.make_file("i.txt", b"\xef\xbb\xbf" + TEXT.encode("utf-8"))
        convert_file(path, "utf-8", bom_policy="remove")
        self.assertIsNone(has_bom(self.read(path)))

    def test_keep_bom(self):
        path = self.make_file("j.txt", b"\xef\xbb\xbf" + TEXT.encode("utf-8"))
        convert_file(path, "utf-8", bom_policy="keep")
        self.assertEqual(has_bom(self.read(path)), "utf-8-sig")


class TestResolveEncoding(unittest.TestCase):
    """编码别名归一化。"""

    def test_aliases(self):
        pairs = {
            "utf8": "utf-8",
            "gbk": "gb18030",
            "gb2312": "gb18030",
            "sjis": "shift_jis",
            "latin1": "latin-1",
            "windows-1252": "cp1252",
        }
        for alias, expected in pairs.items():
            self.assertEqual(resolve_encoding(alias), expected)

    def test_unknown_passthrough(self):
        self.assertEqual(resolve_encoding("weird-codec"), "weird-codec")


if __name__ == "__main__":
    unittest.main(verbosity=2)
