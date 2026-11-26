"""旧版文档格式兼容。全仓库只此一份，所有入口（预设、草稿、AI 输出）都走这里。"""
from __future__ import annotations

from typing import Any

from nano_banana.core.prompt.document import (
    MISSING,
    deepcopy_json,
    get_at_path,
    set_at_path,
)
from nano_banana.core.prompt.schema import PromptSchema, get_schema, overlay_by_id

_LEGACY_NEGATIVE_KEYS = ("禁止元素", "禁止风格")


def normalize_negative_prompt(value: Any) -> str:
    """当前字符串格式，或旧版 {禁止元素, 禁止风格} 分组 → 可编辑文本。"""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""

    values: list[Any] = []
    for key in _LEGACY_NEGATIVE_KEYS:
        item = value.get(key, [])
        values.extend(item if isinstance(item, list) else [item])
    return ", ".join(str(item) for item in values if item)


def migrate_document(
    data: dict[str, Any] | None, schema: PromptSchema | None = None
) -> dict[str, Any]:
    """把任意历史版本的文档升级到当前结构。不修改入参，只动出现了的键。"""
    schema = schema or get_schema()
    result = deepcopy_json(data) if isinstance(data, dict) else {}

    negative_path = overlay_by_id("negativePrompt", schema).path
    negative = get_at_path(result, negative_path)
    if negative is not MISSING and not isinstance(negative, str):
        set_at_path(result, negative_path, normalize_negative_prompt(negative))

    # 旧版「表情与动作」是单个字符串，现在拆成 情绪 / 动作 两个字段
    try:
        emotion_path = schema.get_field("emotion").path
        action_path = schema.get_field("action").path
    except KeyError:
        return result
    expression_path = action_path[:-1]
    expression = get_at_path(result, expression_path)
    if isinstance(expression, str):
        set_at_path(
            result,
            expression_path,
            {emotion_path[-1]: "", action_path[-1]: expression},
        )

    return result
