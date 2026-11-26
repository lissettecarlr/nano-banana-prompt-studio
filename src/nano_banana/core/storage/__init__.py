"""持久化：路径约定、配置、预设、字段选项。所有 store 的路径都由外部注入。"""

from nano_banana.core.storage.options import OptionsStore
from nano_banana.core.storage.paths import StudioPaths
from nano_banana.core.storage.presets import PresetStore, safe_preset_name
from nano_banana.core.storage.settings import ChatSettings, SettingsStore

__all__ = [
    "ChatSettings",
    "OptionsStore",
    "PresetStore",
    "SettingsStore",
    "StudioPaths",
    "safe_preset_name",
]
