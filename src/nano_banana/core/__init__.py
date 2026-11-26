"""无 UI 依赖的领域核心。

交互口的公共入口只有两处：

- `nano_banana.core`（本模块）：Studio 门面及其输入输出类型；
- `nano_banana.core.prompt`：schema 与文档的纯函数工具。

`core.images.providers`、`core.storage`、`core.llm` 是内部实现，交互口不得直接导入
（由 import-linter 和 tests/test_architecture.py 强制）。
"""
from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "Studio": "nano_banana.core.studio",
    "StudioError": "nano_banana.core.studio",
    "NotConfiguredError": "nano_banana.core.studio",
    "PromptEvent": "nano_banana.core.studio",
    "ProviderStatus": "nano_banana.core.studio",
    "StudioPaths": "nano_banana.core.storage.paths",
    "ImageRequest": "nano_banana.core.images.types",
    "ImageResult": "nano_banana.core.images.types",
    "ImageGenerationError": "nano_banana.core.images.types",
    "ProviderSpec": "nano_banana.core.images.types",
    "ProviderRegistry": "nano_banana.core.images.registry",
    "UnknownProviderError": "nano_banana.core.images.registry",
    "Change": "nano_banana.core.prompt.diff",
    "RenderedPrompt": "nano_banana.core.prompt.render",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str):
    # 惰性导出：只用 schema 的调用方不必加载存储和渠道代码
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(_EXPORTS))
