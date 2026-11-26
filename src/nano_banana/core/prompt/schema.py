"""提示词字段 schema：唯一真源。"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

import yaml

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.yaml"


@dataclass(frozen=True)
class PromptField:
    id: str
    label: str
    path: tuple[str, ...]
    widget_key: str
    options_key: str
    widget: str = "combo"
    type: str = "string"
    example: Any = ""
    optional: bool = False

    @property
    def path_list(self) -> list[str]:
        return list(self.path)


@dataclass(frozen=True)
class PromptCategory:
    id: str
    label: str
    description: str = ""
    color_class: str = ""
    two_column: bool = False
    fields: tuple[PromptField, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PromptOverlay:
    id: str
    label: str
    path: tuple[str, ...]
    optional: bool = True
    default: str = ""
    options_key: str = ""
    ui_only: bool = False


class PromptSchema:
    def __init__(self, raw: dict[str, Any]):
        self.version = int(raw.get("version") or 1)
        self.categories: tuple[PromptCategory, ...] = tuple(
            _parse_category(item) for item in raw.get("categories") or []
        )
        self.overlays: tuple[PromptOverlay, ...] = tuple(
            _parse_overlay(item) for item in raw.get("overlays") or []
        )
        self.root_order: tuple[str, ...] = tuple(raw.get("root_order") or [])
        self._fields_by_id = {field.id: field for field in self.iter_fields()}
        self._fields_by_widget_key = {
            field.widget_key: field for field in self.iter_fields()
        }

    def iter_fields(self) -> Iterator[PromptField]:
        for category in self.categories:
            yield from category.fields

    @property
    def fields(self) -> tuple[PromptField, ...]:
        return tuple(self.iter_fields())

    @property
    def field_ids(self) -> tuple[str, ...]:
        return tuple(field.id for field in self.iter_fields())

    @property
    def widget_keys(self) -> tuple[str, ...]:
        return tuple(field.widget_key for field in self.iter_fields())

    @property
    def category_ids(self) -> tuple[str, ...]:
        return tuple(category.id for category in self.categories)

    def get_category(self, category_id: str) -> PromptCategory:
        for category in self.categories:
            if category.id == category_id:
                return category
        raise KeyError(f"未知分类: {category_id}")

    def get_field(self, field_id: str) -> PromptField:
        try:
            return self._fields_by_id[field_id]
        except KeyError as exc:
            raise KeyError(f"未知字段: {field_id}") from exc

    def get_field_by_widget_key(self, widget_key: str) -> PromptField:
        try:
            return self._fields_by_widget_key[widget_key]
        except KeyError as exc:
            raise KeyError(f"未知控件字段: {widget_key}") from exc

    def category_paths(self, category_id: str) -> tuple[tuple[str, ...], ...]:
        return tuple(field.path for field in self.get_category(category_id).fields)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "categories": [
                {
                    "id": category.id,
                    "label": category.label,
                    "description": category.description,
                    "color_class": category.color_class,
                    "two_column": category.two_column,
                    "fields": [
                        {
                            "id": field.id,
                            "label": field.label,
                            "path": list(field.path),
                            "widget_key": field.widget_key,
                            "options_key": field.options_key,
                            "widget": field.widget,
                            "type": field.type,
                        }
                        for field in category.fields
                    ],
                }
                for category in self.categories
            ],
            "overlays": [
                {
                    "id": overlay.id,
                    "label": overlay.label,
                    "path": list(overlay.path),
                    "optional": overlay.optional,
                    "default": overlay.default,
                    "options_key": overlay.options_key,
                    "ui_only": overlay.ui_only,
                }
                for overlay in self.overlays
            ],
            "root_order": list(self.root_order),
        }

    def example_values(self) -> dict[str, Any]:
        return {field.id: field.example for field in self.iter_fields() if field.example}


def _parse_field(raw: dict[str, Any]) -> PromptField:
    path = tuple(raw["path"])
    widget_key = raw.get("widget_key") or raw["id"]
    return PromptField(
        id=raw["id"],
        label=raw.get("label") or widget_key,
        path=path,
        widget_key=widget_key,
        options_key=raw.get("options_key") or widget_key,
        widget=raw.get("widget") or "combo",
        type=raw.get("type") or "string",
        example=raw.get("example") or "",
        optional=bool(raw.get("optional")),
    )


def _parse_category(raw: dict[str, Any]) -> PromptCategory:
    return PromptCategory(
        id=raw["id"],
        label=raw.get("label") or raw["id"],
        description=raw.get("description") or "",
        color_class=raw.get("color_class") or raw["id"],
        two_column=bool(raw.get("two_column")),
        fields=tuple(_parse_field(item) for item in raw.get("fields") or []),
    )


def _parse_overlay(raw: dict[str, Any]) -> PromptOverlay:
    return PromptOverlay(
        id=raw["id"],
        label=raw.get("label") or raw["id"],
        path=tuple(raw["path"]),
        optional=raw.get("optional", True),
        default=raw.get("default") or "",
        options_key=raw.get("options_key") or "",
        ui_only=bool(raw.get("ui_only")),
    )


def load_schema(path: Path | None = None) -> PromptSchema:
    schema_path = Path(path) if path else SCHEMA_PATH
    with schema_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError("schema.yaml 必须是 JSON/YAML 对象")
    return PromptSchema(raw)


@lru_cache(maxsize=1)
def get_schema() -> PromptSchema:
    return load_schema()


def overlay_by_id(overlay_id: str, schema: PromptSchema | None = None) -> PromptOverlay:
    schema = schema or get_schema()
    for overlay in schema.overlays:
        if overlay.id == overlay_id:
            return overlay
    raise KeyError(f"未知 overlay: {overlay_id}")


def default_negative_prompt(schema: PromptSchema | None = None) -> str:
    return overlay_by_id("negativePrompt", schema).default
