"""生图面板：渠道/模型/参数、参考图、生成与预览。

渠道列表和参数控件完全由 Studio 给出的渠道声明驱动，新增渠道不需要改这里。
"""
from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QIcon, QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from nano_banana.core import ImageRequest, ProviderStatus, Studio
from nano_banana.desktop.preview import ImagePreviewDialog, ImagePreviewLabel
from nano_banana.desktop.styles import CARD_FRAME_STYLE
from nano_banana.desktop.window_utils import get_last_dir, remember_last_dir
from nano_banana.desktop.workers import ImageGenerationThread

MAX_IMAGE_HISTORY = 10
MAX_REFERENCE_IMAGES = 3
_CHINESE_NUMBERS = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]

_OPTION_COMBO_STYLE = """
    QComboBox {
        padding: 4px 8px;
        border: 1px solid #d9d9d9;
        border-radius: 4px;
        background-color: white;
        min-height: 24px;
        font-size: 12px;
    }
    QComboBox:hover {
        border-color: #40a9ff;
    }
"""

_REFERENCE_BUTTON_STYLE = """
    QPushButton {
        padding: 4px 12px;
        font-size: 12px;
        border: 1px solid #d9d9d9;
        border-radius: 4px;
        background-color: #ffffff;
        min-width: 50px;
    }
    QPushButton:hover {
        border-color: #ff4d4f;
        background-color: #fff1f0;
        color: #ff4d4f;
    }
"""


