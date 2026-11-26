from unittest.mock import Mock, patch

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QMessageBox  # noqa: E402

from nano_banana.core import Change, PromptEvent  # noqa: E402
from nano_banana.core.prompt import build_document, default_negative_prompt  # noqa: E402
from nano_banana.desktop.components import TagTextInput  # noqa: E402
from nano_banana.desktop.dialogs import (  # noqa: E402
    AIGenerateDialog,
    AIModifyDialog,
    UnifiedAIConfigDialog,
)
from nano_banana.desktop.panels import PromptFormPanel  # noqa: E402
from nano_banana.desktop.workers import ImageGenerationThread, PromptStreamThread  # noqa: E402

NEGATIVE_TAGS = "反向提示词标签"
DEFAULT_TAG = "水印、签名、文字"


@pytest.fixture
def form(qapp, studio):
    panel = PromptFormPanel(studio)
    yield panel
    panel.deleteLater()


# ================= 表单面板 =================


def test_form_is_generated_from_the_schema(form, studio):
    assert list(form.field_widgets) == [field.widget_key for field in studio.schema.iter_fields()]
    assert set(form.category_preset_selectors) == set(studio.schema.category_ids)


def test_negative_prompt_is_enabled_by_default_and_restored_on_reset(form):
    assert default_negative_prompt() == DEFAULT_TAG
    assert form.negative_prompt_enabled.isChecked()
    assert form.negative_prompt_input.get_value() == DEFAULT_TAG
    assert form.document()["反向提示词"] == DEFAULT_TAG

    form.negative_prompt_enabled.setChecked(False)
    form.negative_prompt_input.set_value("别的")
    assert "反向提示词" not in form.document()

    form.reset()
    assert form.negative_prompt_enabled.isChecked()
    assert form.negative_prompt_input.get_value() == DEFAULT_TAG
    assert not form.negative_group.isHidden()


def test_document_roundtrip_through_the_form(form):
    document = build_document(
        {
            "styleMode": "插画",
            "location": "海边",
            "materialRealism": "皮肤纹理, 布料质感",
        },
        negative_prompt="水印",
        special_requirement="横图",
    )

    form.apply_document(document, replace=True)

    assert form.document() == document
    assert form.document()["审美控制"]["材质真实度"] == ["皮肤纹理", "布料质感"]
    assert form.special_requirement_enabled.isChecked()
    assert not form.is_line_art_mode()


def test_partial_document_only_touches_what_it_contains(form):
    form.field_widgets["风格模式"].set_value("插画")
    form.field_widgets["地点设定"].set_value("海边")

    form.apply_document({"场景": {"环境": {"地点设定": "森林"}}})

    assert form.field_widgets["风格模式"].get_value() == "插画"
    assert form.field_widgets["地点设定"].get_value() == "森林"
    assert form.negative_prompt_input.get_value() == DEFAULT_TAG  # overlay 没出现就不动


def test_legacy_preset_shapes_are_migrated_on_apply(form):
    form.apply_document({"反向提示词": {"禁止元素": ["水印", "文字"], "禁止风格": ["模糊"]}})
    assert form.negative_prompt_input.get_value() == "水印, 文字, 模糊"
    assert form.negative_prompt_enabled.isChecked()


def test_line_art_mode_disables_fields_and_changes_the_document(form, studio):
    studio.options.save_line_art_prompt("默认线稿")
    form.field_widgets["风格模式"].set_value("插画")

    form.line_art_mode_enabled.setChecked(True)

    assert form.is_line_art_mode()
    assert form.line_art_prompt_input.toPlainText() == "默认线稿"
    assert not form.field_widgets["风格模式"].isEnabled()
    assert not form.negative_prompt_enabled.isChecked()
    document = form.document()
    assert document["角色线稿生成"] == {"启用": True, "提示词": "默认线稿"}
    assert studio.render(document).text == "默认线稿"

    form.line_art_mode_enabled.setChecked(False)
    assert form.field_widgets["风格模式"].isEnabled()
    assert "角色线稿生成" not in form.document()


def test_save_line_art_prompt_persists_through_the_option_store(form, studio):
    messages = []
    form.message.connect(messages.append)
    form.line_art_mode_enabled.setChecked(True)
    form.line_art_prompt_input.setPlainText("新的线稿提示词")

    form.save_line_art_prompt_btn.click()

    assert studio.options.get_line_art_prompt() == "新的线稿提示词"
    assert messages == ["提示词保存成功"]


def test_changed_is_emitted_once_per_batch(form):
    emitted = []
    form.changed.connect(lambda: emitted.append(1))

    form.apply_document(
        build_document({"styleMode": "插画", "location": "海边"}, negative_prompt="x"), replace=True
    )
    assert len(emitted) == 1

    form.reset()
    assert len(emitted) == 2

    form.field_widgets["风格模式"].set_value("写实")
    assert len(emitted) == 3


