"""把 AI 返回的文本解析成文档。"""
from __future__ import annotations

import json
import re
from typing import Any

from nano_banana.core.prompt.migrate import migrate_document
from nano_banana.core.prompt.schema import PromptSchema


class PromptParseError(ValueError):
    """AI 输出无法解析成文档。"""


def strip_code_fences(content: str) -> str:
    """剥离 AI 返回内容外层的 ```json / ``` 围栏。

    模型经常在 JSON 前后加 markdown 代码块标记（有时还带语言名或说明文字），
    直接 json.loads 会失败。
    """
    text = (content or "").strip()
    match = re.search(r"```[ \t]*[\w-]*[ \t]*\r?\n(.*?)\r?\n?[ \t]*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # 只有开头围栏没有闭合（流被截断等情况）
    text = re.sub(r"^```[ \t]*[\w-]*[ \t]*\r?\n?", "", text)
    text = re.sub(r"\r?\n?[ \t]*```$", "", text)
    return text.strip()


def parse_ai_document(content: str, schema: PromptSchema | None = None) -> dict[str, Any]:
    """AI 输出 → 当前结构的文档。容忍代码围栏和 JSON 前后的说明文字。"""
    text = strip_code_fences(content)
    if not text:
        raise PromptParseError("AI 没有返回内容")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as first_error:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise PromptParseError(f"AI 返回内容不是有效的 JSON: {first_error}") from first_error
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise PromptParseError(f"AI 返回内容不是有效的 JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise PromptParseError("AI 返回的 JSON 必须是对象")
    return migrate_document(data, schema)
