"""整套预设与分类预设。读出的文档一律先升级到当前结构。"""
from flask import Blueprint, jsonify, request

from nano_banana.web.context import error, studio

bp = Blueprint("presets", __name__)


def _listing(presets: list[dict]) -> list[dict]:
    return [
        {"name": preset["name"], "modified_time": preset["modified_time"].isoformat()}
        for preset in presets
    ]


def _known_scope(scope: str) -> bool:
    return scope in studio().schema.category_ids


@bp.get("/api/presets")
def get_presets():
    return jsonify(_listing(studio().presets.list_all()))


@bp.get("/api/presets/details")
def get_all_preset_details():
    app_studio = studio()
    details = []
    for preset in app_studio.presets.list_all():
        data = app_studio.presets.load(preset["name"])
        if data is not None:
            details.append(app_studio.migrate(data))
    return jsonify(details)


@bp.get("/api/presets/<name>")
def get_preset(name):
    preset = studio().presets.load(name)
    if preset is None:
        return error("预设不存在", 404)
    return jsonify(studio().migrate(preset))


@bp.post("/api/presets")
def save_preset():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    data = payload.get("data")
    if not name or not isinstance(name, str) or not isinstance(data, dict) or not data:
        return error("名称和数据不能为空")
    saved_name = studio().presets.save(name, data)
    if saved_name is None:
        return error("保存失败", 500)
    return jsonify({"success": True, "name": saved_name})


@bp.delete("/api/presets/<name>")
def delete_preset(name):
    if studio().presets.delete(name):
        return jsonify({"success": True})
    return error("预设不存在", 404)


@bp.get("/api/category-presets/<scope>")
def get_category_presets(scope):
    if not _known_scope(scope):
        return error("未知的预设分类", 404)
    return jsonify(_listing(studio().presets.list_category(scope)))


@bp.get("/api/category-presets/<scope>/<name>")
def get_category_preset(scope, name):
    if not _known_scope(scope):
        return error("未知的预设分类", 404)
    preset = studio().presets.load_category(scope, name)
    if preset is None:
        return error("分类预设不存在", 404)
    return jsonify(studio().migrate(preset))


@bp.post("/api/category-presets/<scope>")
def save_category_preset(scope):
    if not _known_scope(scope):
        return error("未知的预设分类", 404)
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    data = payload.get("data")
    if not name or not isinstance(name, str) or not isinstance(data, dict):
        return error("名称和分类数据不能为空")
    saved_name = studio().presets.save_category(scope, name, data)
    if saved_name is None:
        return error("保存失败", 500)
    return jsonify({"success": True, "name": saved_name})


@bp.delete("/api/category-presets/<scope>/<name>")
def delete_category_preset(scope, name):
    if not _known_scope(scope):
        return error("未知的预设分类", 404)
    if studio().presets.delete_category(scope, name):
        return jsonify({"success": True})
    return error("删除失败", 404)
