"""结构化提示词文档：flatten / nest / subset / merge，以及 overlay 读写。

文档 = schema 字段 + overlay（反向提示词 / 特别要求 / 角色线稿）。
它是预设、草稿、各交互口之间交换的唯一格式；最终发给模型的文本由 render 生成。
"""
from __future__ import annotations

from typing import Any

from nano_banana.core.prompt.schema import (
    PromptField,
    PromptSchema,
    get_schema,
    overlay_by_id,
)

MISSING = object()

LINE_ART_ENABLED_KEY = "启用"
LINE_ART_PROMPT_KEY = "提示词"


def get_at_path(data: Any, path: tuple[str, ...] | list[str], default: Any = MISSING) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def set_at_path(data: dict[str, Any], path: tuple[str, ...] | list[str], value: Any) -> dict[str, Any]:
    if not path:
        raise ValueError("path 不能为空")
    target = data
    for key in path[:-1]:
        existing = target.get(key)
        if not isinstance(existing, dict):
            existing = {}
            target[key] = existing
        target = existing
    target[path[-1]] = value
    return data


def delete_at_path(data: dict[str, Any], path: tuple[str, ...] | list[str]) -> bool:
    if not path:
        return False
    parent = get_at_path(data, path[:-1], None) if len(path) > 1 else data
    if not isinstance(parent, dict) or path[-1] not in parent:
        return False
    del parent[path[-1]]
    return True


def encode_field_value(field: PromptField, value: Any) -> Any:
    if field.type != "string_list":
        return "" if value is None else value
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def decode_field_value(field: PromptField, value: Any) -> str:
    if field.type == "string_list":
        if isinstance(value, list):
            return ", ".join(str(item) for item in value if item)
        return str(value) if value else ""
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)


def flatten(
    data: dict[str, Any] | None,
    schema: PromptSchema | None = None,
    *,
    include_missing: bool = False,
) -> dict[str, Any]:
    """嵌套 JSON → {field_id: widget 字符串}。"""
    schema = schema or get_schema()
    source = data or {}
    result: dict[str, Any] = {}
    for field in schema.iter_fields():
        value = get_at_path(source, field.path)
        if value is MISSING:
            if include_missing:
                result[field.id] = ""
            continue
        result[field.id] = decode_field_value(field, value)
    return result


def nest(
    flat: dict[str, Any] | None,
    schema: PromptSchema | None = None,
    *,
    include_empty: bool = True,
) -> dict[str, Any]:
    """{field_id 或 widget_key: value} → 对外嵌套 JSON。"""
    schema = schema or get_schema()
    values = flat or {}
    result: dict[str, Any] = {}
    for field in schema.iter_fields():
        if field.id in values:
            raw = values[field.id]
        elif field.widget_key in values:
            raw = values[field.widget_key]
        elif include_empty:
            raw = [] if field.type == "string_list" else ""
        else:
            continue
        encoded = encode_field_value(field, raw)
        if field.type == "string_list" and not encoded:
            encoded = [str(raw)] if raw else []
        set_at_path(result, field.path, encoded)
    return result


def subset(
    data: dict[str, Any] | None,
    category_id: str,
    schema: PromptSchema | None = None,
) -> dict[str, Any]:
    """抽出一个分类的嵌套切片，供分类预设使用。"""
    schema = schema or get_schema()
    source = data or {}
    result: dict[str, Any] = {}
    for field in schema.get_category(category_id).fields:
        value = get_at_path(source, field.path)
        if value is MISSING:
            continue
        set_at_path(result, field.path, value)
    return result


def apply_partial(dst: dict[str, Any] | None, src: dict[str, Any] | None) -> dict[str, Any]:
    """把 src 中出现的键深合并进 dst，未出现的键保持不动。"""
    result = {} if dst is None else deepcopy_json(dst)
    _merge(result, src or {})
    return result


def order_document(
    data: dict[str, Any] | None,
    schema: PromptSchema | None = None,
) -> dict[str, Any]:
    schema = schema or get_schema()
    source = data or {}
    ordered: dict[str, Any] = {}
    for key in schema.root_order:
        if key in source:
            ordered[key] = source[key]
    for key, value in source.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def build_document(
    fields: dict[str, Any] | None,
    schema: PromptSchema | None = None,
    *,
    negative_prompt: str | None = None,
    special_requirement: str | None = None,
    line_art_prompt: str | None = None,
) -> dict[str, Any]:
    """表单值 → 完整文档。overlay 传 None 表示未启用，不写入文档。"""
    schema = schema or get_schema()
    data = nest(fields, schema)
    if negative_prompt is not None:
        set_at_path(data, overlay_by_id("negativePrompt", schema).path, negative_prompt)
    if special_requirement is not None:
        set_at_path(
            data, overlay_by_id("specialRequirement", schema).path, special_requirement
        )
    if line_art_prompt is not None:
        set_at_path(
            data,
            overlay_by_id("lineArt", schema).path,
            {LINE_ART_ENABLED_KEY: True, LINE_ART_PROMPT_KEY: line_art_prompt},
        )
    return order_document(data, schema)


def get_special_requirement(data: dict[str, Any] | None, schema: PromptSchema | None = None) -> str:
    value = get_at_path(data or {}, overlay_by_id("specialRequirement", schema).path, "")
    return value.strip() if isinstance(value, str) else ""


def get_line_art(
    data: dict[str, Any] | None, schema: PromptSchema | None = None
) -> tuple[bool, str]:
    """返回 (是否启用线稿模式, 线稿提示词)。"""
    value = get_at_path(data or {}, overlay_by_id("lineArt", schema).path, None)
    if not isinstance(value, dict) or not value.get(LINE_ART_ENABLED_KEY):
        return False, ""
    prompt = value.get(LINE_ART_PROMPT_KEY)
    return True, prompt.strip() if isinstance(prompt, str) else ""


def strip_ui_only(data: dict[str, Any] | None, schema: PromptSchema | None = None) -> dict[str, Any]:
    """去掉 ui_only overlay，得到可以交给模型的 JSON。"""
    schema = schema or get_schema()
    result = deepcopy_json(data or {})
    for overlay in schema.overlays:
        if overlay.ui_only:
            delete_at_path(result, overlay.path)
    return result


def deepcopy_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: deepcopy_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [deepcopy_json(item) for item in value]
    return value


def _merge(dst: dict[str, Any], src: dict[str, Any]) -> None:
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            _merge(dst[key], value)
        else:
            dst[key] = deepcopy_json(value)
