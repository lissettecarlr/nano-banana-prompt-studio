"""火山方舟豆包 Seedream 生图渠道。"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from loguru import logger

from nano_banana.core.images.providers.openai_images import extract_openai_image
from nano_banana.core.images.types import (
    OptionSpec,
    ProviderCredentials,
    ProviderSpec,
    aspect_ratio_option,
)
from nano_banana.core.media import encode_image_reference

DEFAULT_MODEL = "doubao-seedream-5-0-pro-260628"
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MAX_REFERENCE_IMAGES = 10
_GENERATIONS_SUFFIX = "/images/generations"

DOUBAO_IMAGE_SIZE_MAP = {
    "1K": {
        "1:1": "1024x1024",
        "2:3": "832x1248",
        "3:2": "1248x832",
        "3:4": "864x1152",
        "4:3": "1152x864",
        "4:5": "960x1200",
        "5:4": "1200x960",
        "9:16": "800x1424",
        "16:9": "1424x800",
        "21:9": "1568x672",
    },
    "1.5K": {
        "1:1": "1536x1536",
        "2:3": "1248x1872",
        "3:2": "1872x1248",
        "3:4": "1344x1792",
        "4:3": "1792x1344",
        "4:5": "1280x1600",
        "5:4": "1600x1280",
        "9:16": "1152x2048",
        "16:9": "2048x1152",
        "21:9": "2352x1008",
    },
    "2K": {
        "1:1": "2048x2048",
        "2:3": "1664x2496",
        "3:2": "2496x1664",
        "3:4": "1776x2368",
        "4:3": "2368x1776",
        "4:5": "1792x2240",
        "5:4": "2240x1792",
        "9:16": "1584x2816",
        "16:9": "2816x1584",
        "21:9": "3136x1344",
    },
}


def normalize_base_url(base_url: str) -> str:
    """用户常把完整的 .../images/generations 端点粘进来，这里收敛成 SDK 需要的根地址。"""
    url = (base_url or "").strip().rstrip("/")
    if url.endswith(_GENERATIONS_SUFFIX):
        url = url[: -len(_GENERATIONS_SUFFIX)]
    return url


class DoubaoImageBackend:
    def __init__(self, credentials: ProviderCredentials):
        from openai import OpenAI

        self.model = credentials.model or DEFAULT_MODEL
        self.base_url = normalize_base_url(credentials.base_url)
        self.client = OpenAI(api_key=credentials.api_key, base_url=self.base_url)
        logger.info(f"[Doubao] 初始化完成，模型: {self.model}，地址: {self.base_url}")

    def generate(self, prompt: str, images: Sequence[str], options: Mapping[str, Any]):
        kwargs = self.build_request_kwargs(prompt, images, options)
        log_kwargs = {key: value for key, value in kwargs.items() if key != "prompt"}
        extra_body = dict(log_kwargs.get("extra_body") or {})
        if "image" in extra_body:
            refs = extra_body["image"]
            extra_body["image"] = f"{len(refs) if isinstance(refs, list) else 1} 张参考图"
            log_kwargs["extra_body"] = extra_body
        logger.info(f"[Doubao] 发起请求，参数: {log_kwargs}")
        try:
            response = self.client.images.generate(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"豆包 Seedream 请求失败: {exc}") from exc
        return extract_openai_image(response)

    def build_request_kwargs(
        self,
        prompt: str,
        images: Sequence[str],
        options: Mapping[str, Any],
    ) -> dict[str, Any]:
        extra_body: dict[str, Any] = {
            "watermark": str(options.get("watermark", "false")).lower() == "true",
            "optimize_prompt_options": {
                "mode": options.get("optimize_prompt_mode") or "standard"
            },
        }
        if images:
            if len(images) > MAX_REFERENCE_IMAGES:
                logger.warning(
                    f"[Doubao] 参考图超过 {MAX_REFERENCE_IMAGES} 张，"
                    f"仅使用前 {MAX_REFERENCE_IMAGES} 张（共 {len(images)}）"
                )
            encoded = [encode_image_reference(image) for image in images[:MAX_REFERENCE_IMAGES]]
            extra_body["image"] = encoded[0] if len(encoded) == 1 else encoded

        return {
            "model": self.model,
            "prompt": prompt,
            "size": resolve_size(options),
            "output_format": options.get("output_format") or "png",
            "response_format": "b64_json",
            "extra_body": extra_body,
        }


def resolve_size(options: Mapping[str, Any]) -> str:
    image_size = options.get("image_size") or "2K"
    aspect_ratio = options.get("aspect_ratio") or "1:1"
    size_bucket = DOUBAO_IMAGE_SIZE_MAP.get(image_size) or DOUBAO_IMAGE_SIZE_MAP["2K"]
    return size_bucket.get(aspect_ratio) or size_bucket["1:1"]


SPEC = ProviderSpec(
    id="doubao_image",
    label="豆包 Seedream",
    factory=DoubaoImageBackend,
    default_model=DEFAULT_MODEL,
    default_base_url=DEFAULT_BASE_URL,
    url_placeholder=DEFAULT_BASE_URL,
    model_suggestions=(DEFAULT_MODEL,),
    options=(
        aspect_ratio_option(),
        OptionSpec("image_size", "尺寸", "2K", ("1K", "1.5K", "2K")),
        OptionSpec("output_format", "输出格式", "png", ("png", "jpeg")),
        OptionSpec("watermark", "水印", "false", ("false", "true")),
        OptionSpec("optimize_prompt_mode", "提示词优化", "standard", ("standard", "fast")),
    ),
    max_reference_images=MAX_REFERENCE_IMAGES,
)
