"""文档 → 最终发给生图模型的文本。两端共用，只此一份。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from nano_banana.core.prompt.document import (
    get_line_art,
    get_special_requirement,
    order_document,
    strip_ui_only,
)
from nano_banana.core.prompt.schema import PromptSchema, get_schema

MODE_JSON = "json"
MODE_LINE_ART = "line_art"

_SPECIAL_PREFIX = {
    MODE_JSON: "\n\n特别要求：",
    MODE_LINE_ART: "\n\n额外要求：",
}


@dataclass(frozen=True)
class RenderedPrompt:
    text: str
    mode: str
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "mode": self.mode,
            "payload": self.payload,
            "is_empty": self.is_empty,
        }


def prompt_payload(data: dict[str, Any] | None, schema: PromptSchema | None = None) -> dict[str, Any]:
    """模型可见的 JSON 部分：去掉 ui_only overlay，并按 schema 排序。"""
    schema = schema or get_schema()
    return order_document(strip_ui_only(data, schema), schema)


def payload_json(data: dict[str, Any] | None, schema: PromptSchema | None = None) -> str:
    return json.dumps(prompt_payload(data, schema), ensure_ascii=False, indent=2)


def render_prompt(data: dict[str, Any] | None, schema: PromptSchema | None = None) -> RenderedPrompt:
    """渲染规则：

    - 线稿模式：只用线稿提示词，结构化字段全部忽略；
    - 普通模式：模型可见 JSON；文档里什么都没有时正文为空（而不是 "{}"）；
    - 特别要求不进 JSON，追加在正文之后；正文为空时不单独发送。
    """
    schema = schema or get_schema()
    payload = prompt_payload(data, schema)
    special = get_special_requirement(data, schema)
    line_art_enabled, line_art_prompt = get_line_art(data, schema)

    if line_art_enabled:
        mode, body = MODE_LINE_ART, line_art_prompt
    else:
        mode = MODE_JSON
        body = json.dumps(payload, ensure_ascii=False, indent=2) if payload else ""

    if special and body:
        body += _SPECIAL_PREFIX[mode] + special
    return RenderedPrompt(text=body, mode=mode, payload=payload)
