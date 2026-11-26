"""字段下拉选项与线稿提示词。

读取时用户文件按键覆盖包内默认值；写入只落到用户文件，且只写用户动过的键。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from nano_banana.core.storage.files import locked, read_yaml, write_yaml

LINE_ART_PROMPT_KEY = "角色线稿提示词"


class OptionsStore:
    def __init__(
        self,
        user_file: Path,
        builtin_file: Path | None = None,
        *,
        fallback: dict[str, list[str]] | None = None,
    ):
        self.user_file = Path(user_file)
        self.builtin_file = Path(builtin_file) if builtin_file else None
        # 用户文件和内置文件都没有该字段时的兜底（例如默认反向提示词标签）
        self.fallback = {key: list(value) for key, value in (fallback or {}).items()}

    # ---------- 读 ----------

    def load_options(self) -> dict[str, Any]:
        """全部选项：内置默认值 + 用户覆盖。"""
        return {**self._read(self.builtin_file), **self._read(self.user_file)}

    def get_field_options(self, field_name: str) -> list[str]:
        value = self.load_options().get(field_name)
        if isinstance(value, list):
            return list(value)
        return list(self.fallback.get(field_name, []))

    def get_line_art_prompt(self) -> str:
        value = self.load_options().get(LINE_ART_PROMPT_KEY)
        return value if isinstance(value, str) else ""

    # ---------- 写 ----------

    def add_option(self, field_name: str, value: str) -> None:
        def mutate(options: list[str]) -> bool:
            if not value or value in options:
                return False
            options.append(value)
            return True

        self._mutate_field(field_name, mutate)

    def remove_option(self, field_name: str, value: str) -> None:
        def mutate(options: list[str]) -> bool:
            if value not in options:
                return False
            options.remove(value)
            return True

        self._mutate_field(field_name, mutate)

    def update_option(self, field_name: str, old_value: str, new_value: str) -> None:
        def mutate(options: list[str]) -> bool:
            if old_value not in options:
                return False
            options[options.index(old_value)] = new_value
            return True

        self._mutate_field(field_name, mutate)

    def save_line_art_prompt(self, prompt: str) -> None:
        with locked(self.user_file):
            user = self._read(self.user_file)
            user[LINE_ART_PROMPT_KEY] = prompt
            write_yaml(self.user_file, user)

    # ---------- 内部 ----------

    def _mutate_field(self, field_name: str, mutate) -> None:
        with locked(self.user_file):
            options = self.get_field_options(field_name)
            if not mutate(options):
                return
            user = self._read(self.user_file)
            user[field_name] = options
            write_yaml(self.user_file, user)

    @staticmethod
    def _read(path: Path | None) -> dict[str, Any]:
        if path is None or not path.exists():
            return {}
        try:
            data = read_yaml(path)
        except (OSError, yaml.YAMLError) as exc:
            logger.warning(f"加载选项文件失败 {path}: {exc}")
            return {}
        return data if isinstance(data, dict) else {}
