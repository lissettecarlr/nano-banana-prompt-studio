from unittest.mock import patch

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtGui import QColor, QPixmap  # noqa: E402
from PyQt6.QtWidgets import QApplication, QInputDialog, QMessageBox  # noqa: E402

from nano_banana.core import ImageRequest  # noqa: E402
from nano_banana.desktop.main_window import MainWindow  # noqa: E402
from nano_banana.desktop.panels import image_panel as image_panel_module  # noqa: E402


@pytest.fixture
def make_window(qapp):
    windows = []

    def factory(studio) -> MainWindow:
        window = MainWindow(studio)
        windows.append(window)
        return window

    yield factory
    for window in windows:
        window.image_panel.cancel_generation()
        window.close()
        window.deleteLater()
    qapp.processEvents()


def _set_keys(studio, **api_keys):
    studio.settings.update(
        {"image": {"providers": {provider: {"api_key": key} for provider, key in api_keys.items()}}}
    )


def _provider_ids(window) -> list:
    combo = window.image_panel.provider_combo
    return [combo.itemData(index) for index in range(combo.count())]


# ================= 生图面板：渠道 / 参数 =================


def test_provider_combo_shows_only_channels_with_api_keys_and_falls_back(studio, make_window):
    studio.settings.update(
        {
            "image": {
                "active": "gemini",
                "providers": {
                    "gemini": {"base_url": "https://gemini.example", "api_key": "gemini-key"},
                    "qwen_image": {"api_key": "qwen-key"},
                },
            }
        }
    )
    window = make_window(studio)
    panel = window.image_panel

    assert _provider_ids(window) == ["gemini", "qwen_image"]
    assert panel.provider_combo.currentData() == "gemini"
    assert panel.config_status.text() == ""

    # 配置对话框保存后：删掉 gemini 的密钥，自动落到剩下的渠道
    _set_keys(studio, gemini="")
    panel.reload_providers()

    assert _provider_ids(window) == ["qwen_image"]
    assert panel.provider_combo.currentData() == "qwen_image"
    assert studio.settings.active_provider() == "qwen_image"


def test_provider_combo_has_disabled_empty_state_without_api_keys(studio, make_window):
    window = make_window(studio)
    panel = window.image_panel

    assert panel.provider_combo.count() == 1
    assert panel.provider_combo.currentData() is None
    assert not panel.provider_combo.isEnabled()
    assert not panel.model_combo.isEnabled()
    assert not panel.generate_button.isEnabled()
    assert "填写密钥" in panel.config_status.text()
    assert not studio.paths.settings_file.exists()  # 只是打开窗口，不应该写配置


def test_image_options_use_a_compact_two_column_grid(studio, make_window):
    _set_keys(studio, qwen_image="qwen-key")
    studio.settings.set_active_selection("qwen_image")
    panel = make_window(studio).image_panel

    positions = [
        panel.options_layout.getItemPosition(index) for index in range(panel.options_layout.count())
    ]
    assert positions == [(0, 0, 1, 1), (0, 1, 1, 1), (1, 0, 1, 1), (1, 1, 1, 1)]
    assert list(panel.option_widgets) == [
        "aspect_ratio",
        "image_size",
        "prompt_extend",
        "prompt_extend_mode",
    ]
    assert panel.config_status.text() == "未配置"  # 千问没有默认 Base URL


def test_options_follow_the_model_and_are_remembered_per_model(fake_studio, make_window):
    _set_keys(fake_studio, fake="k")
    panel = make_window(fake_studio).image_panel

    assert list(panel.option_widgets) == ["aspect_ratio", "image_size"]
    panel.option_widgets["aspect_ratio"].setCurrentText("16:9")
    panel.option_widgets["image_size"].setCurrentText("1K")

    panel.model_combo.setCurrentText("fake-model-lite")
    assert list(panel.option_widgets) == ["aspect_ratio"]  # lite 模型没有尺寸选项
    assert panel.collect_options() == {"aspect_ratio": "1:1"}
    assert fake_studio.settings.credentials("fake").model == "fake-model-lite"

    panel.model_combo.setCurrentText("fake-model")
    assert panel.collect_options() == {"aspect_ratio": "16:9", "image_size": "1K"}
    assert fake_studio.settings.generation_options("fake", "fake-model") == {
        "aspect_ratio": "16:9",
        "image_size": "1K",
    }


def test_switching_provider_updates_models_and_active_selection(fake_studio, make_window):
    _set_keys(fake_studio, fake="k", other="k")
    fake_studio.settings.update({"image": {"providers": {"other": {"model": "custom-model"}}}})
    panel = make_window(fake_studio).image_panel

    panel.provider_combo.setCurrentIndex(panel.provider_combo.findData("other"))

    assert fake_studio.settings.active_provider() == "other"
    models = [panel.model_combo.itemText(index) for index in range(panel.model_combo.count())]
    assert models == ["fake-model", "fake-model-lite", "custom-model"]
    assert panel.model_combo.currentText() == "custom-model"


# ================= 生图面板：预览 / 错误 =================


