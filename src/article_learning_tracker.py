"""Build a sanitized article-learning CSV from local HAR files."""

from __future__ import annotations

import argparse
import base64
import binascii
import csv
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SENSITIVE_QUERY_KEYS = {
    "key",
    "pass_ticket",
    "uin",
    "sessionid",
    "exportkey",
    "appmsg_token",
    "wxtoken",
    "token",
    "access_token",
    "auth",
    "authorization",
}

COLUMNS = [
    "学习状态",
    "建议学习顺序",
    "原始编号",
    "文章标题",
    "发布日期",
    "建议分类",
    "难度",
    "优先级",
    "学习日期",
    "需要复习",
    "学习笔记",
    "原文链接",
]


@dataclass(frozen=True)
class Article:
    identity: str
    source_order: int | None
    title: str
    published_date: str
    url: str


@dataclass(frozen=True)
class ClassificationRule:
    category: str
    difficulty: str
    priority: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class ClassificationConfig:
    rules: tuple[ClassificationRule, ...]
    default_category: str = "未分类"
    default_difficulty: str = "待判断"
    default_priority: str = "中"


DEFAULT_CLASSIFICATION = ClassificationConfig(rules=())


def sanitize_url(raw_url: str) -> str:
    """Remove common authentication parameters while preserving public links."""
    try:
        parts = urlsplit(raw_url)
        clean_query = [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.lower() not in SENSITIVE_QUERY_KEYS
        ]
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(clean_query), parts.fragment)
        )
    except ValueError:
        return ""


def normalize_url_for_identity(raw_url: str) -> str:
    clean = sanitize_url(raw_url)
    try:
        parts = urlsplit(clean)
        ordered_query = sorted(parse_qsl(parts.query, keep_blank_values=True))
        return urlunsplit(
            (parts.scheme.lower(), parts.netloc.lower(), parts.path, urlencode(ordered_query), "")
        )
    except ValueError:
        return clean


