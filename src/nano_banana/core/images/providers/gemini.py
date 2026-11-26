"""Gemini 生图渠道。"""
from __future__ import annotations

import base64
import os
from collections.abc import Mapping, Sequence
from io import BytesIO
from typing import Any

from loguru import logger

from nano_banana.core.images.types import (
    ASPECT_RATIO_LIST,
    IMAGE_SIZE_LIST,
    THINKING_LEVEL_LIST,
    OptionSpec,
    ProviderCredentials,
    ProviderSpec,
    aspect_ratio_option,
)
from nano_banana.core.media import read_image_reference

DEFAULT_MODEL = "gemini-3-pro-image-preview"


def _bypass_system_proxy() -> None:
    """Gemini 中转站通常需要直连。

    注意这是进程级副作用：首次创建 Gemini 客户端后，本进程里的其它 HTTP 请求
    也不再走系统代理。沿用历史行为，改动前请先确认用户的网络环境。
    """
    os.environ["NO_PROXY"] = "*"
    os.environ["HTTP_PROXY"] = ""
    os.environ["HTTPS_PROXY"] = ""


class GeminiImageBackend:
    def __init__(self, credentials: ProviderCredentials):
        _bypass_system_proxy()
        from google import genai
        from google.genai import types

        self._types = types
        self.model = credentials.model or DEFAULT_MODEL
        self.base_url = credentials.base_url.rstrip("/")
        self.client = genai.Client(
            http_options=types.HttpOptions(base_url=self.base_url),
            api_key=credentials.api_key,
        )
        logger.info(f"[Gemini] 初始化完成，模型: {self.model}，地址: {self.base_url}")

    def generate(self, prompt: str, images: Sequence[str], options: Mapping[str, Any]):
        from PIL import Image

        types = self._types
        aspect_ratio = _checked(options.get("aspect_ratio") or "1:1", ASPECT_RATIO_LIST, "宽高比")
        image_size = _checked(options.get("image_size") or "2K", IMAGE_SIZE_LIST, "图片尺寸")
        logger.info(
            f"[Gemini] 开始生图，宽高比={aspect_ratio}，尺寸={image_size}，参考图={len(images)}"
        )

        parts = [types.Part(text=prompt)]
        for image_ref in images:
            data, mime_type = read_image_reference(image_ref)
            parts.append(types.Part(inline_data=types.Blob(mime_type=mime_type, data=data)))

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[types.Content(parts=parts)],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=image_size,
                    )
                ),
            )
        except Exception as exc:
            logger.error(f"[Gemini] 生图调用失败: {exc}")
            raise

        for part in response.parts or []:
            if not part.inline_data:
                continue
            data = part.inline_data.data
            if isinstance(data, str):
                data = base64.b64decode(data)
            return Image.open(BytesIO(bytes(data)))

        if response.text:
            logger.warning(f"[Gemini] 未生成图片，返回文本: {response.text[:100]}")
        return None


def _checked(value: str, allowed: Sequence[str], name: str) -> str:
    if value not in allowed:
        raise ValueError(f"{name}不支持: {value}，可选: {list(allowed)}")
    return value


SPEC = ProviderSpec(
    id="gemini",
    label="Gemini",
    factory=GeminiImageBackend,
    default_model=DEFAULT_MODEL,
    default_base_url="",
    url_placeholder="https://generativelanguage.googleapis.com",
    model_suggestions=(DEFAULT_MODEL, "gemini-3.1-flash-image-preview"),
    options=(
        aspect_ratio_option(),
        OptionSpec("image_size", "尺寸", "2K", IMAGE_SIZE_LIST),
        OptionSpec("thinking_level", "思考级别", "low", THINKING_LEVEL_LIST),
    ),
)