class ImagePanel(QWidget):
    config_requested = pyqtSignal(str)  # 需要打开某个渠道的连接配置

    def __init__(
        self,
        studio: Studio,
        document_provider: Callable[[], dict[str, Any]],
        parent=None,
    ):
        super().__init__(parent)
        self.studio = studio
        self._document_provider = document_provider

        self.selected_images: list[str] = []
        self.image_buttons: list[QPushButton] = []
        self.generated_image_bytes: bytes | None = None
        self.generated_pixmap: QPixmap | None = None
        self.image_history: list[tuple[bytes, QPixmap]] = []  # 最新的在末尾
        self.worker_thread: ImageGenerationThread | None = None
        self._stale_threads: list[ImageGenerationThread] = []
        self.option_widgets: dict[str, QComboBox] = {}
        self._statuses: dict[str, ProviderStatus] = {}
        self._active_provider = ""
        self._active_model = ""

        self._create_action_buttons()
        self._setup_ui()
        self.reload_providers()
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)

    # ================= 界面 =================

    def _create_action_buttons(self):
        """生成/保存/复制按钮归面板所有，由主窗口决定摆在哪。"""
        self.copy_button = QPushButton("复制图片")
        self.copy_button.setObjectName("secondaryButton")
        self.copy_button.setEnabled(False)
        self.copy_button.setToolTip("把当前生成的图片复制到剪贴板")
        self.copy_button.clicked.connect(self.copy_image_to_clipboard)

        self.save_button = QPushButton("保存图片")
        self.save_button.setObjectName("secondaryButton")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_image)

        self.generate_button = QPushButton("生成图片")
        self.generate_button.setObjectName("primaryButton")
        self.generate_button.clicked.connect(self._on_generate_clicked)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("图片生成")
        title.setObjectName("previewTitle")
        layout.addWidget(title)

        layout.addWidget(self._create_param_frame())
        layout.addWidget(self._create_preview_frame(), 1)

        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("color: #595959; font-size: 12px;")
        layout.addWidget(self.status_label)

    def _create_param_frame(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("paramFrame")
        frame.setStyleSheet(CARD_FRAME_STYLE % "paramFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        provider_row = QWidget()
        provider_layout = QHBoxLayout(provider_row)
        provider_layout.setContentsMargins(0, 0, 0, 0)
        provider_layout.setSpacing(8)
        provider_layout.addWidget(QLabel("渠道"))
        self.provider_combo = QComboBox()
        provider_layout.addWidget(self.provider_combo, 1)
        provider_layout.addWidget(QLabel("模型"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(False)
        provider_layout.addWidget(self.model_combo, 2)
        self.config_status = QLabel()
        provider_layout.addWidget(self.config_status)
        layout.addWidget(provider_row)

        options_container = QWidget()
        self.options_layout = QGridLayout(options_container)
        self.options_layout.setContentsMargins(0, 0, 0, 0)
        self.options_layout.setHorizontalSpacing(16)
        self.options_layout.setVerticalSpacing(8)
        self.options_layout.setColumnStretch(0, 1)
        self.options_layout.setColumnStretch(1, 1)
        layout.addWidget(options_container)

        reference_row = QWidget()
        reference_layout = QHBoxLayout(reference_row)
        reference_layout.setContentsMargins(0, 0, 0, 0)
        reference_layout.setSpacing(12)

        self.add_image_btn = QPushButton("添加参考图")
        self.add_image_btn.setObjectName("secondaryButton")
        self.add_image_btn.clicked.connect(self._choose_reference_images)
        reference_layout.addWidget(self.add_image_btn)

        buttons_container = QWidget()
        self.image_buttons_layout = QHBoxLayout(buttons_container)
        self.image_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.image_buttons_layout.setSpacing(8)
        self.image_buttons_layout.addStretch()
        hint = QLabel("点击删除参考图")
        hint.setStyleSheet("font-size: 11px; color: #8c8c8c;")
        self.image_buttons_layout.addWidget(hint)
        reference_layout.addWidget(buttons_container, 1)

        layout.addWidget(reference_row)
        return frame

    def _create_preview_frame(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("previewFrame")
        frame.setStyleSheet(CARD_FRAME_STYLE % "previewFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        preview_title = QLabel("生成预览")
        preview_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #262626;")
        layout.addWidget(preview_title)

        canvas = QFrame()
        canvas.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 #fafafa, stop:1 #f0f0f0); "
            "border: 2px dashed #d9d9d9; border-radius: 6px;"
        )
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(16, 16, 16, 16)

        self.preview_area = ImagePreviewLabel("图片生成后会显示在这里")
        self.preview_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_area.setMinimumHeight(120)
        self.preview_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_area.setStyleSheet("color: #bfbfbf; font-size: 13px; border: none;")
        # 禁用自动缩放，使用手动缩放以保持宽高比
        self.preview_area.setScaledContents(False)
        self.preview_area.clicked.connect(self._show_image_preview)
        canvas_layout.addWidget(self.preview_area)
        layout.addWidget(canvas, 1)

        # 历史缩略图条：新结果不覆盖旧图，点击可回看
        self.history_list = QListWidget()
        self.history_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.history_list.setFlow(QListWidget.Flow.LeftToRight)
        self.history_list.setWrapping(False)
        self.history_list.setFixedHeight(76)
        self.history_list.setIconSize(QSize(56, 56))
        self.history_list.setSpacing(6)
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.history_list.setToolTip("本次会话的生成历史，点击回看")
        self.history_list.itemClicked.connect(self._on_history_item_clicked)
        self.history_list.setVisible(False)
        layout.addWidget(self.history_list)
        return frame

    def _create_option_row(self, label_text: str, values: list[str], current: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        label = QLabel(label_text)
        # 最小宽度保证对齐，长文本/大字体时允许自动加宽而不是裁剪
        label.setMinimumWidth(72)
        label.setStyleSheet("font-size: 12px; color: #595959;")
        layout.addWidget(label)

        combo = QComboBox()
        combo.addItems(values)
        if current:
            combo.setCurrentText(current)
        combo.setStyleSheet(_OPTION_COMBO_STYLE)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(combo, 1)
        return container

    # ================= 渠道 / 模型 / 参数 =================

    def reload_providers(self) -> None:
        """重新读取渠道配置并刷新控件（启动时、配置对话框保存后调用）。"""
        self._remember_options()
        provider = self._refresh_provider_choices(self.provider_combo.currentData() or "")
        if not provider:
            self._render_options("", "")
            return
        self._populate_models(provider)
        self._activate(provider, self.model_combo.currentText().strip())

    def _refresh_provider_choices(self, preferred: str = "") -> str:
        """只列出已填写密钥的渠道，返回最终选中的渠道。"""
        self._statuses = {status.id: status for status in self.studio.provider_statuses()}
        available = [status for status in self._statuses.values() if status.has_api_key]
        available_ids = [status.id for status in available]
        selected = next(
            (
                provider
                for provider in (preferred, self.studio.settings.active_provider())
                if provider in available_ids
            ),
            available_ids[0] if available_ids else "",
        )

        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        for status in available:
            self.provider_combo.addItem(status.label, status.id)
        if selected:
            self.provider_combo.setCurrentIndex(self.provider_combo.findData(selected))
        else:
            self.provider_combo.addItem("请先配置图片渠道", None)
        self.provider_combo.setEnabled(bool(available))
        self.provider_combo.blockSignals(False)
        self.model_combo.setEnabled(bool(available))
        return selected

    def _populate_models(self, provider: str):
        status = self._statuses[provider]
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(list(status.models))
        self.model_combo.setCurrentText(status.configured_model)
        self.model_combo.blockSignals(False)

    def _activate(self, provider: str, model: str):
        """记住当前渠道/模型，并渲染它的参数控件。"""
        self.studio.settings.set_active_selection(provider, model)
        self._render_options(provider, model)

    def _remember_options(self):
        if self._active_provider and self.option_widgets:
            self.studio.settings.save_generation_options(
                self._active_provider, self._active_model, self.collect_options()
            )

    def _on_provider_changed(self, *_args):
        self._remember_options()
        provider = self.provider_combo.currentData()
        if not provider:
            return
        self._populate_models(provider)
        self._activate(provider, self.model_combo.currentText().strip())

    def _on_model_changed(self, *_args):
        provider = self.provider_combo.currentData()
        if not provider:
            return
        model = self.model_combo.currentText().strip()
        if provider == self._active_provider and model == self._active_model:
            return
        self._remember_options()
        self._activate(provider, model)

    def _render_options(self, provider: str, model: str):
        """按渠道声明渲染生图参数，并恢复上次用过的值。"""
        while self.options_layout.count():
            widget = self.options_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        self.option_widgets = {}
        self._active_provider = provider
        self._active_model = model

        if not provider:
            self.model_combo.blockSignals(True)
            self.model_combo.clear()
            self.model_combo.blockSignals(False)
            self._update_config_status()
            return

        saved = self.studio.settings.generation_options(provider, model)
        options = self.studio.capabilities(provider, model)["options"]
        for index, (key, option) in enumerate(options.items()):
            values = list(option.get("values") or [])
            value = saved.get(key, option.get("default"))
            if value not in values:
                value = option.get("default")
            row = self._create_option_row(option["label"], values, value)
            combo = row.findChild(QComboBox)
            combo.currentTextChanged.connect(lambda *_: self._remember_options())
            self.option_widgets[key] = combo
            self.options_layout.addWidget(row, index // 2, index % 2)
        self._update_config_status()

    def collect_options(self) -> dict[str, str]:
        return {key: combo.currentText() for key, combo in self.option_widgets.items()}

    def _is_generating(self) -> bool:
        return bool(self.worker_thread and self.worker_thread.isRunning())

    def _update_config_status(self):
        provider = self.provider_combo.currentData()
        configured = bool(provider and self.studio.settings.is_provider_configured(provider))
        if not provider:
            self.config_status.setText("请先在 AI 配置中填写密钥")
            self.config_status.setStyleSheet("color: #cf1322; font-size: 12px;")
        elif configured:
            self.config_status.clear()
        else:
            self.config_status.setText("未配置")
            self.config_status.setStyleSheet("color: #cf1322; font-size: 12px;")
        # 生成中按钮是「取消生成」，必须保持可点
        self.generate_button.setEnabled(self._is_generating() or configured)

    # ================= 参考图 =================

    def _choose_reference_images(self):
        if len(self.selected_images) >= MAX_REFERENCE_IMAGES:
            QMessageBox.information(self, "提示", f"最多只能选择 {MAX_REFERENCE_IMAGES} 张参考图")
            return
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择参考图片",
            get_last_dir("reference"),
            "图像文件 (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not files:
            return
        remember_last_dir(files[0], "reference")
        self.add_reference_paths(files)

    def add_reference_paths(self, paths: list[str]) -> None:
        """把图片路径加入参考图（拖拽/粘贴/文件对话框共用入口）。"""
        remaining = MAX_REFERENCE_IMAGES - len(self.selected_images)
        if remaining <= 0:
            self.set_status(f"最多只能选择 {MAX_REFERENCE_IMAGES} 张参考图", "#faad14")
            return
        added = 0
        for path in paths[:remaining]:
            if path in self.selected_images:
                continue
            self.selected_images.append(path)
            button = QPushButton()
            button.setToolTip(path)
            button.setStyleSheet(_REFERENCE_BUTTON_STYLE)
            button.clicked.connect(lambda _checked=False, b=button: self._remove_reference(b))
            self.image_buttons.append(button)
            # 插在提示文本之前
            self.image_buttons_layout.insertWidget(self.image_buttons_layout.count() - 1, button)
            added += 1
        self._relabel_reference_buttons()
        if added:
            self.set_status(f"已添加 {added} 张参考图", "#52c41a")

    def _remove_reference(self, button: QPushButton):
        if button not in self.image_buttons:
            return
        index = self.image_buttons.index(button)
        self.selected_images.pop(index)
        self.image_buttons.pop(index)
        button.setParent(None)
        button.deleteLater()
        self._relabel_reference_buttons()

    def _relabel_reference_buttons(self):
        for index, button in enumerate(self.image_buttons, start=1):
            number = _CHINESE_NUMBERS[index] if index < len(_CHINESE_NUMBERS) else str(index)
            button.setText(f"图{number}")

    def clear_references(self) -> None:
        for button in self.image_buttons:
            button.setParent(None)
            button.deleteLater()
        self.image_buttons.clear()
        self.selected_images.clear()

    # ================= 生成 =================

    def _on_generate_clicked(self):
        """生成中再次点击即取消。"""
        if self._is_generating():
            self.cancel_generation()
            return

        rendered = self.studio.render(self._document_provider())
        line_art = rendered.mode == "line_art"
        if rendered.is_empty:
            QMessageBox.warning(
                self,
                "提示",
                "线稿提示词不能为空" if line_art else "当前提示词为空，请先填写表单内容",
            )
            return

        provider = self.provider_combo.currentData()
        if not provider:
            QMessageBox.warning(self, "未配置图片渠道", "请先在 AI 配置中填写渠道密钥。")
            return
        if not self.studio.settings.is_provider_configured(provider):
            reply = QMessageBox.question(
                self,
                "未配置 API",
                "尚未配置当前图片生成 API，是否现在配置？",
                QMessageBox.StandardButton.Yes,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.config_requested.emit(provider)
            return

        request = ImageRequest(
            prompt=rendered.text,
            provider=provider,
            model=self.model_combo.currentText().strip(),
            images=tuple(self.selected_images),
            options=self.collect_options(),
        )

        self.generated_image_bytes = None
        self.generated_pixmap = None
        self.preview_area.setText("正在生成，请稍候...")
        self.preview_area.clearSourcePixmap()
        self._set_result_actions_enabled(False)
        self.set_status(
            "提交到图片生成服务（角色线稿模式）" if line_art else "提交到图片生成服务",
            "#1890ff",
        )

        thread = ImageGenerationThread(self.studio, request, self._statuses[provider].label)
        thread.progress.connect(lambda msg: self.set_status(f"⏳ {msg}", "#1890ff"))
        thread.image_ready.connect(self._on_image_ready)
        thread.error.connect(self._on_generation_error)
        thread.finished.connect(self._on_thread_finished)
        self.worker_thread = thread
        self._set_generating_state(True)
        thread.start()

    def cancel_generation(self) -> None:
        """取消当前生图：断开信号后放弃该线程，UI 立即恢复可用。"""
        thread = self.worker_thread
        if not thread:
            return
        thread.cancel()
        for signal in (thread.progress, thread.image_ready, thread.error, thread.finished):
            try:
                signal.disconnect()
            except TypeError:
                pass
        # 保住引用直到线程自然结束，避免 QThread 运行中被析构
        self._stale_threads = [t for t in self._stale_threads if t.isRunning()]
        self._stale_threads.append(thread)
        self.worker_thread = None
        self._set_generating_state(False)
        self.preview_area.setText("已取消生成")
        self.set_status("已取消", "#8c8c8c")

    def _on_thread_finished(self):
        self.worker_thread = None
        self._set_generating_state(False)

    def _on_image_ready(self, image_bytes: bytes):
        pixmap = QPixmap.fromImage(QImage.fromData(image_bytes))
        self._append_to_history(image_bytes, pixmap)
        self._show_result(image_bytes, pixmap)
        self.set_status("生成完成，点击图片可查看大图", "#52c41a")

    def _on_generation_error(self, message: str):
        self.set_status("生成失败", "#ff4d4f", message)
        self.preview_area.setText("生成失败，请调整参数后重试")
        self._enable_image_preview(False)
        self._set_generating_state(False)
        self._show_image_error(message)

    def _show_image_error(self, message: str):
        """弹窗展示生成错误，支持选中和一键复制。非阻塞，避免卡事件循环。"""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("图片生成失败")
        box.setText("图片生成失败，错误详情：")
        box.setInformativeText(message)
        box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        copy_btn = box.addButton("复制错误信息", QMessageBox.ButtonRole.ActionRole)
        box.addButton("关闭", QMessageBox.ButtonRole.RejectRole)

        def on_clicked(button):
            if button is copy_btn:
                QApplication.clipboard().setText(message)
                self.set_status("错误信息已复制到剪贴板", "#8c8c8c", message)

        box.buttonClicked.connect(on_clicked)
        box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        box.open()

    def _set_generating_state(self, generating: bool):
        self.provider_combo.setEnabled(not generating)
        self.model_combo.setEnabled(not generating)
        for combo in self.option_widgets.values():
            combo.setEnabled(not generating)
        self.add_image_btn.setEnabled(not generating)
        for button in self.image_buttons:
            button.setEnabled(not generating)
        if generating:
            # 生成中按钮变为取消入口，保持可点
            self.generate_button.setText("取消生成")
            self.generate_button.setEnabled(True)
        else:
            self.generate_button.setText("生成图片")
            self._update_config_status()

    # ================= 结果 / 预览 =================

    def _show_result(self, image_bytes: bytes, pixmap: QPixmap):
        self.generated_image_bytes = image_bytes
        self.generated_pixmap = pixmap
        self.refresh_preview()
        self._set_result_actions_enabled(True)

    def _set_result_actions_enabled(self, enabled: bool):
        self.save_button.setEnabled(enabled)
        self.copy_button.setEnabled(enabled)
        self._enable_image_preview(enabled)

    def _append_to_history(self, image_bytes: bytes, pixmap: QPixmap):
        self.image_history.append((image_bytes, pixmap))
        if len(self.image_history) > MAX_IMAGE_HISTORY:
            self.image_history.pop(0)
            self.history_list.takeItem(0)
        thumbnail = pixmap.scaled(
            56,
            56,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        item = QListWidgetItem(QIcon(thumbnail), "")
        item.setToolTip(f"第 {len(self.image_history)} 张，点击回看")
        self.history_list.addItem(item)
        self.history_list.setCurrentItem(item)
        self.history_list.scrollToItem(item)
        self.history_list.setVisible(True)

    def _on_history_item_clicked(self, item: QListWidgetItem):
        row = self.history_list.row(item)
        if not (0 <= row < len(self.image_history)):
            return
        self._show_result(*self.image_history[row])
        self.set_status(f"已切换到历史第 {row + 1} 张", "#595959")

    def copy_image_to_clipboard(self):
        if not self.generated_pixmap:
            return
        QApplication.clipboard().setPixmap(self.generated_pixmap)
        self.set_status("图片已复制到剪贴板", "#52c41a")

    def save_image(self):
        if not self.generated_image_bytes:
            return
        default_name = time.strftime("generated_%Y%m%d_%H%M%S.png")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存为",
            os.path.join(get_last_dir("save"), default_name),
            "PNG 图片 (*.png);;JPEG 图片 (*.jpg *.jpeg)",
        )
        if not file_path:
            return
        remember_last_dir(file_path, "save")

        suffix = os.path.splitext(file_path)[1].lower()
        format_name = "PNG" if suffix in ("", ".png") else "JPEG"
        if QImage.fromData(self.generated_image_bytes).save(file_path, format_name):
            self.set_status(f"图片已保存到 {file_path}", "#52c41a")
        else:
            QMessageBox.critical(self, "错误", "保存图片失败，请重试")

    def set_status(self, text: str, color: str = "#757575", tooltip: str = ""):
        self.status_label.setText(text)
        self.status_label.setToolTip(tooltip)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px;")

    def refresh_preview(self):
        if self.generated_pixmap:
            self.preview_area.setSourcePixmap(self.generated_pixmap)
        else:
            self.preview_area.clearSourcePixmap()
        self.preview_area.setScaledContents(False)

    def _enable_image_preview(self, enabled: bool):
        clickable = enabled and bool(self.generated_pixmap)
        self.preview_area.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor if clickable else Qt.CursorShape.ArrowCursor)
        )

    def _show_image_preview(self):
        if self.generated_pixmap:
            ImagePreviewDialog(self.generated_pixmap, self).exec()

    def reset(self) -> None:
        """清空参考图和当前结果（保留本次会话的历史缩略图）。"""
        self.clear_references()
        self.generated_image_bytes = None
        self.generated_pixmap = None
        self.preview_area.setText("图片生成后会显示在这里")
        self.preview_area.clearSourcePixmap()
        self._set_result_actions_enabled(False)
        self.set_status("准备就绪")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.generated_pixmap:
            self.refresh_preview()
