#!/usr/bin/env python3
"""Tests for score_routing.classify on expected-"ask" cases. Run: python3 tasks/hep-research/scripts/test_score_routing.py"""
import unittest

from score_routing import classify


def trace(result):
    return {"case": {"expected_primary": "ask"}, "skills_invoked": [], "subtype": "success", "result": result}


class AskDetection(unittest.TestCase):
    def test_question_marks(self):
        self.assertEqual(classify(trace("Which two experiments?"))[0], "pass")
        self.assertEqual(classify(trace("是哪兩個實驗？"))[0], "pass")

    def test_chinese_request_without_question_mark(self):
        # the run-4 underspec-2 answer, shortened
        self.assertEqual(classify(trace("工作目錄是空的。\n\n請你提供下列任一項：\n- 兩個實驗結果的檔案路徑。"))[0], "pass")
        self.assertEqual(classify(trace("请提供两个实验结果的文件路径。"))[0], "pass")

    def test_statement_without_request_fails(self):
        self.assertEqual(classify(trace("兩個實驗的結果一致，差異在誤差範圍內。"))[0], "fail")
        self.assertEqual(classify(trace("The two results agree within uncertainties."))[0], "fail")


if __name__ == "__main__":
    unittest.main()
