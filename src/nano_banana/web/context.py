"""请求内获取 Studio，以及统一的错误响应。"""
from __future__ import annotations

from flask import current_app, jsonify

from nano_banana.core import Studio

STUDIO_EXTENSION = "nano_banana_studio"


def studio() -> Studio:
    return current_app.extensions[STUDIO_EXTENSION]


def error(message: str, status: int = 400):
    return jsonify({"error": message}), status
