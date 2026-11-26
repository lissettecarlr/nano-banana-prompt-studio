"""AI 连接配置。对话模型与各图片渠道相互独立。

内存和磁盘都是同一份嵌套结构，渠道一律按 id 索引：

    chat:  {base_url, api_key, model}
    image:
      active: <provider id>
      providers: {<provider id>: {base_url, api_key, model}}
      options:   {<provider id>: {<model | __default__>: {...}}}

旧版扁平 yaml（gemini_base_url 之类）只在读入时转换一次。
"""
from __future__ import annotations

import shutil
import time
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from nano_banana.core.images.registry import ProviderRegistry, UnknownProviderError
from nano_banana.core.images.types import ProviderCredentials
from nano_banana.core.storage.files import locked, read_yaml, write_yaml

CREDENTIAL_KEYS = ("base_url", "api_key", "model")
DEFAULT_OPTIONS_MODEL_KEY = "__default__"

# 旧版扁平键前缀。只为读旧文件 / 兼容旧 API 请求体，新渠道不需要登记。
LEGACY_FLAT_PREFIXES = {
    "gemini": "gemini",
    "openai_images": "openai_image",
    "qwen_image": "qwen_image",
    "doubao_image": "doubao_image",
}


@dataclass(frozen=True)
class ChatSettings:
    base_url: str = ""
    api_key: str = ""
    model: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


def legacy_flat_to_nested(data: dict[str, Any]) -> dict[str, Any]:
    """旧扁平配置 → 嵌套补丁。只包含源里出现过的键。"""
    patch: dict[str, Any] = {}
    chat = {key: data[key] for key in CREDENTIAL_KEYS if key in data}
    if chat:
        patch["chat"] = chat

    image: dict[str, Any] = {}
    if "image_provider" in data:
        image["active"] = data["image_provider"]
    providers: dict[str, Any] = {}
    for provider_id, prefix in LEGACY_FLAT_PREFIXES.items():
        creds = {
            key: data[f"{prefix}_{key}"] for key in CREDENTIAL_KEYS if f"{prefix}_{key}" in data
        }
        if creds:
            providers[provider_id] = creds
    if providers:
        image["providers"] = providers
    if "image_generation_options" in data:
        image["options"] = data["image_generation_options"]
    if image:
        patch["image"] = image
    return patch


def as_nested_patch(data: dict[str, Any]) -> dict[str, Any]:
    if "chat" in data or "image" in data:
        return {key: data[key] for key in ("chat", "image") if key in data}
    return legacy_flat_to_nested(data)


