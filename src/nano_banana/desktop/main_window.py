"""主窗口：只负责摆放面板和把它们接起来。

表单 → PromptFormPanel；生图 → ImagePanel；业务全部走注入的 Studio。
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction, QCursor, QDesktopServices, QFont, QIcon, QKeySequence, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from nano_banana.core import Studio
from nano_banana.desktop.panels.form_panel import PromptFormPanel
from nano_banana.desktop.panels.image_panel import ImagePanel
from nano_banana.desktop.preview import ClickableLabel
from nano_banana.desktop.resources import logo_path
from nano_banana.desktop.styles import LIGHT_THEME, MENU_STYLE
from nano_banana.desktop.window_utils import (
    app_settings,
    extract_image_paths,
    fit_window_to_screen,
    save_clipboard_image,
)

GITHUB_URL = "https://github.com/lissettecarlr/nano-banana-prompt-studio"


class MainWindow(QMainWindow):
    def __init__(self, studio: Studio):
        super().__init__()
        self.studio = studio
        self.current_preset_name: str | None = None
        self.json_preview_visible = False

        self._setup_window()
        self._setup_ui()
        self._restore_ui_state()
        self._load_presets_to_selector()
        self._update_preview()
        self.setAcceptDrops(True)

    # ================= 窗口 =================

    def _setup_window(self):
        self.setWindowTitle("Nano Banana 生图工具")
        # 尺寸按屏幕可用区域钳制，小分辨率/高DPI缩放下不会超出屏幕
        fit_window_to_screen(self, 1400, 900, min_width=1200, min_height=800)
        geometry = app_settings().value("main_window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        self.setStyleSheet(LIGHT_THEME)
        if logo_path().exists():
            self.setWindowIcon(QIcon(str(logo_path())))

    def _restore_ui_state(self):
        """恢复分割条布局和预览列可见性。"""
        settings = app_settings()
        splitter_state = settings.value("main_window/splitter")
        if splitter_state is None:
            return
        self._set_preview_visible(settings.value("main_window/json_visible", False, bool))
        self.main_splitter.restoreState(splitter_state)

    def closeEvent(self, event):
        settings = app_settings()
        settings.setValue("main_window/geometry", self.saveGeometry())
        settings.setValue("main_window/splitter", self.main_splitter.saveState())
        settings.setValue("main_window/json_visible", self.json_preview_visible)
        super().closeEvent(event)

    # ---------- 拖拽 / 粘贴参考图 ----------

    def dragEnterEvent(self, event):
        if extract_image_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        paths = extract_image_paths(event.mimeData())
        if paths:
            self.image_panel.add_reference_paths(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def keyPressEvent(self, event):
        # 文本框会自行消费 Ctrl+V，只有焦点不在输入控件时才会到这里
        if event.matches(QKeySequence.StandardKey.Paste):
            path = save_clipboard_image()
            if path:
                self.image_panel.add_reference_paths([path])
                return
        super().keyPressEvent(event)

    # ================= 界面 =================

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        main_layout.addWidget(self._create_header())
        main_layout.addWidget(self._create_preset_bar())

        self.form_panel = PromptFormPanel(self.studio)
        self.form_panel.changed.connect(self._update_preview)
        self.form_panel.message.connect(self._show_toast)

        self.json_preview_area = self._create_preview_area()

        self.image_panel = ImagePanel(self.studio, self.form_panel.document)
        self.image_panel.config_requested.connect(
            lambda provider: self._open_ai_config_dialog("image", provider)
        )

        # 三列：表单 | 提示词预览（可折叠） | 生图
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(8)
        # 禁止把面板拖成 0 宽导致内容"消失"
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(self.form_panel)
        self.main_splitter.addWidget(self.json_preview_area)
        self.main_splitter.addWidget(self.image_panel)
        for index in range(3):
            self.main_splitter.setStretchFactor(index, 1)
        self.main_splitter.setSizes([600, 0, 600])
        self.json_preview_area.setVisible(False)
        main_layout.addWidget(self.main_splitter, 1)

        main_layout.addWidget(self._create_button_bar())

    def _create_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 10)

        def clickable(text: str = "") -> ClickableLabel:
            label = ClickableLabel(text)
            label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            label.setToolTip("点击访问 GitHub 仓库")
            label.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL)))
            return label

        logo_label = clickable()
        if logo_path().exists():
            logo_label.setPixmap(
                QPixmap(str(logo_path())).scaled(
                    48,
                    48,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        logo_label.setFixedSize(52, 52)
        layout.addWidget(logo_label)

        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(12, 0, 0, 0)
        title_layout.setSpacing(4)
        title = clickable("Nano Banana 图片生成工具")
        title.setObjectName("appTitle")
        title_layout.addWidget(title)
        subtitle = clickable("一站式AI图片生成工具，通过结构化提示词控制图片生成质量")
        subtitle.setObjectName("appSubtitle")
        title_layout.addWidget(subtitle)
        layout.addWidget(title_container)
        layout.addStretch()
        return header

    def _create_preset_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("presetBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        label = QLabel("预设:")
        label.setObjectName("presetLabel")
        layout.addWidget(label)

        self.preset_selector = QComboBox()
        self.preset_selector.setObjectName("presetSelector")
        self.preset_selector.setMinimumWidth(250)
        self.preset_selector.setPlaceholderText("选择预设...")
        self.preset_selector.currentIndexChanged.connect(self._on_preset_selected)
        layout.addWidget(self.preset_selector)

        def button(text: str, object_name: str, slot, tooltip: str = "") -> QPushButton:
            btn = QPushButton(text)
            btn.setObjectName(object_name)
            if tooltip:
                btn.setToolTip(tooltip)
            btn.clicked.connect(slot)
            layout.addWidget(btn)
            return btn

        button("刷新", "secondaryButton", self._load_presets_to_selector, "刷新预设列表")
        button(
            "AI提示词生成",
            "aiGenerateButton",
            self._show_ai_generate_dialog,
            "使用AI根据描述自动生成提示词",
        )
        button(
            "AI提示词修改",
            "aiGenerateButton",
            self._show_ai_modify_dialog,
            "使用AI根据描述修改当前提示词",
        )
        layout.addStretch()
        self.manage_presets_btn = button("管理预设", "secondaryButton", self._show_preset_menu)
        button("AI配置", "secondaryButton", lambda: self._open_ai_config_dialog("chat"))
        return bar

    def _create_preview_area(self) -> QWidget:
        """最终提示词预览（可折叠）。内容由 Studio.render 生成，和实际发给生图模型的一致。"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("提示词预览")
        title.setObjectName("previewTitle")
        layout.addWidget(title)

        self.json_preview = QTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setPlaceholderText("填写表单后，这里将实时显示最终发送给生图模型的提示词...")
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.json_preview.setFont(font)
        layout.addWidget(self.json_preview)
        return container

    def _create_button_bar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(12)

        clear_btn = QPushButton("清空表单")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.clicked.connect(self._clear_form)
        layout.addWidget(clear_btn)

        copy_btn = QPushButton("复制表单")
        copy_btn.setObjectName("secondaryButton")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        layout.addWidget(copy_btn)

        self.json_toggle_btn = QPushButton("JSON浏览")
        self.json_toggle_btn.setObjectName("secondaryButton")
        self.json_toggle_btn.clicked.connect(self._toggle_preview)
        layout.addWidget(self.json_toggle_btn)

        layout.addStretch()

        # 生图动作按钮归 ImagePanel 所有，这里只负责摆放
        layout.addWidget(self.image_panel.copy_button)
        layout.addWidget(self.image_panel.save_button)
        layout.addWidget(self.image_panel.generate_button)
        return bar

    # ================= 提示词预览 =================

    def _update_preview(self):
        self.json_preview.setPlainText(self.studio.render(self.form_panel.document()).text)

    def _set_preview_visible(self, visible: bool):
        self.json_preview_visible = visible
        self.json_preview_area.setVisible(visible)
        self.json_toggle_btn.setText("JSON隐藏" if visible else "JSON浏览")

    def _toggle_preview(self):
        self._set_preview_visible(not self.json_preview_visible)
        # 按当前分割器实际宽度按比例分配，而不是写死像素值
        total = max(self.main_splitter.width(), 1)
        if self.json_preview_visible:
            left = int(total * 0.38)
            middle = int(total * 0.24)
            self.main_splitter.setSizes([left, middle, total - left - middle])
        else:
            half = total // 2
            self.main_splitter.setSizes([half, 0, total - half])

    def _copy_to_clipboard(self):
        """复制最终提示词。"""
        self._update_preview()
        QApplication.clipboard().setText(self.json_preview.toPlainText())
        self._show_toast("已复制到剪贴板")

    # ================= 预设 =================

    def _load_presets_to_selector(self, select: str | None = None):
        self.preset_selector.blockSignals(True)
        self.preset_selector.clear()
        self.preset_selector.addItem("")  # 空选项
        presets = self.studio.presets.list_all()
        for preset in presets:
            self.preset_selector.addItem(preset["name"], preset["name"])
        if isinstance(select, str) and select:
            self.preset_selector.setCurrentIndex(max(self.preset_selector.findData(select), 0))
        self.preset_selector.blockSignals(False)
        self._show_toast(f"已加载 {len(presets)} 个预设")

    def _on_preset_selected(self, index: int):
        name = self.preset_selector.itemData(index)
        if name:
            self._load_preset(name)

    def _load_preset(self, name: str):
        data = self.studio.presets.load(name)
        if not data:
            self._show_toast(f"加载预设失败: {name}")
            return
        self.form_panel.apply_document(data)
        self.current_preset_name = name
        self._show_toast(f"已加载预设: {name}")

    def _save_as_preset(self):
        name, ok = QInputDialog.getText(
            self, "保存预设", "请输入预设名称:", text=self.current_preset_name or ""
        )
        if not ok or not name.strip():
            return
        saved_name = self.studio.presets.save(name.strip(), self.form_panel.document())
        if not saved_name:
            self._show_toast("保存预设失败")
            return
        self.current_preset_name = saved_name
        self._load_presets_to_selector(select=saved_name)
        self._show_toast(f"预设已保存: {saved_name}")

    def _show_preset_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)

        save_action = QAction("保存为预设", self)
        save_action.triggered.connect(self._save_as_preset)
        menu.addAction(save_action)
        menu.addSeparator()

        presets = self.studio.presets.list_all()
        if presets:
            delete_menu = menu.addMenu("删除预设")
            delete_menu.setStyleSheet(MENU_STYLE)
            for preset in presets:
                action = QAction(preset["name"], self)
                action.triggered.connect(
                    lambda _checked=False, n=preset["name"]: self._delete_preset(n)
                )
                delete_menu.addAction(action)
        else:
            no_preset = QAction("(暂无预设)", self)
            no_preset.setEnabled(False)
            menu.addAction(no_preset)

        anchor = self.manage_presets_btn
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def _delete_preset(self, name: str):
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除预设「{name}」吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self.studio.presets.delete(name):
            self._load_presets_to_selector()
            if self.current_preset_name == name:
                self.current_preset_name = None
            self._show_toast(f"已删除预设: {name}")
        else:
            self._show_toast("删除预设失败")

    # ================= AI 对话框 =================

    def _show_ai_generate_dialog(self):
        from nano_banana.desktop.dialogs.generate_dialog import AIGenerateDialog

        dialog = AIGenerateDialog(self.studio, self)
        dialog.generated.connect(self._on_ai_generated)
        dialog.exec()

    def _show_ai_modify_dialog(self):
        from nano_banana.desktop.dialogs.modify_dialog import AIModifyDialog

        dialog = AIModifyDialog(self.studio, self.form_panel.document(), self)
        dialog.modified.connect(self._on_ai_modified)
        dialog.exec()

    def _open_ai_config_dialog(self, tab: str = "chat", image_provider: str | None = None):
        from nano_banana.desktop.dialogs.config_dialog import UnifiedAIConfigDialog

        dialog = UnifiedAIConfigDialog(
            self.studio, self, initial_tab=tab, image_provider=image_provider
        )
        dialog.config_saved.connect(self.image_panel.reload_providers)
        dialog.exec()

    def _on_ai_generated(self, document: dict):
        # AI 只产出模型可见的部分；特别要求、线稿等保持用户当前设置
        self.form_panel.apply_document(document)
        self.current_preset_name = None
        self._show_toast("已应用AI生成的提示词")

    def _on_ai_modified(self, document: dict):
        # document 是「原文档 + 勾选的差异」，即完整的新状态
        self.form_panel.apply_document(document, replace=True)
        self.current_preset_name = None
        self._show_toast("已应用AI修改的提示词")

    # ================= 其他 =================

    def _clear_form(self):
        reply = QMessageBox.question(
            self,
            "确认清空",
            "确定要清空所有表单内容吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.form_panel.reset()
        self.image_panel.reset()
        self.current_preset_name = None
        self.preset_selector.setCurrentIndex(0)
        self._show_toast("表单已清空")

    def _show_toast(self, message: str):
        self.statusBar().showMessage(message, 3000)