def test_preview_image_fits_inside_canvas_at_minimum_window_size(studio, make_window, qapp):
    window = make_window(studio)
    window.resize(window.minimumSize())
    window.show()
    qapp.processEvents()

    source = QPixmap(1600, 900)
    source.fill(QColor("red"))
    preview = window.image_panel.preview_area
    preview.setSourcePixmap(source)
    qapp.processEvents()

    canvas = preview.parentWidget()
    displayed = preview.pixmap()
    assert canvas.contentsRect().contains(preview.geometry()), (
        f"preview {preview.geometry()} overflows canvas {canvas.contentsRect()}"
    )
    assert preview.contentsRect().height() >= 120
    assert displayed.width() <= preview.contentsRect().width()
    assert displayed.height() <= preview.contentsRect().height()


def test_long_generation_error_does_not_collapse_main_splitter(studio, make_window, qapp):
    window = make_window(studio)
    window.resize(1400, 900)
    window.show()
    qapp.processEvents()

    sizes_before = window.main_splitter.sizes()
    error_message = (
        "ContentFilterError.IntentDetected.PolicyViolation: "
        + "x" * 800
        + "; Request id: 021786687661009b75b42a52114d75a63a7057f0ece04dd564b0c"
    )
    window.image_panel._on_generation_error(error_message)
    qapp.processEvents()

    sizes_after = window.main_splitter.sizes()
    assert sizes_after[0] > sizes_before[0] * 0.8, f"{sizes_before} -> {sizes_after}"
    # 错误详情走非阻塞弹窗，状态栏只显示简短文案
    assert window.image_panel.status_label.text() == "生成失败"
    assert window.image_panel.status_label.toolTip() == error_message
    for box in window.image_panel.findChildren(QMessageBox):
        box.close()


def test_reference_images_are_capped_deduplicated_and_removable(studio, make_window):
    panel = make_window(studio).image_panel

    panel.add_reference_paths(["a.png", "b.png", "a.png"])
    assert panel.selected_images == ["a.png", "b.png"]
    panel.add_reference_paths(["c.png", "d.png"])
    assert panel.selected_images == ["a.png", "b.png", "c.png"]
    assert [button.text() for button in panel.image_buttons] == ["图一", "图二", "图三"]

    panel.image_buttons[0].click()
    assert panel.selected_images == ["b.png", "c.png"]
    assert [button.text() for button in panel.image_buttons] == ["图一", "图二"]

    panel.reset()
    assert panel.selected_images == [] and panel.image_buttons == []


# ================= 生成请求 =================


class _RecordingThread:
    """替身生图线程：只记录请求，不起线程。"""

    instances: list = []

    def __init__(self, studio, request, provider_label=""):
        self.request = request
        self.provider_label = provider_label
        type(self).instances.append(self)
        self.progress = self.image_ready = self.error = self.finished = _Signal()

    def start(self):
        pass

    def isRunning(self):
        return False

    def cancel(self):
        pass


class _Signal:
    def connect(self, _slot):
        pass

    def disconnect(self):
        pass


@pytest.fixture
def recorded_requests(monkeypatch):
    _RecordingThread.instances = []
    monkeypatch.setattr(image_panel_module, "ImageGenerationThread", _RecordingThread)
    return _RecordingThread.instances


def test_generate_sends_the_rendered_prompt_and_current_selection(
    fake_studio, make_window, recorded_requests
):
    _set_keys(fake_studio, fake="k")
    window = make_window(fake_studio)
    form, panel = window.form_panel, window.image_panel
    form.field_widgets["风格模式"].set_value("插画")
    form.special_requirement_enabled.setChecked(True)
    form.special_requirement_input.setPlainText("横图")
    panel.option_widgets["aspect_ratio"].setCurrentText("16:9")
    panel.add_reference_paths(["ref.png"])

    panel.generate_button.click()

    assert len(recorded_requests) == 1
    request = recorded_requests[0].request
    assert isinstance(request, ImageRequest)
    assert request.prompt == window.json_preview.toPlainText()  # 预览即所发
    assert request.prompt == fake_studio.render(form.document()).text
    assert request.prompt.endswith("\n\n特别要求：横图")
    assert (request.provider, request.model) == ("fake", "fake-model")
    assert request.images == ("ref.png",)
    assert request.options == {"aspect_ratio": "16:9", "image_size": "2K"}
    assert recorded_requests[0].provider_label == "Fake fake"


def test_line_art_mode_sends_only_the_line_art_prompt(fake_studio, make_window, recorded_requests):
    _set_keys(fake_studio, fake="k")
    fake_studio.options.save_line_art_prompt("画线稿")
    window = make_window(fake_studio)
    window.form_panel.field_widgets["风格模式"].set_value("插画")
    window.form_panel.line_art_mode_enabled.setChecked(True)

    window.image_panel.generate_button.click()

    assert recorded_requests[0].request.prompt == "画线稿"
    assert window.json_preview.toPlainText() == "画线稿"


