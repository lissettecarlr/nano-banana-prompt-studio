"""提示词文档：schema、渲染、字段选项、线稿提示词。"""
from flask import Blueprint, jsonify, request

from nano_banana.web.context import error, studio

bp = Blueprint("prompt", __name__)


@bp.get("/api/schema")
def get_prompt_schema():
    return jsonify(studio().schema.to_public_dict())


@bp.post("/api/prompt/render")
def render_prompt():
    """文档 → 最终提示词文本。前端预览和实际生图请求都以这里为准。"""
    document = (request.get_json(silent=True) or {}).get("document")
    if not isinstance(document, dict):
        return error("document 必须是 JSON 对象")
    return jsonify(studio().render(document).to_dict())


@bp.get("/api/options")
def get_options():
    return jsonify(studio().options.load_options())


@bp.get("/api/options/<field_name>")
def get_field_options(field_name):
    return jsonify(studio().options.get_field_options(field_name))


@bp.post("/api/options/<field_name>")
def add_option(field_name):
    value = (request.get_json(silent=True) or {}).get("value")
    if not value or not isinstance(value, str):
        return error("值不能为空")
    studio().options.add_option(field_name, value)
    return jsonify({"success": True})


@bp.delete("/api/options/<field_name>")
def delete_option(field_name):
    value = (request.get_json(silent=True) or {}).get("value")
    if not value or not isinstance(value, str):
        return error("值不能为空")
    studio().options.remove_option(field_name, value)
    return jsonify({"success": True})


@bp.get("/api/line-art-prompt")
def get_line_art_prompt():
    return jsonify({"prompt": studio().options.get_line_art_prompt()})


@bp.post("/api/line-art-prompt")
def save_line_art_prompt():
    prompt = (request.get_json(silent=True) or {}).get("prompt")
    if not isinstance(prompt, str):
        return error("提示词不能为空")
    studio().options.save_line_art_prompt(prompt)
    return jsonify({"success": True})
