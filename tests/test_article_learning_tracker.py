from __future__ import annotations

import importlib.util
import base64
import json
import sys
import tempfile
import unittest
from csv import DictReader
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "article_learning_tracker.py"
SPEC = importlib.util.spec_from_file_location("article_learning_tracker", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ArticleLearningTrackerTests(unittest.TestCase):
    def test_sanitize_url_removes_session_parameters(self) -> None:
        raw = (
            "https://example.com/article?id=7&key=secret&pass_ticket=ticket"
            "&uin=123&sessionid=session&exportkey=export"
        )
        clean = MODULE.sanitize_url(raw)
        self.assertEqual(clean, "https://example.com/article?id=7")

    def test_extract_and_deduplicate(self) -> None:
        item = {
            "pos_num": "12",
            "title": "虚构的 Python 入门文章",
            "create_time": "1704067200",
            "url": "https://example.com/article?mid=100&key=secret",
            "msgid": "100",
            "itemidx": "1",
        }
        har = {
            "log": {
                "entries": [
                    {"response": {"content": {"text": json.dumps({"result": {"article_list": [item, item]}})}}}
                ]
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(har), encoding="utf-8")
            extracted = MODULE.extract_from_har(path)

        unique = MODULE.deduplicate(extracted)
        self.assertEqual(len(extracted), 2)
        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0].source_order, 12)
        self.assertNotIn("secret", unique[0].url)

    def test_non_article_json_is_ignored(self) -> None:
        har = {"log": {"entries": [{"response": {"content": {"text": "{\"ok\": true}"}}}]}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(har), encoding="utf-8")
            self.assertEqual(MODULE.extract_from_har(path), [])

    def test_base64_json_response_is_extracted_and_sanitized(self) -> None:
        payload = {
            "article_list": [
                {
                    "pos_num": 7,
                    "title": "虚构的 Base64 示例文章",
                    "create_time": "1704067200",
                    "url": "https://example.com/article?id=7&key=fake-secret",
                    "msgid": "base64-demo",
                }
            ]
        }
        encoded = base64.b64encode(
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        har = {
            "log": {
                "entries": [
                    {
                        "response": {
                            "content": {
                                "text": encoded,
                                "encoding": "base64",
                                "mimeType": "application/json",
                            }
                        }
                    }
                ]
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(har), encoding="utf-8")
            articles = MODULE.extract_from_har(path)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].source_order, 7)
        self.assertEqual(articles[0].url, "https://example.com/article?id=7")

    def test_invalid_base64_response_is_ignored(self) -> None:
        entry = {
            "response": {
                "content": {
                    "text": "not-valid-base64!",
                    "encoding": "base64",
                    "mimeType": "application/json",
                }
            }
        }
        self.assertIsNone(MODULE.response_json(entry))

    def test_base64_binary_response_is_ignored(self) -> None:
        entry = {
            "response": {
                "content": {
                    "text": base64.b64encode(b"image-data").decode("ascii"),
                    "encoding": "base64",
                    "mimeType": "image/png",
                }
            }
        }
        self.assertIsNone(MODULE.response_json(entry))

    def test_user_defined_rules_control_classification(self) -> None:
        payload = {
            "default": {"category": "其他", "difficulty": "待判断", "priority": "低"},
            "rules": [
                {
                    "category": "英语学习",
                    "difficulty": "入门",
                    "priority": "高",
                    "keywords": ["英语", "vocabulary"],
                },
                {
                    "category": "科研方法",
                    "difficulty": "进阶",
                    "priority": "中",
                    "keywords": ["论文"],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            config = MODULE.load_classification_config(path)

        self.assertEqual(MODULE.classify("英语词汇复习", config), ("英语学习", "入门", "高"))
        self.assertEqual(MODULE.classify("旅行随笔", config), ("其他", "待判断", "低"))

    def test_write_csv_uses_custom_rules(self) -> None:
        config = MODULE.ClassificationConfig(
            rules=(
                MODULE.ClassificationRule("读书", "入门", "高", ("书单",)),
            ),
            default_category="其他",
            default_difficulty="待判断",
            default_priority="低",
        )
        article = MODULE.Article("id", 1, "年度书单", "2026-01-01", "https://example.com/a")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "articles.csv"
            MODULE.write_csv([article], output, config)
            with output.open("r", encoding="utf-8-sig", newline="") as handle:
                row = next(DictReader(handle))

        self.assertEqual(row["建议分类"], "读书")
        self.assertEqual(row["难度"], "入门")
        self.assertEqual(row["优先级"], "高")

    def test_invalid_rules_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.json"
            path.write_text('{"rules": [{"category": "读书", "keywords": []}]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "keywords"):
                MODULE.load_classification_config(path)


if __name__ == "__main__":
    unittest.main()
