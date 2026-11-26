"""图片生成的公共类型：请求、结果、渠道声明。

新增一个渠道 = 在 providers/ 下写一个模块并导出 SPEC，再把模块名登记到 registry。
其余（配置读写、/api/config、两端的配置界面和参数控件）全部由 SPEC 驱动。
"""
from __future__ import annotations

import base64
import copy
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Protocol, runtime_checkable

ASPECT_RATIO_LIST = ("1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9")
IMAGE_SIZE_LIST = ("1K", "2K", "4K")
THINKING_LEVEL_LIST = ("none", "low", "medium", "high")


class ImageGenerationError(RuntimeError):
    """渠道返回了错误，或没有返回图片。"""


@dataclass(frozen=True)
class OptionSpec:
    key: str
    label: str
    default: str
    values: tuple[str, ...]
    type: str = "select"

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "type": self.type,
            "default": self.default,
            "values": list(self.values),
        }


def aspect_ratio_option(default: str = "1:1") -> OptionSpec:
    return OptionSpec("aspect_ratio", "宽高比", default, ASPECT_RATIO_LIST)


@dataclass(frozen=True)
class ProviderCredentials:
    base_url: str
    api_key: str
    model: str

    @property
    def is_complete(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)


@runtime_checkable
class ImageBackend(Protocol):
    """一次生成调用所需的全部输入都走参数，实现不得在实例上保存生成参数。"""

    def generate(
        self,
        prompt: str,
        images: Sequence[str],
        options: Mapping[str, Any],
    ) -> Any: ...


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    label: str
    factory: Callable[[ProviderCredentials], ImageBackend]
    default_model: str
    default_base_url: str = ""
    url_placeholder: str = ""
    model_suggestions: tuple[str, ...] = ()
    options: tuple[OptionSpec, ...] = ()
    # 按模型覆盖：{model: {"label": ..., "options": {key: {覆盖项} | None(移除)}}}
    model_overrides: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    max_reference_images: int | None = None

    def capabilities(self, model: str = "") -> dict[str, Any]:
        """给界面用的能力描述：{"label": ..., "options": {key: {label,type,default,values}}}。"""
        capabilities: dict[str, Any] = {
            "label": self.label,
            "options": {option.key: option.to_dict() for option in self.options},
        }
        overrides = self.model_overrides.get(model) or {}
        for key, value in overrides.items():
            if key != "options":
                capabilities[key] = copy.deepcopy(value)
        for key, option in (overrides.get("options") or {}).items():
            if option is None:
                capabilities["options"].pop(key, None)
            else:
                existing = capabilities["options"].get(key, {})
                capabilities["options"][key] = {**existing, **copy.deepcopy(option)}
        return capabilities

    def resolve_options(self, model: str, options: Mapping[str, Any] | None) -> dict[str, Any]:
        """丢掉该渠道/模型不认识的键和空值。"""
        known = self.capabilities(model)["options"]
        return {
            key: value
            for key, value in (options or {}).items()
            if key in known and value not in (None, "")
        }

    def models(self, configured_model: str = "") -> list[str]:
        models = list(self.model_suggestions)
        if configured_model and configured_model not in models:
            models.append(configured_model)
        return models

    def describe(self) -> dict[str, Any]:
        """不含任何用户数据的静态描述，供配置界面生成表单。"""
        return {
            "id": self.id,
            "label": self.label,
            "default_model": self.default_model,
            "default_base_url": self.default_base_url,
            "url_placeholder": self.url_placeholder,
            "model_suggestions": list(self.model_suggestions),
        }


@dataclass(frozen=True)
class ImageRequest:
    prompt: str
    provider: str = ""  # 空 = 用设置里的当前渠道
    model: str = ""  # 空 = 用该渠道已配置的模型
    images: tuple[str, ...] = ()
    options: Mapping[str, Any] = field(default_factory=dict)
    remember: bool = True  # 把渠道/模型/参数记为下次默认


@dataclass(frozen=True)
class ImageResult:
    image: Any  # PIL.Image.Image
    provider: str
    model: str

    def to_png_bytes(self) -> bytes:
        buffer = BytesIO()
        self.image.save(buffer, format="PNG")
        return buffer.getvalue()

    def to_data_url(self) -> str:
        encoded = base64.b64encode(self.to_png_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
