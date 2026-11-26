"""连接配置。读接口永远不返回密钥。"""
from flask import Blueprint, jsonify, request

from nano_banana.core import UnknownProviderError
from nano_banana.web.context import error, studio

bp = Blueprint("config", __name__)


@bp.get("/api/config")
def get_config():
    return jsonify(studio().settings.public_view())


@bp.post("/api/config")
def update_config():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("请求体必须是 JSON 对象")
    try:
        studio().settings.update(data)
    except UnknownProviderError as exc:
        return error(str(exc))
    except (OSError, TimeoutError) as exc:
        return error(f"配置写入失败: {exc}", 500)
    return jsonify({"success": True})
