"""数据目录约定。

- builtin：随包发布的只读数据（内置预设、默认选项）。
- user：可写目录。桌面端 = exe 同级目录，Web = 挂载卷，插件 = 宿主给的目录。

核心代码不自己猜路径，一律由交互口构造 StudioPaths 注入。
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

HOME_ENV = "NANO_BANANA_HOME"

PACKAGE_ROOT = Path(__file__).resolve().parents[2]  # .../nano_banana
BUILTIN_DIR = PACKAGE_ROOT / "builtin"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def source_checkout_root() -> Path | None:
    """从源码仓库运行（含 pip install -e）时返回仓库根目录，否则 None。"""
    root = PACKAGE_ROOT.parents[1]
    if PACKAGE_ROOT.parent.name == "src" and (root / "pyproject.toml").is_file():
        return root
    return None


def default_user_dir() -> Path:
    """可写目录的默认位置，优先级：环境变量 > exe 同级 > 仓库 data/ > ~/.nano-banana。"""
    override = os.environ.get(HOME_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    if is_frozen():
        return Path(sys.executable).resolve().parent
    checkout = source_checkout_root()
    if checkout is not None:
        return checkout / "data"
    return Path.home() / ".nano-banana"


@dataclass(frozen=True)
class StudioPaths:
    user: Path
    builtin: Path = BUILTIN_DIR

    def __post_init__(self):
        # 调用方（脚本、插件）经常直接传字符串
        object.__setattr__(self, "user", Path(self.user).expanduser())
        object.__setattr__(self, "builtin", Path(self.builtin))

    @classmethod
    def default(cls) -> "StudioPaths":
        return cls(user=default_user_dir())

    @property
    def settings_file(self) -> Path:
        return self.user / "config" / "ai_config.yaml"

    @property
    def options_file(self) -> Path:
        return self.user / "config" / "options.yaml"

    @property
    def presets_dir(self) -> Path:
        return self.user / "presets"

    @property
    def builtin_options_file(self) -> Path:
        return self.builtin / "options.yaml"

    @property
    def builtin_presets_dir(self) -> Path:
        return self.builtin / "presets"

    @property
    def legacy_user_dir(self) -> Path | None:
        """重构前源码运行时的数据目录（src/config、src/presets），用于一次性导入。

        只有当前可写目录就是仓库默认的 data/ 时才有意义。
        """
        checkout = source_checkout_root()
        if checkout is None or is_frozen() or self.user != checkout / "data":
            return None
        return checkout / "src"
