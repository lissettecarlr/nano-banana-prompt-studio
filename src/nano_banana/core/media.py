"""参考图引用的统一读取：本地路径 / data URL / http(s) URL。"""
from __future__ import annotations

import base64
import binascii
import mimetypes
import os

_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
}


def is_remote_reference(image_ref: str) -> bool:
    return image_ref.startswith(("http://", "https://"))


def encode_image_reference(image_ref: str) -> str:
    """转成可直接放进请求体的引用：data URL 或远程 URL。"""
    value = (image_ref or "").strip()
    if not value:
        raise ValueError("参考图路径为空")
    if value.startswith("data:") or is_remote_reference(value):
        return value
    if not os.path.isfile(value):
        raise ValueError(f"参考图文件不存在: {value}")

    mime_type, _ = mimetypes.guess_type(value)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/png"
    with open(value, "rb") as file_obj:
        encoded = base64.b64encode(file_obj.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def read_image_reference(image_ref: str) -> tuple[bytes, str]:
    """读出图片字节和 MIME。支持本地路径、data URL、裸 base64。"""
    value = (image_ref or "").strip()
    if not value:
        raise ValueError("参考图路径为空")
    if is_remote_reference(value):
        raise ValueError("该渠道不支持远程 URL 参考图，请先下载到本地")
    if value.startswith("data:"):
        header, separator, payload = value.partition(";base64,")
        if not separator:
            raise ValueError("参考图 data URL 必须是 base64 编码")
        return _decode_base64(payload), header[len("data:"):] or "image/png"
    if os.path.isfile(value):
        mime_type, _ = mimetypes.guess_type(value)
        if not mime_type or not mime_type.startswith("image/"):
            mime_type = "image/png"
        with open(value, "rb") as file_obj:
            return file_obj.read(), mime_type
    # 历史行为：非文件一律当作裸 base64 的 JPEG
    return _decode_base64(value), "image/jpeg"


def image_reference_filename(index: int, mime_type: str) -> str:
    return f"reference_{index}{_EXTENSIONS.get(mime_type, '.png')}"


def _decode_base64(payload: str) -> bytes:
    try:
        return base64.b64decode(payload, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("参考图不是有效的文件路径或 base64 数据") from exc
