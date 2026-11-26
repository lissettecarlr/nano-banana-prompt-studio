"""图片渠道状态与生图。"""
from flask import Blueprint, jsonify, request
from loguru import logger

from nano_banana.core import ImageRequest, StudioError, UnknownProviderError
from nano_banana.web.context import error, studio

bp = Blueprint("images", __name__)

_LEGACY_OPTION_KEYS = ("aspect_ratio", "image_size", "thinking_level")


@bp.get("/api/image-providers")
def get_image_providers():
    return jsonify({status.id: status.to_dict() for status in studio().provider_statuses()})


@bp.post("/api/image-generation-settings")
def save_image_generation_settings():
    payload = request.get_json(silent=True) or {}
    provider = payload.get("provider")
    model = payload.get("model")
    options = payload.get("options")
    if not isinstance(provider, str) or provider not in studio().registry:
        return error(f"未知图片生成渠道: {provider}")
    if not isinstance(model, str) or not model.strip():
        return error("图片模型不能为空")
    if options is not None and not isinstance(options, dict):
        return error("生成参数必须是 JSON 对象")
    model = model.strip()
    try:
        settings = studio().settings
        settings.set_active_selection(provider, model)
        if options is not None:
            settings.save_generation_options(provider, model, options)
    except (OSError, TimeoutError) as exc:
        return error(f"生图设置保存失败: {exc}", 500)
    return jsonify({"success": True})


@bp.post("/api/generate-image")
def generate_image():
    data = request.get_json(silent=True) or {}

    # document 由服务端渲染成最终文本；prompt 是给已经自己拼好文本的调用方用的
    if isinstance(data.get("document"), dict):
        prompt = studio().render(data["document"]).text
    else:
        prompt = data.get("prompt") or ""

    options = data.get("options")
    if not isinstance(options, dict) or not options:
        options = {key: data[key] for key in _LEGACY_OPTION_KEYS if data.get(key)}
    images = data.get("images") or []
    if not isinstance(images, list):
        return error("images 必须是数组")

    try:
        result = studio().generate_image(
            ImageRequest(
                prompt=prompt,
                provider=data.get("provider") or "",
                model=data.get("model") or "",
                images=tuple(item for item in images if isinstance(item, str)),
                options=options,
            )
        )
    except (StudioError, UnknownProviderError) as exc:
        return error(str(exc))
    except Exception as exc:  # noqa: BLE001 — 渠道错误原样透传给用户
        logger.warning(f"生图失败: {exc}")
        return error(str(exc), 500)
    return jsonify({"image": result.to_data_url(), "provider": result.provider, "model": result.model})