def test_category_presets_save_and_load_only_their_slice(form, studio):
    form.field_widgets["风格模式"].set_value("插画")
    form.field_widgets["地点设定"].set_value("海边")

    with patch("nano_banana.desktop.panels.form_panel.QInputDialog.getText", return_value=("常用", True)):
        form._save_category_preset("basic", "基础设定")

    saved = studio.presets.load_category("basic", "常用")
    assert saved["风格模式"] == "插画"
    assert "场景" not in saved
    selector = form.category_preset_selectors["basic"]
    assert selector.findData("常用") >= 0 or selector.findText("常用") >= 0

    form.field_widgets["风格模式"].set_value("写实")
    form.field_widgets["地点设定"].set_value("森林")
    index = max(selector.findData("常用"), selector.findText("常用"))
    form._load_category_preset("basic", index)

    assert form.field_widgets["风格模式"].get_value() == "插画"
    assert form.field_widgets["地点设定"].get_value() == "森林"  # 别的分类不受影响


# ================= 标签输入 =================


def test_tag_fills_input_without_duplicating_it(qapp):
    widget = TagTextInput(NEGATIVE_TAGS, [DEFAULT_TAG])
    widget._apply_tag(DEFAULT_TAG)
    widget._apply_tag(DEFAULT_TAG)
    assert widget.get_value() == DEFAULT_TAG

    widget._apply_tag("低清晰度")
    assert widget.get_value() == f"{DEFAULT_TAG}, 低清晰度"


def test_tag_is_added_from_the_dedicated_input(qapp):
    option_store = Mock()
    widget = TagTextInput(NEGATIVE_TAGS, [], option_store=option_store)
    widget.set_value("已有反向提示词")
    widget.tag_input.setText("低清晰度")

    widget._add_new_tag()

    assert widget._options == ["低清晰度"]
    assert widget.get_value() == "已有反向提示词"
    assert widget.tag_input.text() == ""
    option_store.add_option.assert_called_once_with(NEGATIVE_TAGS, "低清晰度")


def test_tag_can_be_deleted(qapp):
    option_store = Mock()
    widget = TagTextInput(NEGATIVE_TAGS, [DEFAULT_TAG], option_store=option_store)

    widget._delete_tag(DEFAULT_TAG)

    assert widget._options == []
    option_store.remove_option.assert_called_once_with(NEGATIVE_TAGS, DEFAULT_TAG)


def test_tags_persist_through_the_real_option_store(form, studio):
    tags = form.negative_prompt_input
    tags.tag_input.setText("低清晰度")
    tags._add_new_tag()
    assert studio.options.get_field_options(NEGATIVE_TAGS) == [DEFAULT_TAG, "低清晰度"]

    tags._delete_tag(DEFAULT_TAG)
    assert studio.options.get_field_options(NEGATIVE_TAGS) == ["低清晰度"]


# ================= 配置对话框 =================


def test_config_dialog_lists_registered_providers_and_prefills_defaults(qapp, studio):
    studio.settings.update({"chat": {"base_url": "https://chat", "api_key": "ck", "model": "cm"}})
    dialog = UnifiedAIConfigDialog(studio, initial_tab="image", image_provider="doubao_image")

    labels = [
        dialog.image_provider_input.item(row).text() for row in range(dialog.image_provider_input.count())
    ]
    assert labels == [
        f"{spec.label}\n未配置" for spec in studio.registry
    ]
    assert len(labels) == 4
    assert dialog.config_tabs.currentIndex() == 1
    assert dialog._current_image_provider == "doubao_image"
    assert dialog.image_url_input.text() == "https://ark.cn-beijing.volces.com/api/v3"
    assert dialog.image_model_input.currentText() == "doubao-seedream-5-0-pro-260628"
    assert dialog.image_key_input.text() == ""
    assert (dialog.prompt_url_input.text(), dialog.prompt_key_input.text(), dialog.prompt_model_input.text()) == (
        "https://chat",
        "ck",
        "cm",
    )
    dialog.deleteLater()


def test_config_dialog_keeps_drafts_across_provider_switches_and_saves_all(qapp, studio):
    dialog = UnifiedAIConfigDialog(studio, initial_tab="image", image_provider="doubao_image")
    saved = []
    dialog.config_saved.connect(lambda: saved.append(True))

    dialog.image_key_input.setText(" doubao-key ")
    dialog.image_provider_input.setCurrentRow(0)  # gemini
    assert dialog.image_provider_input.item(3).text().endswith("\n✓ 已配置")
    dialog.image_url_input.setText("https://gemini.example")
    dialog.image_key_input.setText("gemini-key")
    dialog.image_model_input.setEditText("my-gemini")
    dialog.prompt_key_input.setText("chat-key")

    dialog._save_config()

    assert saved == [True]
    assert studio.chat_settings().api_key == "chat-key"
    doubao = studio.settings.credentials("doubao_image")
    assert doubao.api_key == "doubao-key"
    gemini = studio.settings.credentials("gemini")
    assert (gemini.base_url, gemini.api_key, gemini.model) == (
        "https://gemini.example",
        "gemini-key",
        "my-gemini",
    )
    assert studio.settings.providers_with_api_key() == ["gemini", "doubao_image"]
    dialog.deleteLater()