class SettingsStore:
    def __init__(self, path: Path, registry: ProviderRegistry):
        self.path = Path(path)
        self.registry = registry

    # ---------- 读 ----------

    def read(self) -> dict[str, Any]:
        """返回归一化后的完整配置（含密钥）。文件缺失或损坏时返回空配置。"""
        raw, _ = self._read_raw()
        return self._normalize(raw)

    def chat(self) -> ChatSettings:
        chat = self.read()["chat"]
        return ChatSettings(**{key: chat[key].strip() for key in CREDENTIAL_KEYS})

    def active_provider(self) -> str:
        return self.read()["image"]["active"]

    def credentials(self, provider_id: str) -> ProviderCredentials:
        """指定渠道的连接参数，未填写的 base_url / model 用渠道默认值补齐。"""
        spec = self.registry.get(provider_id)
        stored = self.read()["image"]["providers"].get(provider_id) or {}
        return ProviderCredentials(
            base_url=(stored.get("base_url") or spec.default_base_url or "").strip(),
            api_key=(stored.get("api_key") or "").strip(),
            model=(stored.get("model") or "").strip() or spec.default_model,
        )

    def is_provider_configured(self, provider_id: str | None = None) -> bool:
        return self.credentials(provider_id or self.active_provider()).is_complete

    def providers_with_api_key(self) -> list[str]:
        """按注册顺序返回已填写 API 密钥的渠道。"""
        providers = self.read()["image"]["providers"]
        return [
            spec.id
            for spec in self.registry
            if ((providers.get(spec.id) or {}).get("api_key") or "").strip()
        ]

    def generation_options(self, provider_id: str, model: str = "") -> dict[str, Any]:
        """指定渠道/模型上次使用的生成参数。"""
        options = self.read()["image"]["options"]
        saved = (options.get(provider_id) or {}).get(_options_model_key(model)) or {}
        return deepcopy(saved) if isinstance(saved, dict) else {}

    def public_view(self) -> dict[str, Any]:
        """可以安全发给前端的配置：密钥只保留「是否已填写」。"""
        config = self.read()
        return {
            "chat": _mask(config["chat"]),
            "image": {
                "active": config["image"]["active"],
                "providers": {
                    spec.id: _mask(config["image"]["providers"].get(spec.id) or {})
                    for spec in self.registry
                },
                "options": config["image"]["options"],
            },
        }

    # ---------- 写 ----------

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        """把补丁合并进磁盘配置。接受嵌套补丁，也接受旧版扁平键。

        整个「读-改-写」在文件锁内完成，写入是原子的。
        """
        if not isinstance(patch, dict):
            raise ValueError("配置必须是 JSON 对象")
        nested = as_nested_patch(patch)
        active = (nested.get("image") or {}).get("active")
        if active is not None and active not in self.registry:
            raise UnknownProviderError(str(active))

        with locked(self.path):
            raw, corrupt = self._read_raw()
            if corrupt:
                self._backup_corrupt_file()
            config = self._normalize(raw)
            _merge_patch(config, nested)
            write_yaml(self.path, config)
            return config

    def set_active_selection(self, provider_id: str, model: str | None = None) -> None:
        """记住主界面当前使用的渠道和模型，不动任何凭证。"""
        self.registry.get(provider_id)
        image: dict[str, Any] = {"active": provider_id}
        if model is not None:
            image["providers"] = {provider_id: {"model": model.strip()}}
        self.update({"image": image})

    def save_generation_options(self, provider_id: str, model: str, options: dict[str, Any]) -> None:
        """记住指定渠道/模型的生成参数偏好。"""
        self.registry.get(provider_id)
        self.update(
            {"image": {"options": {provider_id: {_options_model_key(model): dict(options)}}}}
        )

    # ---------- 内部 ----------

    def _read_raw(self) -> tuple[dict[str, Any], bool]:
        if not self.path.exists():
            return {}, False
        try:
            data = read_yaml(self.path)
        except (OSError, yaml.YAMLError) as exc:
            logger.warning(f"加载 AI 配置失败，按空配置处理: {exc}")
            return {}, True
        return (data if isinstance(data, dict) else {}), False

    def _backup_corrupt_file(self) -> None:
        backup = self.path.with_name(f"{self.path.name}.corrupt-{int(time.time())}")
        try:
            shutil.copy2(self.path, backup)
            logger.warning(f"AI 配置文件无法解析，已备份到 {backup}")
        except OSError as exc:
            logger.warning(f"备份损坏的 AI 配置失败: {exc}")

    def _normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        nested = as_nested_patch(raw)
        chat = nested.get("chat") if isinstance(nested.get("chat"), dict) else {}
        image = nested.get("image") if isinstance(nested.get("image"), dict) else {}
        stored_providers = image.get("providers") if isinstance(image.get("providers"), dict) else {}
        options = image.get("options") if isinstance(image.get("options"), dict) else {}

        providers = {
            spec.id: _credentials_dict(stored_providers.get(spec.id)) for spec in self.registry
        }
        # 当前版本不认识的渠道原样保留，升级/降级不丢用户数据
        for provider_id, creds in stored_providers.items():
            if provider_id not in providers and isinstance(creds, dict):
                providers[provider_id] = _credentials_dict(creds)

        active = image.get("active")
        if active not in self.registry:
            active = self.registry.default_id
        return {
            "chat": _credentials_dict(chat),
            "image": {
                "active": active,
                "providers": providers,
                "options": deepcopy(options),
            },
        }


def _options_model_key(model: str) -> str:
    return (model or "").strip() or DEFAULT_OPTIONS_MODEL_KEY


def _credentials_dict(raw: Any) -> dict[str, str]:
    source = raw if isinstance(raw, dict) else {}
    return {key: _text(source.get(key)) for key in CREDENTIAL_KEYS}


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _mask(creds: dict[str, Any]) -> dict[str, Any]:
    return {
        "base_url": _text(creds.get("base_url")),
        "model": _text(creds.get("model")),
        "has_api_key": bool(_text(creds.get("api_key")).strip()),
    }


def _merge_patch(config: dict[str, Any], patch: dict[str, Any]) -> None:
    chat = patch.get("chat")
    if isinstance(chat, dict):
        _merge_credentials(config["chat"], chat)

    image = patch.get("image")
    if not isinstance(image, dict):
        return
    if image.get("active") is not None:
        config["image"]["active"] = image["active"]
    providers = image.get("providers")
    if isinstance(providers, dict):
        for provider_id, creds in providers.items():
            if isinstance(creds, dict):
                target = config["image"]["providers"].setdefault(
                    provider_id, _credentials_dict(None)
                )
                _merge_credentials(target, creds)
    options = image.get("options")
    if isinstance(options, dict):
        for provider_id, by_model in options.items():
            if not isinstance(by_model, dict):
                continue
            target = config["image"]["options"].setdefault(provider_id, {})
            if not isinstance(target, dict):
                target = config["image"]["options"][provider_id] = {}
            for model_key, values in by_model.items():
                target[model_key] = deepcopy(values)


def _merge_credentials(target: dict[str, str], patch: dict[str, Any]) -> None:
    for key in CREDENTIAL_KEYS:
        if key in patch:
            target[key] = _text(patch[key])
