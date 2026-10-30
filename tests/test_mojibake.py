# -*- coding: utf-8 -*-
"""乱码检测与修复的单元测试。

除了"能不能修好"，这里同样重视"不该修的时候别乱修"——
误把正常文本改坏，比修不好更糟糕。
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from charsetseer import (  # noqa: E402
    looks_like_mojibake,
    mojibake_likelihood,
    naturalness,
    repair,
    repair_bytes,
)

ZH = "中文编码检测工具"
ZH_LONG = "我们经常遇到文件乱码问题，需要先判断编码再打开。"
JA = "文字化け検出"
RU = "Это русский текст"
FR = "Café déjà vu"


class TestRepairMojibake(unittest.TestCase):
    """典型乱码的修复。"""

    def test_utf8_read_as_latin1(self):
        broken = ZH.encode("utf-8").decode("latin-1")
        result = repair(broken)
        self.assertTrue(result.ok)
        self.assertEqual(result.repaired, ZH)
        self.assertEqual(result.true_encoding, "utf-8")

    def test_gbk_read_as_latin1(self):
        broken = ZH.encode("gb18030").decode("latin-1")
        result = repair(broken)
        self.assertTrue(result.ok)
        self.assertEqual(result.repaired, ZH)

    def test_utf8_french_read_as_latin1(self):
        broken = FR.encode("utf-8").decode("latin-1")
        result = repair(broken)
        self.assertTrue(result.ok)
        self.assertEqual(result.repaired, FR)

    def test_utf8_japanese_read_as_latin1(self):
        broken = JA.encode("utf-8").decode("latin-1")
        result = repair(broken)
        self.assertTrue(result.ok)
        self.assertEqual(result.repaired, JA)

    def test_utf8_russian_read_as_latin1(self):
        broken = RU.encode("utf-8").decode("latin-1")
        result = repair(broken)
        self.assertTrue(result.ok)
        self.assertEqual(result.repaired, RU)

    def test_long_chinese(self):
        broken = ZH_LONG.encode("utf-8").decode("latin-1")
        result = repair(broken)
        self.assertTrue(result.ok)
        self.assertEqual(result.repaired, ZH_LONG)

    def test_repair_bytes_helper(self):
        result = repair_bytes(ZH.encode("utf-8"), preferred="latin-1")
        self.assertTrue(result.ok)
        self.assertEqual(result.repaired, ZH)


class TestDoNotTouchHealthyText(unittest.TestCase):
    """正常文本必须原样返回 —— 这是易用错的方向。"""

    def test_normal_chinese_untouched(self):
        text = "这是一段完全正常的中文文本，不应该被修改。"
        self.assertFalse(repair(text).ok)

    def test_normal_english_untouched(self):
        text = "This is perfectly normal English text."
        self.assertFalse(repair(text).ok)

    def test_empty_string(self):
        self.assertFalse(repair("").ok)

    def test_repaired_equals_original_when_not_ok(self):
        text = "正常的中文内容"
        result = repair(text)
        self.assertEqual(result.repaired, text)


class TestLikelihood(unittest.TestCase):
    """乱码可能性评估。"""

    def test_broken_text_high_likelihood(self):
        broken = ZH.encode("utf-8").decode("latin-1")
        self.assertGreater(mojibake_likelihood(broken), 0.5)

    def test_healthy_text_low_likelihood(self):
        self.assertLess(mojibake_likelihood("这是一段正常的中文"), 0.3)

    def test_looks_like_mojibake(self):
        broken = ZH.encode("utf-8").decode("latin-1")
        self.assertTrue(looks_like_mojibake(broken))

    def test_healthy_not_mojibake(self):
        self.assertFalse(looks_like_mojibake("完全正常的中文文本"))

    def test_likelihood_bounded(self):
        samples = ("", "abc", ZH, "异常\x00文本\U0001F600混合")
        for text in samples:
            value = mojibake_likelihood(text)
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)


class TestNaturalness(unittest.TestCase):
    """语言中立自然度评分。"""

    def test_healthy_text_scores_high(self):
        self.assertGreater(naturalness(ZH), 0.8)

    def test_english_scores_high(self):
        self.assertGreater(naturalness("Normal english sentence."), 0.8)

    def test_control_chars_penalised(self):
        self.assertLess(naturalness("文本\x00\x01"), naturalness("文本"))

    def test_rare_hanzi_penalised(self):
        # 罕用汉字（乱码的典型产物）应显著拉低分数
        self.assertLess(naturalness("鏂囧瓧"), naturalness(ZH))


if __name__ == "__main__":
    unittest.main(verbosity=2)