def test_generate_asks_to_configure_an_incomplete_provider(studio, make_window, recorded_requests):
    _set_keys(studio, qwen_image="k")  # 缺 Base URL
    window = make_window(studio)
    requested = []
    window.image_panel.config_requested.disconnect()
    window.image_panel.config_requested.connect(requested.append)
    window.image_panel.generate_button.setEnabled(True)

    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
        window.image_panel._on_generate_clicked()

    assert requested == ["qwen_image"]
    assert recorded_requests == []


def test_empty_line_art_prompt_is_rejected_before_any_request(
    fake_studio, make_window, recorded_requests
):
    _set_keys(fake_studio, fake="k")
    window = make_window(fake_studio)
    window.form_panel.line_art_mode_enabled.setChecked(True)
    window.form_panel.line_art_prompt_input.clear()

    with patch.object(QMessageBox, "warning") as warning:
        window.image_panel.generate_button.click()

    assert warning.call_args.args[2] == "线稿提示词不能为空"
    assert recorded_requests == []


# ================= 主窗口：预览 / 预设 / AI 结果 =================


def test_preview_tracks_the_form_and_copy_uses_the_final_prompt(studio, make_window):
    window = make_window(studio)
    form = window.form_panel

    form.field_widgets["风格模式"].set_value("厚涂")
    assert '"风格模式": "厚涂"' in window.json_preview.toPlainText()
    assert window.json_preview.toPlainText() == studio.render(form.document()).text

    window._copy_to_clipboard()
    assert QApplication.clipboard().text() == window.json_preview.toPlainText()

    assert not window.json_preview_area.isVisibleTo(window)
    window._toggle_preview()
    assert window.json_preview_visible and window.json_toggle_btn.text() == "JSON隐藏"
    window._toggle_preview()
    assert not window.json_preview_visible and window.json_toggle_btn.text() == "JSON浏览"


def test_preset_roundtrip_keeps_overlays(studio, make_window):
    window = make_window(studio)
    form = window.form_panel
    form.field_widgets["风格模式"].set_value("插画")
    form.negative_prompt_input.set_value("水印, 模糊")
    form.special_requirement_enabled.setChecked(True)
    form.special_requirement_input.setPlainText("横图")
    saved_document = form.document()

    with patch.object(QInputDialog, "getText", return_value=("我的/预设", True)):
        window._save_as_preset()

    assert window.current_preset_name == "我的预设"
    assert window.preset_selector.currentData() == "我的预设"
    assert studio.presets.load("我的预设") == saved_document

    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
        window._clear_form()
    assert form.field_widgets["风格模式"].get_value() == ""
    assert not form.special_requirement_enabled.isChecked()
    assert window.current_preset_name is None

    window.preset_selector.setCurrentIndex(window.preset_selector.findData("我的预设"))
    assert form.document() == saved_document
    assert window.current_preset_name == "我的预设"

    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
        window._delete_preset("我的预设")
    assert studio.presets.list_all() == []
    assert window.preset_selector.count() == 1
    assert window.current_preset_name is None


def test_ai_generated_document_merges_and_ai_modified_document_replaces(studio, make_window):
    window = make_window(studio)
    form = window.form_panel
    form.field_widgets["风格模式"].set_value("插画")
    form.field_widgets["地点设定"].set_value("海边")
    form.special_requirement_enabled.setChecked(True)
    form.special_requirement_input.setPlainText("横图")

    # AI 生成：只覆盖返回的部分，用户自己的特别要求保留
    window._on_ai_generated({"风格模式": "写实"})
    assert form.field_widgets["风格模式"].get_value() == "写实"
    assert form.field_widgets["地点设定"].get_value() == "海边"
    assert form.special_requirement_input.toPlainText() == "横图"

    # AI 修改：文档即完整状态，没出现的字段被清空
    window._on_ai_modified({"风格模式": "水彩", "特别要求": "横图"})
    assert form.field_widgets["风格模式"].get_value() == "水彩"
    assert form.field_widgets["地点设定"].get_value() == ""
    assert form.special_requirement_enabled.isChecked()
    assert not form.negative_prompt_enabled.isChecked()


def test_config_dialog_save_refreshes_the_image_panel(studio, make_window):
    from nano_banana.desktop.dialogs import config_dialog

    window = make_window(studio)
    assert _provider_ids(window) == [None]

    def fake_exec(dialog):
        dialog.image_key_input.setText("new-key")
        dialog._save_config()

    with patch.object(config_dialog.UnifiedAIConfigDialog, "exec", fake_exec):
        window._open_ai_config_dialog("image", "doubao_image")

    assert _provider_ids(window) == ["doubao_image"]
    assert window.image_panel.generate_button.isEnabled()


def test_window_state_is_not_written_to_the_real_user_settings(studio, make_window, qapp):
    from nano_banana.desktop.window_utils import app_settings

    window = make_window(studio)
    window.close()
    qapp.processEvents()

    settings = app_settings()
    assert settings.format() == settings.Format.IniFormat
    assert settings.fileName().endswith("ui_state.ini")
    assert settings.value("main_window/geometry") is not None
