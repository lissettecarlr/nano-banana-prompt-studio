"""OpenAI Images API 兼容生图渠道。"""
from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from io import BytesIO
from typing import Any
from urllib.request import urlopen

from loguru import logger

from nano_banana.core.images.types import (
    IMAGE_SIZE_LIST,
    OptionSpec,
    ProviderCredentials,
    ProviderSpec,
    aspect_ratio_option,
)
from nano_banana.core.media import image_reference_filename, read_image_reference

DEFAULT_MODEL = "gpt-image-2"
DEFAULT_BASE_URL = "https://api.openai.com/v1"

OPENAI_IMAGES_SIZE_MAP = {
    "1K": {
        "1:1": "1024x1024",
        "2:3": "1024x1536",
        "3:2": "1536x1024",
        "3:4": "1024x1360",
        "4:3": "1360x1024",
        "4:5": "1024x1280",
        "5:4": "1280x1024",
        "9:16": "864x1536",
        "16:9": "1536x864",
        "21:9": "1792x768",
    },
    "2K": {
        "1:1": "2048x2048",
        "2:3": "1440x2160",
        "3:2": "2160x1440",
        "3:4": "1536x2048",
        "4:3": "2048x1536",
        "4:5": "1600x2000",
        "5:4": "2000x1600",
        "9:16": "1440x2560",
        "16:9": "2560x1440",
        "21:9": "3024x1296",
    },
    "4K": {
        "1:1": "2880x2880",
        "2:3": "2304x3456",
        "3:2": "3456x2304",
        "3:4": "2496x3328",
        "4:3": "3328x2496",
        "4:5": "2560x3200",
        "5:4": "3200x2560",
        "9:16": "2160x3840",
        "16:9": "3840x2160",
        "21:9": "3840x1648",
    },
}


def extract_openai_image(response):
    """从 OpenAI Images 风格的响应里取出第一张图（b64_json 优先，其次 url）。"""
    from PIL import Image

    if not getattr(response, "data", None):
        return None

    item = response.data[0]
    b64_json = getattr(item, "b64_json", None)
    if b64_json:
        return Image.open(BytesIO(base64.b64decode(b64_json)))

    url = getattr(item, "url", None)
    if url:
        with urlopen(url, timeout=120) as resp:
            return Image.open(BytesIO(resp.read()))

    return None


class OpenAIImagesBackend:
    def __init__(self, credentials: ProviderCredentials):
        from openai import OpenAI

        self.model = credentials.model or DEFAULT_MODEL
        base_url = credentials.base_url
        self.client = OpenAI(
            api_key=credentials.api_key,
            base_url=base_url.rstrip("/") if base_url else None,
        )
        logger.info(f"[OpenAIImages] 初始化完成，模型: {self.model}，地址: {base_url}")

    def generate(self, prompt: str, images: Sequence[str], options: Mapping[str, Any]):
        kwargs = self.build_request_kwargs(prompt, options)
        logger.info(
            "[OpenAIImages] 发起请求，参数: "
            f"{ {k: v for k, v in kwargs.items() if k != 'prompt'} }，参考图数量: {len(images)}"
        )
        try:
            response = self._send(images, kwargs)
        except TypeError:
            # 部分兼容网关的 SDK 版本不认识 quality / output_format
            logger.warning("[OpenAIImages] 参数不兼容，使用核心字段重试")
            kwargs = {key: kwargs[key] for key in ("model", "prompt", "size")}
            response = self._send(images, kwargs)
        return extract_openai_image(response)

    def build_request_kwargs(self, prompt: str, options: Mapping[str, Any]) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "size": resolve_size(options),
        }
        for key in ("quality", "output_format"):
            value = options.get(key)
            if value and value != "auto":
                kwargs[key] = value
        return kwargs

    def _send(self, images: Sequence[str], kwargs: dict[str, Any]):
        if not images:
            return self.client.images.generate(**kwargs)
        files = []
        for index, image_ref in enumerate(images):
            data, mime_type = read_image_reference(image_ref)
            files.append((image_reference_filename(index, mime_type), data, mime_type))
        return self.client.images.edit(image=files[0] if len(files) == 1 else files, **kwargs)


def resolve_size(options: Mapping[str, Any]) -> str:
    aspect_ratio = options.get("aspect_ratio") or "1:1"
    image_size = options.get("image_size") or "2K"
    return OPENAI_IMAGES_SIZE_MAP.get(image_size, OPENAI_IMAGES_SIZE_MAP["2K"]).get(
        aspect_ratio,
        OPENAI_IMAGES_SIZE_MAP["2K"]["1:1"],
    )


SPEC = ProviderSpec(
    id="openai_images",
    label="OpenAI Images",
    factory=OpenAIImagesBackend,
    default_model=DEFAULT_MODEL,
    default_base_url=DEFAULT_BASE_URL,
    url_placeholder=DEFAULT_BASE_URL,
    model_suggestions=(DEFAULT_MODEL,),
    options=(
        aspect_ratio_option(),
        OptionSpec("image_size", "尺寸", "2K", IMAGE_SIZE_LIST),
        OptionSpec("quality", "质量", "auto", ("auto", "low", "medium", "high")),
        OptionSpec("output_format", "输出格式", "png", ("png", "jpeg", "webp")),
    ),
)