# ================= AI 对话框 =================


def test_generate_dialog_applies_the_parsed_document(qapp, studio):
    dialog = AIGenerateDialog(studio)
    emitted = []
    dialog.generated.connect(emitted.append)

    dialog._on_result(PromptEvent("result", '{"风格模式": "插画"}', document={"风格模式": "插画"}))
    dialog._on_apply()

    assert emitted == [{"风格模式": "插画"}]
    dialog.deleteLater()


def test_generate_dialog_refuses_to_apply_unparseable_output(qapp, studio):
    dialog = AIGenerateDialog(studio)
    emitted = []
    dialog.generated.connect(emitted.append)

    dialog._on_result(PromptEvent("result", "不是 JSON", parse_error="AI返回的内容不是有效的JSON"))
    with patch.object(QMessageBox, "warning") as warning:
        dialog._on_apply()

    assert emitted == []
    assert warning.called
    dialog.deleteLater()


def test_modify_dialog_applies_only_the_checked_changes(qapp, studio):
    current = build_document({"styleMode": "插画", "location": "海边"}, special_requirement="横图")
    dialog = AIModifyDialog(studio, current)
    emitted = []
    dialog.modified.connect(emitted.append)
    changes = (
        Change(("风格模式",), "changed", old="插画", new="写实"),
        Change(("场景", "环境", "地点设定"), "changed", old="海边", new="森林"),
    )

    dialog._on_result(PromptEvent("result", "{}", document={}, changes=changes))

    assert dialog.diff_items == list(changes)
    assert len(dialog.diff_checkboxes) == 2
    dialog.diff_checkboxes[1].setChecked(False)
    dialog._on_apply()

    assert len(emitted) == 1
    result = emitted[0]
    assert result["风格模式"] == "写实"
    assert result["场景"]["环境"]["地点设定"] == "海边"  # 没勾选的不应用
    assert result["特别要求"] == "横图"  # 模型看不到的部分原样保留
    dialog.deleteLater()


# ================= 后台线程 =================


def test_prompt_stream_thread_translates_events_to_signals(qapp):
    result_event = PromptEvent("result", "{}", document={})
    events = [
        PromptEvent("started"),
        PromptEvent("thinking"),
        PromptEvent("content", "{"),
        PromptEvent("content", "}"),
        result_event,
    ]
    thread = PromptStreamThread(lambda _cancelled: iter(events))
    seen = {"progress": [], "chunk": [], "result": [], "error": []}
    for name in seen:
        getattr(thread, name).connect(seen[name].append)

    thread.run()  # 同步执行，不起线程

    assert seen["progress"] == ["正在处理输入...", "正在连接AI服务...", "模型思考中..."]
    assert seen["chunk"] == ["{", "}"]
    assert seen["result"] == [result_event]
    assert seen["error"] == []


def test_prompt_stream_thread_reports_errors_and_closes_the_stream(qapp, studio):
    closed = []

    def stream(_cancelled):
        try:
            yield PromptEvent("started")
            yield PromptEvent("error", "上游失败")
        finally:
            closed.append(True)

    thread = PromptStreamThread(stream)
    errors = []
    thread.error.connect(errors.append)
    thread.run()
    assert errors == ["上游失败"] and closed == [True]

    # 未配置：Studio 立即抛 StudioError，线程把它变成 error 信号
    thread = PromptStreamThread(lambda cancelled: studio.generate_prompt("x", cancelled=cancelled))
    thread.error.connect(errors.append)
    thread.run()
    assert errors[-1] == "请先配置API密钥"


def test_cancelled_prompt_stream_emits_nothing_more(qapp):
    thread = PromptStreamThread(
        lambda _cancelled: iter([PromptEvent("content", "a"), PromptEvent("content", "b")])
    )
    chunks = []
    thread.chunk.connect(lambda text: (chunks.append(text), thread.cancel()))
    thread.run()
    assert chunks == ["a"]


def test_image_thread_emits_png_bytes_or_the_raw_error(qapp, fake_studio, backend_log):
    from nano_banana.core import ImageRequest

    fake_studio.settings.update({"image": {"providers": {"fake": {"api_key": "k"}}}})
    request = ImageRequest(prompt="p", provider="fake", images=("a.png",))

    thread = ImageGenerationThread(fake_studio, request, "Fake")
    seen = {"progress": [], "image_ready": [], "error": []}
    for name in seen:
        getattr(thread, name).connect(seen[name].append)
    thread.run()

    assert seen["progress"] == ["正在生成图片（Fake，含 1 张参考图）..."]
    assert seen["image_ready"][0].startswith(b"\x89PNG")
    assert seen["error"] == []

    backend_log.error = RuntimeError("上游原始错误")
    thread = ImageGenerationThread(fake_studio, request)
    errors = []
    thread.error.connect(errors.append)
    thread.run()
    assert errors == ["上游原始错误"]
