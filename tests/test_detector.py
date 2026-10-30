# -*- coding: utf-8 -*-
"""编码检测引擎的单元测试。

这里的用例刻意覆盖两类场景：

- **常规样本**：足够长的正常文本，检测必须准确无误判；
- **边界样本**：短文本、纯 ASCII、空文件、BOM —— 这些才是真正容易翻车
  的地方，也是同类工具最常出问题的地方。
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from charsetseer import detect, detect_bytes, detect_file  # noqa: E402
from charsetseer.detector import classify_char, infer_script  # noqa: E402

ZH = "中文编码检测是一件非常实用的事情，能够帮助开发者快速定位乱码问题的根源。"
ZH_HANT = "繁體中文編碼檢測是一個非常實用的工具，可以幫助開發者快速定位亂碼問題。"
JA = "これは日本語のテキストです。文字化けを検出して修復することができます。"
KO = "이것은 한국어 텍스트입니다. 인코딩을 감지하고 복구할 수 있습니다."
RU = "Это русский текст для проверки определения кодировки символов."
AR = "هذا نص عربي لاختبار اكتشاف ترميز الأحرف."
EL = "Αυτό είναι ένα ελληνικό κείμενο για δοκιμή."
FR = "Ceci est un texte français avec des accents éàü"


class TestDetectEncoding(unittest.TestCase):
    """编码判定正确性。"""

    def test_utf8_chinese(self):
        self.assertEqual(detect(ZH.encode("utf-8")).encoding, "utf-8")

    def test_gb18030_chinese(self):
        self.assertEqual(detect(ZH.encode("gb18030")).encoding, "gb18030")

    def test_big5_traditional(self):
        self.assertEqual(detect(ZH_HANT.encode("big5")).encoding, "big5")

    def test_shift_jis_japanese(self):
        self.assertEqual(detect(JA.encode("shift_jis")).encoding, "shift_jis")

    def test_euc_kr_korean(self):
        self.assertEqual(detect(KO.encode("euc_kr")).encoding, "euc_kr")

    def test_utf8_russian(self):
        self.assertEqual(detect(RU.encode("utf-8")).encoding, "utf-8")

    def test_cp1251_russian(self):
        self.assertEqual(detect(RU.encode("cp1251")).encoding, "cp1251")

    def test_utf8_arabic(self):
        self.assertEqual(detect(AR.encode("utf-8")).encoding, "utf-8")

    def test_utf8_greek(self):
        self.assertEqual(detect(EL.encode("utf-8")).encoding, "utf-8")

    def test_cp1252_western(self):
        text = "Smart quotes “like this” and — dashes cost €5"
        self.assertEqual(detect(text.encode("cp1252")).encoding, "cp1252")

    def test_latin1_french(self):
        # latin-1 与 cp1252 对这段字节等价，两者都可接受
        self.assertIn(detect(FR.encode("latin-1")).encoding, ("latin-1", "cp1252"))

    def test_ascii(self):
        result = detect(b"Hello world, plain ascii text file.")
        self.assertEqual(result.encoding, "ascii")
        self.assertGreater(result.confidence, 0.9)

    def test_utf8_bom(self):
        data = b"\xef\xbb\xbf" + "带 BOM 的 UTF-8 文件".encode("utf-8")
        result = detect(data)
        self.assertEqual(result.encoding, "utf-8-sig")
        self.assertTrue(result.has_bom)
        self.assertEqual(result.confidence, 1.0)

    def test_utf16_bom_le(self):
        data = b"\xff\xfe" + "UTF-16LE".encode("utf-16-le")
        self.assertEqual(detect(data).encoding, "utf-16-le")

    def test_utf16_bom_be(self):
        data = b"\xfe\xff" + "UTF-16BE".encode("utf-16-be")
        self.assertEqual(detect(data).encoding, "utf-16-be")


class TestShortSamples(unittest.TestCase):
    """短文本与极短文本 —— 统计证据最弱、最容易误判的场景。"""

    def test_two_char_gbk(self):
        self.assertEqual(detect("张三".encode("gb18030")).encoding, "gb18030")

    def test_short_big5(self):
        self.assertEqual(detect("繁體中文測試\n".encode("big5")).encoding, "big5")

    def test_short_shift_jis(self):
        self.assertEqual(detect("日本語\n".encode("shift_jis")).encoding, "shift_jis")

    def test_short_utf8(self):
        self.assertEqual(detect("中文\n".encode("utf-8")).encoding, "utf-8")


class TestEdgeCases(unittest.TestCase):
    """空输入、二进制、混合内容等边界。"""

    def test_empty_bytes(self):
        result = detect(b"")
        self.assertEqual(result.byte_length, 0)

    def test_single_byte(self):
        result = detect(b"A")
        self.assertEqual(result.encoding, "ascii")

    def test_binary_no_crash(self):
        data = bytes(range(256))
        result = detect(data)
        self.assertIsInstance(result.encoding, str)

    def test_mixed_ascii_and_chinese(self):
        data = b"Server: port 8080, path /var/log/app.log\n" + "配置状态正常".encode("utf-8")
        self.assertEqual(detect(data).encoding, "utf-8")


class TestConfidence(unittest.TestCase):
    """置信度的取值范围与相对关系。"""

    def test_confidence_in_range(self):
        for data in (ZH.encode("utf-8"), ZH.encode("gb18030"), JA.encode("shift_jis")):
            result = detect(data)
            self.assertGreaterEqual(result.confidence, 0.0)
            self.assertLessEqual(result.confidence, 1.0)

    def test_bom_gives_full_confidence(self):
        data = b"\xef\xbb\xbf" + ZH.encode("utf-8")
        self.assertEqual(detect(data).confidence, 1.0)

    def test_long_text_more_confident_than_short(self):
        long_result = detect(ZH.encode("gb18030"))
        short_result = detect("张三".encode("gb18030"))
        self.assertGreater(long_result.confidence, short_result.confidence)


class TestClassify(unittest.TestCase):
    """字符分类。"""

    def test_ascii_letter(self):
        self.assertEqual(classify_char("a"), "latin")

    def test_cjk(self):
        self.assertEqual(classify_char("中"), "cjk")

    def test_kana(self):
        self.assertEqual(classify_char("け"), "kana")

    def test_hangul(self):
        self.assertEqual(classify_char("한"), "hangul")

    def test_cyrillic(self):
        self.assertEqual(classify_char("Ж"), "cyrillic")

    def test_control_char_penalised(self):
        self.assertEqual(classify_char("\x00"), "control")

    def test_replacement_char(self):
        self.assertEqual(classify_char("�"), "replacement")

    def test_newline_allowed(self):
        self.assertEqual(classify_char("\n"), "space")


class TestInferScript(unittest.TestCase):
    """语言归属推断。"""

    def test_chinese(self):
        self.assertEqual(infer_script(ZH), "zh-hans")

    def test_japanese_with_kana(self):
        self.assertEqual(infer_script(JA), "ja")

    def test_korean(self):
        self.assertEqual(infer_script(KO), "ko")

    def test_russian(self):
        self.assertEqual(infer_script(RU), "ru")

    def test_latin_default(self):
        self.assertEqual(infer_script("plain english"), "la")


class TestFileAPI(unittest.TestCase):
    """文件级 API。"""

    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "sample.txt")
        with open(self.path, "wb") as handle:
            handle.write(ZH.encode("gb18030"))

    def test_detect_file(self):
        result, _candidates = detect_file(self.path)
        self.assertEqual(result.encoding, "gb18030")

    def test_detect_file_explain(self):
        result, candidates = detect_file(self.path, explain=True)
        self.assertTrue(candidates)
        self.assertTrue(any(c.decodable for c in candidates))


if __name__ == "__main__":
    unittest.main(verbosity=2)
