"""文档差异与选择性应用。AI 修改的「逐项勾选」两端共用。"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from nano_banana.core.prompt.document import deepcopy_json, delete_at_path, set_at_path

ADDED = "added"
REMOVED = "removed"
CHANGED = "changed"


@dataclass(frozen=True)
class Change:
    path: tuple[str, ...]
    kind: str
    old: Any = None
    new: Any = None

    @property
    def label(self) -> str:
        return " > ".join(self.path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": list(self.path),
            "label": self.label,
            "kind": self.kind,
            "old": self.old,
            "new": self.new,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Change":
        path = raw.get("path")
        kind = raw.get("kind")
        if not isinstance(path, list) or not path or not all(isinstance(k, str) for k in path):
            raise ValueError("change.path 必须是非空字符串数组")
        if kind not in (ADDED, REMOVED, CHANGED):
            raise ValueError(f"未知的 change.kind: {kind}")
        return cls(path=tuple(path), kind=kind, old=raw.get("old"), new=raw.get("new"))


def diff_documents(old: dict[str, Any] | None, new: dict[str, Any] | None) -> list[Change]:
    """逐叶子比较。「缺失」和「空值」视为相同，避免满屏无意义差异。"""
    changes: list[Change] = []
    _walk(old or {}, new or {}, (), changes)
    return changes


def apply_changes(base: dict[str, Any] | None, changes: Iterable[Change]) -> dict[str, Any]:
    """把选中的差异应用到 base 的副本上。"""
    result = deepcopy_json(base or {})
    for change in changes:
        if change.kind == REMOVED:
            delete_at_path(result, change.path)
        else:
            set_at_path(result, change.path, deepcopy_json(change.new))
    return result


def _walk(old: dict[str, Any], new: dict[str, Any], prefix: tuple[str, ...], out: list[Change]) -> None:
    keys = list(old)
    keys.extend(key for key in new if key not in old)
    for key in keys:
        path = prefix + (key,)
        in_old, in_new = key in old, key in new
        old_value, new_value = old.get(key), new.get(key)

        if isinstance(old_value, dict) and isinstance(new_value, dict):
            _walk(old_value, new_value, path, out)
            continue
        if _is_empty(old_value) and _is_empty(new_value):
            continue
        if not in_new:
            out.append(Change(path, REMOVED, old=old_value))
        elif not in_old:
            out.append(Change(path, ADDED, new=new_value))
        elif old_value != new_value:
            out.append(Change(path, CHANGED, old=old_value, new=new_value))


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}
