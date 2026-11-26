"""最终提示词的渲染规则。桌面端、Web、任何新交互口都以这里的结果为准。"""
import json

from nano_banana.core.prompt import (
    build_document,
    migrate_document,
    normalize_negative_prompt,
    payload_json,
    prompt_payload,
    render_prompt,
)


def _document(**overlays):
    return build_document({"styleMode": "插画", "location": "海边"}, **overlays)


def test_plain_document_renders_as_indented_json():
    document = _document(negative_prompt="水印")
    rendered = render_prompt(document)

    assert rendered.mode == "json"
    assert rendered.text == json.dumps(document, ensure_ascii=False, indent=2)
    assert json.loads(rendered.text)["反向提示词"] == "水印"
    assert rendered.payload == document


def test_special_requirement_is_appended_after_json_not_inside_it():
    rendered = render_prompt(_document(special_requirement="  不要出现文字 "))

    body, _, suffix = rendered.text.partition("\n\n特别要求：")
    assert suffix == "不要出现文字"
    assert "特别要求" not in json.loads(body)
    assert "特别要求" not in rendered.payload


def test_line_art_mode_uses_only_the_line_art_prompt():
    rendered = render_prompt(
        _document(negative_prompt="水印", line_art_prompt="画一张线稿", special_requirement="侧身")
    )

    assert rendered.mode == "line_art"
    assert rendered.text == "画一张线稿\n\n额外要求：侧身"
    assert "插画" not in rendered.text


def test_empty_line_art_prompt_renders_empty_even_with_special_requirement():
    rendered = render_prompt(_document(line_art_prompt="", special_requirement="侧身"))
    assert rendered.is_empty


def test_disabled_line_art_block_is_ignored():
    document = _document()
    document["角色线稿生成"] = {"启用": False, "提示词": "画一张线稿"}
    rendered = render_prompt(document)

    assert rendered.mode == "json"
    assert "角色线稿生成" not in rendered.payload


def test_payload_is_what_the_chat_model_sees():
    document = _document(negative_prompt="水印", special_requirement="x", line_art_prompt="y")
    payload = prompt_payload(document)

    assert set(payload) == set(document) - {"特别要求", "角色线稿生成"}
    assert json.loads(payload_json(document)) == payload
    assert "特别要求" in document  # 入参不被修改


def test_render_to_dict_is_json_serializable():
    data = render_prompt(_document(special_requirement="x")).to_dict()
    assert set(data) == {"text", "mode", "payload", "is_empty"}
    json.dumps(data, ensure_ascii=False)


def test_document_without_any_content_renders_empty_instead_of_braces():
    for document in ({}, None, {"特别要求": "只有特别要求"}):
        rendered = render_prompt(document)
        assert (rendered.text, rendered.mode, rendered.payload) == ("", "json", {})
        assert rendered.is_empty
    # 表单把所有字段都交上来（哪怕全是空串）时，仍按 JSON 发送
    assert not render_prompt(_document()).is_empty


# ---------------- 旧格式兼容 ----------------


def test_legacy_negative_prompt_groups_are_joined():
    value = normalize_negative_prompt({"禁止元素": ["水印", "文字"], "禁止风格": ["模糊"]})
    assert value == "水印, 文字, 模糊"
    assert normalize_negative_prompt("原样") == "原样"
    assert normalize_negative_prompt(None) == ""


def test_migrate_upgrades_legacy_shapes_without_touching_the_input():
    legacy = {
        "风格模式": "插画",
        "反向提示词": {"禁止元素": ["水印"], "禁止风格": ["模糊"]},
        "场景": {"主体": {"表情与动作": "挥手"}},
    }
    migrated = migrate_document(legacy)

    assert migrated["反向提示词"] == "水印, 模糊"
    assert migrated["场景"]["主体"]["表情与动作"] == {"情绪": "", "动作": "挥手"}
    assert migrated["风格模式"] == "插画"
    assert legacy["场景"]["主体"]["表情与动作"] == "挥手"


def test_migrate_is_idempotent_and_tolerates_garbage():
    current = build_document({"emotion": "开心", "action": "挥手"}, negative_prompt="水印")
    assert migrate_document(current) == current
    assert migrate_document(migrate_document(current)) == current
    assert migrate_document(None) == {}
    assert migrate_document(["not", "a", "dict"]) == {}
    assert "反向提示词" not in migrate_document({"风格模式": "x"})
