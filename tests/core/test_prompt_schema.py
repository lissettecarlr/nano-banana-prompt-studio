import os
import subprocess
import sys
from pathlib import Path

from nano_banana.core.prompt import (
    apply_partial,
    build_document,
    default_negative_prompt,
    flatten,
    get_line_art,
    get_schema,
    get_special_requirement,
    nest,
    overlay_by_id,
    subset,
)

ROOT = Path(__file__).resolve().parents[2]


def test_schema_has_expected_categories_and_web_ids():
    schema = get_schema()
    assert schema.category_ids == ("basic", "scene", "subject", "camera", "aesthetic")
    assert "depth" in schema.field_ids
    assert "clothingDetails" in schema.field_ids
    assert schema.get_field("background").path == ("场景", "背景", "描述")
    assert schema.get_field("clothingDetails").widget_key == "服装细节"


def test_aesthetic_controls_use_precise_display_labels_with_compatible_keys():
    schema = get_schema()
    field = schema.get_field("specialEffects")
    assert field.label == "后期效果"
    assert field.widget_key == "特殊效果"
    assert schema.get_category("aesthetic").label == "调色与质感"


def test_overlays_declare_what_the_model_may_see():
    assert default_negative_prompt() == "水印、签名、文字"
    assert overlay_by_id("negativePrompt").ui_only is False
    assert overlay_by_id("specialRequirement").ui_only is True
    assert overlay_by_id("lineArt").ui_only is True


def test_nest_flatten_roundtrip_and_string_list():
    schema = get_schema()
    flat = {field.id: "值" for field in schema.iter_fields()}
    flat["materialRealism"] = "皮肤, 头发"
    nested = nest(flat, schema)
    assert nested["风格模式"] == "值"
    assert nested["场景"]["背景"]["景深"] == "值"
    assert nested["场景"]["主体"]["服装"]["细节"] == "值"
    assert nested["审美控制"]["材质真实度"] == ["皮肤", "头发"]
    back = flatten(nested, schema)
    assert back["depth"] == "值"
    assert back["clothingDetails"] == "值"
    assert back["materialRealism"] == "皮肤, 头发"


def test_flatten_only_reports_present_fields_unless_asked():
    assert flatten({"风格模式": "插画"}) == {"styleMode": "插画"}
    full = flatten({"风格模式": "插画"}, include_missing=True)
    assert full["styleMode"] == "插画"
    assert full["depth"] == ""
    assert set(full) == set(get_schema().field_ids)


def test_subset_only_keeps_one_category():
    data = nest({"styleMode": "插画", "atmosphere": "清透", "location": "海边"}, include_empty=True)
    sliced = subset(data, "basic")
    assert sliced == {"风格模式": "插画", "画面气质": "清透"}
    assert "场景" not in sliced


def test_apply_partial_does_not_clobber_missing_keys():
    dst = {"风格模式": "A", "画面气质": "B", "场景": {"环境": {"光线": "旧"}}}
    src = {"画面气质": "C", "场景": {"环境": {"天气氛围": "雨"}}}
    merged = apply_partial(dst, src)
    assert merged["风格模式"] == "A"
    assert merged["画面气质"] == "C"
    assert merged["场景"]["环境"]["光线"] == "旧"
    assert merged["场景"]["环境"]["天气氛围"] == "雨"
    assert dst["画面气质"] == "B"  # 入参不被修改


def test_build_document_only_writes_enabled_overlays():
    plain = build_document({"styleMode": "插画"})
    assert plain["风格模式"] == "插画"
    assert "反向提示词" not in plain
    assert "特别要求" not in plain
    assert "角色线稿生成" not in plain

    full = build_document(
        {"styleMode": "插画"},
        negative_prompt="水印",
        special_requirement="不要文字",
        line_art_prompt="画线稿",
    )
    assert full["反向提示词"] == "水印"
    assert get_special_requirement(full) == "不要文字"
    assert get_line_art(full) == (True, "画线稿")
    # 根键顺序跟 schema 一致，overlay 排在字段之后
    assert list(full)[0] == "风格模式"


def test_system_prompt_contains_schema_example_json():
    from nano_banana.core.llm.prompts import SYSTEM_PROMPT, build_system_prompt_example

    example = build_system_prompt_example()
    assert '"风格模式"' in example
    assert '"景深"' in example
    assert example in SYSTEM_PROMPT


def test_importing_core_does_not_load_sdks_or_ui_toolkits():
    """交互口（尤其是插件）只想用 schema / Studio 时，不该被迫加载各家 SDK。"""
    code = (
        "import sys\n"
        "from nano_banana.core.prompt import get_schema\n"
        "assert get_schema().get_field('depth').id == 'depth'\n"
        "assert 'nano_banana.core.studio' not in sys.modules\n"
        "from nano_banana.core import Studio, StudioPaths\n"
        "import tempfile, pathlib\n"
        "studio = Studio(StudioPaths(pathlib.Path(tempfile.mkdtemp())))\n"
        "assert len(studio.provider_statuses()) >= 4\n"
        "for name in ('openai', 'google.genai', 'httpx', 'flask', 'PyQt6'):\n"
        "    assert name not in sys.modules, name\n"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
    )
    assert result.returncode == 0, result.stderr or result.stdout
