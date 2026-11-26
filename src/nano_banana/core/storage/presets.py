"""预设存取：整套预设 + 分类预设。

用户目录是唯一的读写位置。包内的内置预设是只读种子：每个内置文件只会被
复制到用户目录一次（记在 .seeded.json 里），用户删掉后不会再长回来，
新版本新增的内置预设则会自动出现。
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from nano_banana.core.storage.files import locked, read_json, write_json

CATEGORY_DIR = "categories"
SEED_MARKER = ".seeded.json"
_NAME_EXTRA_CHARS = frozenset(" -_（）()")
_SCOPE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_-")


def safe_preset_name(name: str) -> str:
    """去掉文件名里不安全的字符。结果永远不含路径分隔符或 `.`。"""
    return "".join(
        c for c in (name or "") if c.isalnum() or c in _NAME_EXTRA_CHARS
    ).strip()


class PresetStore:
    def __init__(self, user_dir: Path, builtin_dir: Path | None = None):
        self.user_dir = Path(user_dir)
        self.builtin_dir = Path(builtin_dir) if builtin_dir else None
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self._seed_builtin()

    # ---------- 整套预设 ----------

    def list_all(self) -> list[dict[str, Any]]:
        """按修改时间倒序返回 [{name, path, modified_time}]。"""
        return _list_dir(self.user_dir)

    def load(self, name: str) -> dict[str, Any] | None:
        return _load(self._file(self.user_dir, name))

    def save(self, name: str, data: dict[str, Any]) -> str | None:
        """保存并返回实际使用的名称（清理过非法字符）；失败返回 None。"""
        if not isinstance(data, dict):
            return None
        safe_name = safe_preset_name(name) or f"preset_{datetime.now():%Y%m%d_%H%M%S}"
        return safe_name if _save(self.user_dir / f"{safe_name}.json", data) else None

    def delete(self, name: str) -> bool:
        return _delete(self._file(self.user_dir, name))

    def rename(self, old_name: str, new_name: str) -> bool:
        old_path = self._file(self.user_dir, old_name)
        new_path = self._file(self.user_dir, new_name)
        if old_path is None or new_path is None:
            return False
        try:
            if old_path.exists() and not new_path.exists():
                old_path.rename(new_path)
                return True
        except OSError as exc:
            logger.warning(f"重命名预设失败: {exc}")
        return False

    # ---------- 分类预设 ----------

    def list_category(self, scope: str) -> list[dict[str, Any]]:
        category_dir = self._category_dir(scope)
        if category_dir is None or not category_dir.exists():
            return []
        return _list_dir(category_dir)

    def load_category(self, scope: str, name: str) -> dict[str, Any] | None:
        return _load(self._file(self._category_dir(scope), name))

    def save_category(self, scope: str, name: str, data: dict[str, Any]) -> str | None:
        category_dir = self._category_dir(scope)
        safe_name = safe_preset_name(name)
        if category_dir is None or not safe_name or not isinstance(data, dict):
            return None
        return safe_name if _save(category_dir / f"{safe_name}.json", data) else None

    def delete_category(self, scope: str, name: str) -> bool:
        return _delete(self._file(self._category_dir(scope), name))

    # ---------- 内部 ----------

    def _category_dir(self, scope: str) -> Path | None:
        """拒绝可能逃逸预设目录的 scope。"""
        if not scope or any(c not in _SCOPE_CHARS for c in scope):
            return None
        return self.user_dir / CATEGORY_DIR / scope

    @staticmethod
    def _file(directory: Path | None, name: str) -> Path | None:
        """name 必须是单个文件名，杜绝 `../`、绝对路径、盘符之类的路径穿越。"""
        if directory is None or not _is_plain_filename(name):
            return None
        return directory / f"{name}.json"

    def _seed_builtin(self) -> None:
        if self.builtin_dir is None or not self.builtin_dir.is_dir():
            return
        marker = self.user_dir / SEED_MARKER
        try:
            with locked(marker):
                seeded = set(_read_seed_marker(marker))
                added = False
                for source in sorted(self.builtin_dir.rglob("*.json")):
                    relative = source.relative_to(self.builtin_dir).as_posix()
                    if relative in seeded:
                        continue
                    target = self.user_dir / relative
                    if not target.exists():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(source, target)
                    seeded.add(relative)
                    added = True
                if added:
                    write_json(marker, sorted(seeded))
        except (OSError, TimeoutError) as exc:
            logger.warning(f"初始化内置预设失败: {exc}")


def _is_plain_filename(name: Any) -> bool:
    if not isinstance(name, str) or not name.strip() or name.startswith("."):
        return False
    if any(c in name for c in '/\\:\0') or name in {".", ".."}:
        return False
    return Path(name).name == name


def _read_seed_marker(marker: Path) -> list[str]:
    if not marker.exists():
        return []
    try:
        data = read_json(marker)
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in data if isinstance(item, str)] if isinstance(data, list) else []


def _list_dir(directory: Path) -> list[dict[str, Any]]:
    presets = []
    for file in directory.glob("*.json"):
        if file.name.startswith("."):
            continue
        try:
            stat = file.stat()
        except OSError:
            continue
        presets.append(
            {
                "name": file.stem,
                "path": str(file),
                "modified_time": datetime.fromtimestamp(stat.st_mtime),
            }
        )
    presets.sort(key=lambda item: item["modified_time"], reverse=True)
    return presets


def _load(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        data = read_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(f"加载预设失败: {exc}")
        return None
    return data if isinstance(data, dict) else None


def _save(path: Path, data: dict[str, Any]) -> bool:
    try:
        write_json(path, data)
        return True
    except OSError as exc:
        logger.warning(f"保存预设失败: {exc}")
        return False


def _delete(path: Path | None) -> bool:
    if path is None:
        return False
    try:
        if path.exists():
            path.unlink()
            return True
    except OSError as exc:
        logger.warning(f"删除预设失败: {exc}")
    return False
