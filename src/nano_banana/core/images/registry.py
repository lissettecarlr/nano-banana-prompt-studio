"""图片渠道注册表。渠道模块只在这里登记一次。"""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from functools import lru_cache
from importlib import import_module

from nano_banana.core.images.types import ProviderSpec

# 顺序即界面展示顺序。渠道模块导入时不得加载各家 SDK（SDK 在 factory 里按需导入）。
BUILTIN_PROVIDER_MODULES = (
    "nano_banana.core.images.providers.gemini",
    "nano_banana.core.images.providers.openai_images",
    "nano_banana.core.images.providers.qwen",
    "nano_banana.core.images.providers.doubao",
)


class UnknownProviderError(ValueError):
    def __init__(self, provider_id: str):
        super().__init__(f"未知图片生成渠道: {provider_id}")
        self.provider_id = provider_id


class ProviderRegistry:
    def __init__(self, specs: Iterable[ProviderSpec] = ()):
        self._specs: dict[str, ProviderSpec] = {}
        for spec in specs:
            self.register(spec)

    def register(self, spec: ProviderSpec) -> ProviderSpec:
        if spec.id in self._specs:
            raise ValueError(f"图片渠道重复注册: {spec.id}")
        self._specs[spec.id] = spec
        return spec

    def get(self, provider_id: str) -> ProviderSpec:
        try:
            return self._specs[provider_id]
        except KeyError:
            raise UnknownProviderError(provider_id) from None

    def __contains__(self, provider_id: object) -> bool:
        return provider_id in self._specs

    def __iter__(self) -> Iterator[ProviderSpec]:
        return iter(self._specs.values())

    def __len__(self) -> int:
        return len(self._specs)

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(self._specs)

    @property
    def default_id(self) -> str:
        return next(iter(self._specs), "")


@lru_cache(maxsize=1)
def default_registry() -> ProviderRegistry:
    return ProviderRegistry(
        import_module(module_name).SPEC for module_name in BUILTIN_PROVIDER_MODULES
    )
