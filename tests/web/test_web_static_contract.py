"""静态前端与核心之间的契约：DOM id / 脚本顺序 / 关键样式。

这些是纯文本断言，目的是在「改了 schema 或后端协议却忘了改前端」时尽早报错。
"""
import re
import shutil
import subprocess

import pytest
from conftest import STATIC

from nano_banana.core.prompt import default_negative_prompt, get_schema


def _read(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def test_scripts_load_in_dependency_order():
    html = _read("index.html")
    order = [
        html.index(f'<script src="/static/{name}"></script>')
        for name in ("sse-parser.js", "schema-form.js", "script.js", "image-gen.js", "ai-stream.js", "structured-ui.js")
    ]
    assert order == sorted(order)


def test_stream_handler_finishes_the_parser_inside_the_try_block():
    script = _read("ai-stream.js")
    stream_handler = script.split("async function handleAiExecute()", 1)[1].split(
        "function handleAiStop()", 1
    )[0]
    assert stream_handler.index("sseParser.finish();") < stream_handler.rfind("} catch (e) {")


def test_web_field_ids_match_schema():
    schema = get_schema()
    html = _read("index.html")
    for field in schema.iter_fields():
        assert f'id="{field.id}"' in html, field.id
        assert (
            f'data-field-name="{field.widget_key}"' in html
            or f'data-field-name="{field.label}"' in html
        ), field.widget_key
    for category in schema.categories:
        assert f'id="tab-{category.id}"' in html, category.id


def test_aesthetic_labels_follow_the_schema():
    schema = get_schema()
    field = schema.get_field("specialEffects")
    assert (field.label, field.widget_key) == ("后期效果", "特殊效果")
    assert schema.get_category("aesthetic").label == "调色与质感"

    html = _read("index.html")
    assert 'data-tab="aesthetic"' in html
    assert 'data-preset-label="调色与质感"' in html
    assert '<label for="specialEffects">后期效果' in html


def test_negative_prompt_is_enabled_by_default_with_the_schema_default():
    html = _read("index.html")
    assert "checked" in html.split('id="negativePromptEnabled"', 1)[1].split(">", 1)[0]
    textarea = html.split('id="negativePromptInput"', 1)[1].split("</textarea>", 1)[0]
    assert textarea.endswith(">" + default_negative_prompt())
    # JS 里不再硬编码默认值
    assert default_negative_prompt() not in _read("script.js")


def test_structured_layout_still_uses_single_line_controls():
    html = _read("index.html")
    structured = html.split('id="tab-basic"', 1)[1].split('id="tab-advanced"', 1)[0]
    assert "<textarea" not in structured
    subject = html.split('id="tab-subject"', 1)[1].split('id="tab-camera"', 1)[0]
    assert 'class="form-grid form-grid-two-column"' in subject


def test_generation_preview_css_keeps_stable_scrollbar_and_wraps_errors():
    style = _read("style.css")
    assert "scrollbar-gutter: stable" in style
    assert "if (hasGeneratedContent && !hadGeneratedContent)" in _read("structured-ui.js")

    inspector = re.search(r"\.inspector-panel\s*\{([^}]+)\}", style).group(1)
    assert "height: calc(100vh - var(--header-height))" in inspector

    error_rule = re.search(r"\.generation-error-message\s*\{([^}]+)\}", style).group(1)
    assert "overflow-wrap: anywhere" in error_rule
    assert "white-space: pre-wrap" in error_rule
    assert "min-width: 0" in error_rule
    assert re.search(r"\.result-preview\.has-error\s*\{[^}]*overflow:\s*visible;", style)

    image_gen = _read("image-gen.js")
    assert "errorState.className = 'generation-error';" in image_gen
    assert "errorState.setAttribute('role', 'alert');" in image_gen
    assert "elements.resultPreview.classList.add('has-error');" in image_gen
    assert "message.textContent = e.message;" in image_gen  # 渠道错误原样展示，且不走 innerHTML


def test_frontend_delegates_prompt_logic_to_the_server():
    """渲染 / 解析 / diff 只有服务端一份实现，前端不能再长出第二份。"""
    script = _read("script.js")
    image_gen = _read("image-gen.js")
    ai_stream = _read("ai-stream.js")
    schema_js = _read("schema-form.js")

    assert "/api/schema" in schema_js
    assert "PromptDoc.nestFromElements" in script
    assert "hydrateFromSchema" in _read("structured-ui.js")
    assert "/api/prompt/render" in script
    assert "document: getFormData()" in image_gen
    assert "body.document = getFormData()" in ai_stream
    assert "function diffJson" not in ai_stream
    assert "current_data" not in ai_stream
    for source in (script, image_gen, ai_stream):
        assert "特别要求：" not in source
        assert "额外要求：" not in source


def test_config_modal_is_generated_from_provider_specs():
    """新增图片渠道不需要改前端：配置表单由 /api/image-providers 渲染。"""
    html = _read("index.html")
    image_gen = _read("image-gen.js")

    assert 'id="configImageProviderFields"' in html
    assert re.search(r'<select id="configImageProvider"[^>]*></select>', html)
    assert "renderImageProviderConfigFields" in image_gen
    for hardcoded in ("gemini", "qwen", "doubao", "openai_images"):
        assert hardcoded not in html.lower(), hardcoded
        assert hardcoded not in image_gen.lower(), hardcoded
    for legacy_key in ("gemini_api_key", "image_provider", "image_generation_options"):
        assert legacy_key not in image_gen
        assert legacy_key not in _read("script.js")


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js is required for syntax checks")
@pytest.mark.parametrize("path", sorted(STATIC.glob("*.js")), ids=lambda path: path.name)
def test_static_scripts_are_syntactically_valid(path):
    result = subprocess.run(
        ["node", "--check", str(path)], capture_output=True, text=True, encoding="utf-8", check=False
    )
    assert result.returncode == 0, result.stderr
