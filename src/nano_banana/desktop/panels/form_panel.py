"""提示词表单：schema 驱动的字段分组 + overlay（特别要求 / 线稿 / 反向提示词）。

对外只暴露「文档」：document() 读出、apply_document() 写入、reset() 清空。
最终提示词怎么拼由 Studio.render 决定，这里不关心。
"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from nano_banana.core import Studio
from nano_banana.core.prompt import (
    build_document,
    flatten,
    get_at_path,
    get_line_art,
    overlay_by_id,
    subset,
)
from nano_banana.desktop.components.combo_input import ComboInput
from nano_banana.desktop.components.field_group import FieldGroup
from nano_banana.desktop.components.tag_text_input import TagTextInput
from nano_banana.desktop.styles import MENU_STYLE, PLAIN_TEXT_EDIT_STYLE

_MISSING = object()


class PromptFormPanel(QScrollArea):
    changed = pyqtSignal()  # 文档内容变化
    message = pyqtSignal(str)  # 给状态栏的简短提示

    def __init__(self, studio: Studio, parent=None):
        super().__init__(parent)
        self.studio = studio
        self.schema = studio.schema
        self.field_widgets: dict[str, ComboInput] = {}  # widget_key -> 控件
        self.category_preset_selectors: dict[str, QComboBox] = {}
        self._negative_overlay = overlay_by_id("negativePrompt", self.schema)
        self._special_overlay = overlay_by_id("specialRequirement", self.schema)
        self._line_art_overlay = overlay_by_id("lineArt", self.schema)
        self._batch_depth = 0
        self._setup_ui()

    # ================= 文档读写 =================

    def document(self) -> dict[str, Any]:
        """当前表单 → 完整文档（含已启用的 overlay）。"""
        fields = {
            field.id: self.field_widgets[field.widget_key].get_value()
            for field in self.schema.iter_fields()
            if field.widget_key in self.field_widgets
        }
        special = self.special_requirement_input.toPlainText().strip()
        return build_document(
            fields,
            self.schema,
            negative_prompt=(
                self.negative_prompt_input.get_value()
                if self.negative_prompt_enabled.isChecked()
                else None
            ),
            special_requirement=(
                special if self.special_requirement_enabled.isChecked() and special else None
            ),
            line_art_prompt=(
                self.line_art_prompt_input.toPlainText().strip()
                if self.line_art_mode_enabled.isChecked()
                else None
            ),
        )

    def apply_document(self, data: dict[str, Any] | None, *, replace: bool = False) -> None:
        """把文档写进表单。

        replace=False：只覆盖文档里出现的部分（预设、分类预设、AI 生成）；
        replace=True：文档即完整状态，没出现的字段清空、overlay 关闭（AI 修改的结果）。
        """
        data = self.studio.migrate(data)
        with _Batch(self):
            flat = flatten(data, self.schema, include_missing=replace)
            for field in self.schema.iter_fields():
                widget = self.field_widgets.get(field.widget_key)
                if widget is not None and field.id in flat:
                    widget.set_value(flat[field.id])

            negative = get_at_path(data, self._negative_overlay.path, _MISSING)
            if negative is not _MISSING or replace:
                text = negative if isinstance(negative, str) else ""
                self.negative_prompt_input.set_value(text)
                self.negative_prompt_enabled.setChecked(bool(text))

            special = get_at_path(data, self._special_overlay.path, _MISSING)
            if special is not _MISSING or replace:
                text = special.strip() if isinstance(special, str) else ""
                self.special_requirement_input.setPlainText(text)
                self.special_requirement_enabled.setChecked(bool(text))

            line_art = get_at_path(data, self._line_art_overlay.path, _MISSING)
            if line_art is not _MISSING or replace:
                enabled, prompt = get_line_art(data, self.schema)
                self.line_art_mode_enabled.setChecked(enabled)
                if enabled and prompt:
                    self.line_art_prompt_input.setPlainText(prompt)

    def reset(self) -> None:
        """清空表单，overlay 回到默认状态。"""
        with _Batch(self):
            self.line_art_mode_enabled.setChecked(False)
            for widget in self.field_widgets.values():
                widget.clear()
            self.negative_prompt_enabled.setChecked(True)
            self.negative_prompt_input.set_value(self._negative_overlay.default)
            self.special_requirement_enabled.setChecked(False)
            self.special_requirement_input.clear()

    def is_line_art_mode(self) -> bool:
        return self.line_art_mode_enabled.isChecked()

    # ================= 界面 =================

    def _setup_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 16, 0)

        for category in self.schema.categories:
            group = FieldGroup(category.label, color_class=category.color_class)
            for field in category.fields:
                self._add_field(group, field.label, field.widget_key)
            self._add_category_preset_controls(group, category.id, category.label)
            layout.addWidget(group)

        layout.addWidget(self._create_special_requirement_section())
        layout.addWidget(self._create_line_art_section())
        layout.addWidget(self._create_negative_prompt_section())
        layout.addStretch()
        self.setWidget(container)

    def _add_field(self, group: FieldGroup, label: str, field_name: str):
        widget = ComboInput(
            field_name=field_name,
            options=self.studio.options.get_field_options(field_name),
            option_store=self.studio.options,
        )
        widget.value_changed.connect(self._emit_changed)
        group.add_field(label, widget)
        self.field_widgets[field_name] = widget

    def _create_special_requirement_section(self) -> QWidget:
        container, layout = _section()

        self.special_requirement_enabled = QCheckBox("启用特别要求")
        self.special_requirement_enabled.setObjectName("specialRequirementToggle")
        self.special_requirement_enabled.setChecked(False)
        self.special_requirement_enabled.toggled.connect(self._on_special_requirement_toggled)
        layout.addWidget(self.special_requirement_enabled)

        self.special_requirement_group = FieldGroup("特别要求", color_class="special")
        self.special_requirement_input = QTextEdit()
        self.special_requirement_input.setPlaceholderText(
            "请输入额外的特别要求，这些内容不会纳入AI提示词生成和修改，只在生成图片时补充..."
        )
        self.special_requirement_input.setMaximumHeight(100)
        self.special_requirement_input.setStyleSheet(PLAIN_TEXT_EDIT_STYLE)
        self.special_requirement_input.textChanged.connect(self._emit_changed)
        self.special_requirement_group.add_widget(self.special_requirement_input)
        self.special_requirement_group.setVisible(False)
        layout.addWidget(self.special_requirement_group)
        return container

    def _create_line_art_section(self) -> QWidget:
        container, layout = _section()

        self.line_art_mode_enabled = QCheckBox("启用角色线稿生成")
        self.line_art_mode_enabled.setObjectName("lineArtModeToggle")
        self.line_art_mode_enabled.setChecked(False)
        self.line_art_mode_enabled.setToolTip(
            "启用后将使用专用线稿提示词，并禁用其他表单设置（除额外要求外）"
        )
        self.line_art_mode_enabled.toggled.connect(self._on_line_art_mode_toggled)
        layout.addWidget(self.line_art_mode_enabled)

        self.line_art_hint = QLabel("启用后，除特别要求外，其他提示词被禁用。")
        self.line_art_hint.setStyleSheet(
            "color: #999999; font-size: 12px; margin-left: 24px; margin-bottom: 4px;"
        )
        layout.addWidget(self.line_art_hint)

        self.line_art_group = FieldGroup("线稿提示词", color_class="special")
        self.line_art_prompt_input = QTextEdit()
        self.line_art_prompt_input.setPlaceholderText("请输入角色线稿生成的提示词...")
        self.line_art_prompt_input.setMinimumHeight(120)
        self.line_art_prompt_input.setMaximumHeight(200)
        self.line_art_prompt_input.setStyleSheet(PLAIN_TEXT_EDIT_STYLE)
        self.line_art_prompt_input.textChanged.connect(self._emit_changed)
        self.line_art_group.add_widget(self.line_art_prompt_input)

        save_row = QWidget()
        save_layout = QHBoxLayout(save_row)
        save_layout.setContentsMargins(0, 8, 0, 0)
        save_layout.addStretch()
        self.save_line_art_prompt_btn = QPushButton("保存提示词")
        self.save_line_art_prompt_btn.setObjectName("secondaryButton")
        self.save_line_art_prompt_btn.clicked.connect(self._save_line_art_prompt)
        save_layout.addWidget(self.save_line_art_prompt_btn)
        self.line_art_group.add_widget(save_row)

        self.line_art_group.setVisible(False)
        layout.addWidget(self.line_art_group)
        return container

    def _create_negative_prompt_section(self) -> QWidget:
        container, layout = _section()

        self.negative_prompt_enabled = QCheckBox("启用反向提示词")
        self.negative_prompt_enabled.setObjectName("negativePromptToggle")
        self.negative_prompt_enabled.setChecked(True)
        self.negative_prompt_enabled.toggled.connect(self._on_negative_toggled)
        layout.addWidget(self.negative_prompt_enabled)

        self.negative_group = FieldGroup("反向提示词", color_class="negative")
        options_key = self._negative_overlay.options_key
        self.negative_prompt_input = TagTextInput(
            field_name=options_key,
            options=self.studio.options.get_field_options(options_key),
            option_store=self.studio.options,
        )
        self.negative_prompt_input.set_value(self._negative_overlay.default)
        self.negative_prompt_input.value_changed.connect(self._emit_changed)
        self.negative_group.add_field("提示词", self.negative_prompt_input)
        layout.addWidget(self.negative_group)
        return container

    # ================= 开关联动 =================

    def _emit_changed(self, *_args):
        if self._batch_depth == 0:
            self.changed.emit()

    def _on_negative_toggled(self, enabled: bool):
        self.negative_group.setVisible(enabled)
        self._emit_changed()

    def _on_special_requirement_toggled(self, enabled: bool):
        self.special_requirement_group.setVisible(enabled)
        self._emit_changed()

    def _on_line_art_mode_toggled(self, enabled: bool):
        """线稿模式：只用线稿提示词，其余字段置灰。"""
        with _Batch(self):
            self.line_art_group.setVisible(enabled)
            if enabled:
                self.line_art_prompt_input.setPlainText(self.studio.options.get_line_art_prompt())
                # 线稿模式下反向提示词不参与，顺手收起
                self.negative_prompt_enabled.setChecked(False)
            for widget in self.field_widgets.values():
                widget.setEnabled(not enabled)
            self.negative_prompt_enabled.setEnabled(not enabled)
            self.negative_group.setEnabled(not enabled)

    def _save_line_art_prompt(self):
        """把当前线稿提示词存为默认值。"""
        prompt = self.line_art_prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "提示", "提示词不能为空")
            return
        try:
            self.studio.options.save_line_art_prompt(prompt)
            self.message.emit("提示词保存成功")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "错误", f"保存失败: {exc}")

    # ================= 分类预设 =================

    def _add_category_preset_controls(self, group: FieldGroup, scope: str, label: str):
        """在分类标题中加入预设选择和管理控件。"""
        selector = QComboBox()
        selector.setObjectName("categoryPresetSelector")
        selector.setMinimumWidth(140)
        selector.setMaximumWidth(190)
        selector.setToolTip(f"应用{label}预设，仅覆盖本分类")
        selector.activated.connect(lambda index, s=scope: self._load_category_preset(s, index))
        self.category_preset_selectors[scope] = selector
        group.add_header_widget(selector)

        manage_btn = QPushButton("管理")
        manage_btn.setObjectName("secondaryButton")
        manage_btn.setToolTip(f"保存或删除{label}预设")
        manage_btn.clicked.connect(
            lambda _checked=False, s=scope, l=label, b=manage_btn: (
                self._show_category_preset_menu(s, l, b)
            )
        )
        group.add_header_widget(manage_btn)
        self._refresh_category_preset_selector(scope)

    def _refresh_category_preset_selector(self, scope: str, selected_name: str = ""):
        selector = self.category_preset_selectors.get(scope)
        if selector is None:
            return
        selector.blockSignals(True)
        selector.clear()
        selector.addItem("分类预设...", None)
        for preset in self.studio.presets.list_category(scope):
            selector.addItem(preset["name"], preset["name"])
        if selected_name:
            index = selector.findData(selected_name)
            if index >= 0:
                selector.setCurrentIndex(index)
        selector.blockSignals(False)

    def _load_category_preset(self, scope: str, index: int):
        selector = self.category_preset_selectors.get(scope)
        if selector is None or index <= 0:
            return
        name = selector.itemData(index)
        data = self.studio.presets.load_category(scope, name)
        if not data:
            self.message.emit(f"加载分类预设失败: {name}")
            return
        self.apply_document(data)
        self.message.emit(f"已应用分类预设: {name}")

    def _save_category_preset(self, scope: str, label: str):
        selector = self.category_preset_selectors.get(scope)
        default_name = selector.currentData() if selector else ""
        name, ok = QInputDialog.getText(
            self, f"保存{label}预设", "请输入预设名称:", text=default_name or ""
        )
        if not ok or not name.strip():
            return
        data = subset(self.document(), scope, self.schema)
        saved_name = self.studio.presets.save_category(scope, name.strip(), data)
        if saved_name:
            self._refresh_category_preset_selector(scope, saved_name)
            self.message.emit(f"{label}预设已保存: {saved_name}")
        else:
            self.message.emit(f"保存{label}预设失败")

    def _show_category_preset_menu(self, scope: str, label: str, anchor: QWidget):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        save_action = QAction("保存当前分类", self)
        save_action.triggered.connect(
            lambda _checked=False: self._save_category_preset(scope, label)
        )
        menu.addAction(save_action)

        delete_menu = menu.addMenu("删除分类预设")
        delete_menu.setStyleSheet(MENU_STYLE)
        presets = self.studio.presets.list_category(scope)
        for preset in presets:
            action = QAction(preset["name"], self)
            action.triggered.connect(
                lambda _checked=False, n=preset["name"]: (
                    self._delete_category_preset(scope, label, n)
                )
            )
            delete_menu.addAction(action)
        if not presets:
            empty_action = QAction("(暂无预设)", self)
            empty_action.setEnabled(False)
            delete_menu.addAction(empty_action)
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def _delete_category_preset(self, scope: str, label: str, name: str):
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除{label}预设「{name}」吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self.studio.presets.delete_category(scope, name):
            self._refresh_category_preset_selector(scope)
            self.message.emit(f"已删除分类预设: {name}")
        else:
            self.message.emit(f"删除分类预设失败: {name}")


class _Batch:
    """批量改控件期间只在最后发一次 changed。"""

    def __init__(self, panel: PromptFormPanel):
        self.panel = panel

    def __enter__(self):
        self.panel._batch_depth += 1

    def __exit__(self, *_exc):
        self.panel._batch_depth -= 1
        if self.panel._batch_depth == 0:
            self.panel.changed.emit()


def _section() -> tuple[QWidget, QVBoxLayout]:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    return container, layout
