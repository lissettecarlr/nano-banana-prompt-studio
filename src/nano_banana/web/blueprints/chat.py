"""AI 生成 / 修改提示词（SSE）。"""
import json

from flask import Blueprint, request

from nano_banana.core import StudioError
from nano_banana.web.context import error, studio
from nano_banana.web.sse import sse_response

bp = Blueprint("chat", __name__)


def _images(data: dict) -> list[str]:
    images = data.get("images") or []
    return [item for item in images if isinstance(item, str)] if isinstance(images, list) else []


@bp.post("/api/generate")
def generate_prompt():
    data = request.get_json(silent=True) or {}
    try:
        events = studio().generate_prompt(data.get("prompt") or "", _images(data))
    except StudioError as exc:
        return error(str(exc))
    return sse_response(events)


@bp.post("/api/modify")
def modify_prompt():
    data = request.get_json(silent=True) or {}
    document = data.get("document")
    if document is None and isinstance(data.get("current_data"), str):
        # 兼容旧请求体：current_data 是 JSON 字符串
        try:
            document = json.loads(data["current_data"])
        except json.JSONDecodeError:
            return error("current_data 不是有效的 JSON")
    if not isinstance(document, dict):
        return error("当前数据和修改要求不能为空")
    try:
        events = studio().modify_prompt(
            document, data.get("modify_request") or "", _images(data)
        )
    except StudioError as exc:
        return error(str(exc))
    return sse_response(events)