def iter_article_lists(value: Any) -> Iterator[list[dict[str, Any]]]:
    """Find JSON arrays named article_list without depending on one site wrapper."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "article_list" and isinstance(child, list):
                yield [item for item in child if isinstance(item, dict)]
            else:
                yield from iter_article_lists(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_article_lists(child)


def parse_date(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        timestamp = int(value)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        text = str(value).strip()
        return text[:10] if len(text) >= 10 else text


def make_identity(item: dict[str, Any], clean_url: str) -> str:
    message_id = str(item.get("msgid", "")).strip()
    item_index = str(item.get("itemidx", item.get("idx", "1"))).strip()
    if message_id:
        source = f"message:{message_id}:{item_index}"
    else:
        source = f"url:{normalize_url_for_identity(clean_url)}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:20]


def article_from_item(item: dict[str, Any]) -> Article | None:
    title = str(item.get("title", "")).strip()
    clean_url = sanitize_url(str(item.get("url", "")).strip())
    if not title or not clean_url.startswith(("http://", "https://")):
        return None

    raw_order = item.get("pos_num", item.get("position"))
    try:
        source_order = int(raw_order) if raw_order not in (None, "") else None
    except (TypeError, ValueError):
        source_order = None
    if source_order is not None and source_order <= 0:
        source_order = None

    return Article(
        identity=make_identity(item, clean_url),
        source_order=source_order,
        title=title,
        published_date=parse_date(item.get("create_time", item.get("published_at"))),
        url=clean_url,
    )


def response_json(entry: dict[str, Any]) -> Any | None:
    content = entry.get("response", {}).get("content", {})
    text = content.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    if content.get("encoding") == "base64":
        mime_type = str(content.get("mimeType", "")).lower()
        if "json" not in mime_type and not mime_type.startswith("text/"):
            return None
        try:
            text = base64.b64decode(text, validate=True).decode("utf-8-sig")
        except (binascii.Error, UnicodeDecodeError):
            return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def extract_from_har(path: Path) -> list[Article]:
    with path.open("r", encoding="utf-8-sig") as handle:
        har = json.load(handle)

    articles: list[Article] = []
    for entry in har.get("log", {}).get("entries", []):
        payload = response_json(entry)
        if payload is None:
            continue
        for article_list in iter_article_lists(payload):
            for item in article_list:
                article = article_from_item(item)
                if article is not None:
                    articles.append(article)
    return articles


def load_classification_config(path: Path) -> ClassificationConfig:
    """Load user-defined keyword rules from a UTF-8 JSON file."""
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("分类配置的最外层必须是 JSON 对象")

    default = payload.get("default", {})
    if not isinstance(default, dict):
        raise ValueError("default 必须是 JSON 对象")

    def required_text(value: Any, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} 必须是非空文本")
        return value.strip()

    rules_payload = payload.get("rules", [])
    if not isinstance(rules_payload, list):
        raise ValueError("rules 必须是 JSON 数组")

    rules: list[ClassificationRule] = []
    for index, item in enumerate(rules_payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index} 条规则必须是 JSON 对象")
        keywords = item.get("keywords")
        if not isinstance(keywords, list) or not keywords:
            raise ValueError(f"第 {index} 条规则的 keywords 必须是非空数组")
        clean_keywords = tuple(
            required_text(keyword, f"第 {index} 条规则的关键词")
            for keyword in keywords
        )
        rules.append(
            ClassificationRule(
                category=required_text(item.get("category"), f"第 {index} 条规则的 category"),
                difficulty=required_text(item.get("difficulty"), f"第 {index} 条规则的 difficulty"),
                priority=required_text(item.get("priority"), f"第 {index} 条规则的 priority"),
                keywords=clean_keywords,
            )
        )

    return ClassificationConfig(
        rules=tuple(rules),
        default_category=required_text(default.get("category", "未分类"), "default.category"),
        default_difficulty=required_text(default.get("difficulty", "待判断"), "default.difficulty"),
        default_priority=required_text(default.get("priority", "中"), "default.priority"),
    )


def classify(
    title: str, config: ClassificationConfig = DEFAULT_CLASSIFICATION
) -> tuple[str, str, str]:
    text = title.lower()
    for rule in config.rules:
        if any(keyword.lower() in text for keyword in rule.keywords):
            return rule.category, rule.difficulty, rule.priority
    return config.default_category, config.default_difficulty, config.default_priority


def deduplicate(articles: Iterable[Article]) -> list[Article]:
    unique: dict[str, Article] = {}
    for article in articles:
        unique[article.identity] = article
    return list(unique.values())


def learning_sort_key(
    article: Article, config: ClassificationConfig = DEFAULT_CLASSIFICATION
) -> tuple[int, str, int]:
    category, _, _ = classify(article.title, config)
    category_order = {
        rule.category: index for index, rule in enumerate(config.rules, start=1)
    }
    default_order = len(category_order) + 1
    return (category_order.get(category, default_order), article.published_date, article.source_order or 10**9)


def write_csv(
    articles: list[Article],
    output_path: Path,
    config: ClassificationConfig = DEFAULT_CLASSIFICATION,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(articles, key=lambda article: learning_sort_key(article, config))
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for learning_order, article in enumerate(ordered, start=1):
            category, difficulty, priority = classify(article.title, config)
            writer.writerow(
                {
                    "学习状态": "未学习",
                    "建议学习顺序": learning_order,
                    "原始编号": article.source_order or "",
                    "文章标题": article.title,
                    "发布日期": article.published_date,
                    "建议分类": category,
                    "难度": difficulty,
                    "优先级": priority,
                    "学习日期": "",
                    "需要复习": "否",
                    "学习笔记": "",
                    "原文链接": article.url,
                }
            )


def summarize(articles: list[Article]) -> str:
    positions = sorted(
        article.source_order for article in articles if article.source_order is not None
    )
    if not positions:
        return f"生成 {len(articles)} 篇唯一文章；源数据没有可用编号。"
    present = set(positions)
    missing = [value for value in range(positions[0], positions[-1] + 1) if value not in present]
    missing_text = ",".join(map(str, missing[:20]))
    if len(missing) > 20:
        missing_text += ",..."
    return (
        f"生成 {len(articles)} 篇唯一文章；编号范围 {positions[0]}–{positions[-1]}；"
        f"范围内缺号：{missing_text or '无'}。"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="从本地 HAR 生成脱敏、去重的文章学习 CSV。"
    )
    parser.add_argument("--input", nargs="+", type=Path, required=True, help="一个或多个 HAR 文件")
    parser.add_argument("--output", type=Path, required=True, help="输出 CSV 路径")
    parser.add_argument(
        "--rules",
        type=Path,
        help="可选的 JSON 分类规则；不提供时所有文章标记为未分类",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    missing_files = [str(path) for path in args.input if not path.is_file()]
    if missing_files:
        print(f"找不到输入文件：{', '.join(missing_files)}", file=sys.stderr)
        return 2

    try:
        config = (
            load_classification_config(args.rules)
            if args.rules is not None
            else DEFAULT_CLASSIFICATION
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"分类配置无效：{error}", file=sys.stderr)
        return 2

    extracted: list[Article] = []
    for path in args.input:
        extracted.extend(extract_from_har(path))
    articles = deduplicate(extracted)
    write_csv(articles, args.output, config)
    print(summarize(articles))
    print(f"学习清单已保存到：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
