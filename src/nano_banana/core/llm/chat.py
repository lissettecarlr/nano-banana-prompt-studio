"""OpenAI-compatible 流式聊天。无 UI、无传输层（SSE 等）依赖。"""
from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any

from nano_banana.core.llm.prompts import MODIFY_SYSTEM_PROMPT, SYSTEM_PROMPT
from nano_banana.core.media import encode_image_reference

CancelledFn = Callable[[], bool]

DEFAULT_CHAT_MODEL = "gpt-4o-mini"


@dataclass(frozen=True)
class ChatEvent:
    type: str  # thinking | content | done | error
    text: str = ""


def create_chat_client(*, base_url: str, api_key: str, timeout: float = 180):
    """构造客户端但不发请求，调用方可以在打上游之前先向用户反馈「已开始」。"""
    import httpx
    from openai import OpenAI

    http_client = httpx.Client(http2=False)
    client = OpenAI(
        api_key=api_key,
        base_url=(base_url or "").rstrip("/"),
        timeout=timeout,
        http_client=http_client,
    )
    return client, http_client


def iter_completion_events(
    client,
    messages: list[dict[str, Any]],
    *,
    model: str,
    cancelled: CancelledFn | None = None,
) -> Iterator[ChatEvent]:
    thinking_reported = False
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
    )
    full_content = ""
    for chunk in stream:
        if cancelled and cancelled():
            yield ChatEvent("error", "已取消")
            return
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        reasoning_content = getattr(delta, "reasoning_content", None)
        if reasoning_content and not thinking_reported:
            thinking_reported = True
            yield ChatEvent("thinking")
        if delta and delta.content:
            full_content += delta.content
            yield ChatEvent("content", delta.content)
    yield ChatEvent("done", full_content)


def build_generate_messages(
    user_prompt: str,
    images: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    user_content = _multimodal_user_content(
        images or [],
        text_with_images=f"请根据以下描述和参考图片生成提示词：\n\n{user_prompt}",
        text_only=f"请根据以下描述生成提示词：\n\n{user_prompt}",
        images_only="请根据参考图片生成提示词。",
        has_text=bool((user_prompt or "").strip()),
        require_any=True,
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def build_modify_messages(
    current_data: str,
    modify_request: str,
    images: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    text_content = (
        f"当前提示词：\n{current_data}\n\n修改要求：{modify_request}\n\n请返回修改后的JSON提示词:"
    )
    user_content = _multimodal_user_content(
        images or [],
        text_with_images=text_content,
        text_only=text_content,
        images_only=text_content,
        has_text=True,
        require_any=False,
    )
    return [
        {"role": "system", "content": MODIFY_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def format_chat_error(exc: Exception) -> str:
    error_msg = str(exc)
    if "401" in error_msg or "Unauthorized" in error_msg:
        return "API密钥无效或已过期，请检查配置"
    if "429" in error_msg or "rate" in error_msg.lower():
        return "请求过于频繁，请稍后再试"
    if "timeout" in error_msg.lower():
        return "请求超时，请检查网络连接或稍后再试"
    if "connect" in error_msg.lower():
        return f"网络连接失败: {error_msg}"
    return f"API调用失败: {error_msg}"


def _multimodal_user_content(
    images: Sequence[str],
    *,
    text_with_images: str,
    text_only: str,
    images_only: str,
    has_text: bool,
    require_any: bool,
) -> Any:
    parts: list[dict[str, Any]] = [
        {"type": "image_url", "image_url": {"url": encode_image_reference(image_ref)}}
        for image_ref in images
    ]
    if parts:
        parts.append({"type": "text", "text": text_with_images if has_text else images_only})
        return parts
    if has_text:
        return text_only
    if require_any:
        raise ValueError("请提供文字描述或参考图片")
    return text_only
