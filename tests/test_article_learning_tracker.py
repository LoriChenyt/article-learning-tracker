from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
