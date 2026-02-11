"""可编辑的下拉输入组件"""
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QMenu,
    QInputDialog,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction


class NoScrollComboBox(QComboBox):
    """禁用滚轮的下拉框"""
    def wheelEvent(self, event):
        event.ignore()  # 忽略滚轮事件，防止误触


class ComboInput(QWidget):
    """带下拉选项的可编辑输入框，支持添加/删除选项"""

    value_changed = pyqtSignal(str)
    options_changed = pyqtSignal(str, list)  # field_name, new_options

    def __init__(
        self, field_name: str, options: list = None, parent=None, yaml_handler=None
    ):
        super().__init__(parent)
        self.field_name = field_name
        self.yaml_handler = yaml_handler
        self._options = options or []

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 可编辑的下拉框（禁用滚轮）
        self.combo = NoScrollComboBox()
        self.combo.setEditable(True)
        self.combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo.addItems(self._options)
        self.combo.setCurrentText("")
        self.combo.lineEdit().setPlaceholderText("选择或输入...")
        self.combo.setMinimumWidth(300)
        layout.addWidget(self.combo, 1)

        # 管理按钮
        self.manage_btn = QPushButton("⋯")  # 使用更明显的省略号字符
        self.manage_btn.setFixedSize(36, 38)  # 与输入框高度对齐 (20 + 8*2 padding + 2 border)
        self.manage_btn.setToolTip("管理选项")
        self.manage_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manage_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.manage_btn)

    def _connect_signals(self):
        self.combo.currentTextChanged.connect(self._on_text_changed)
        self.manage_btn.clicked.connect(self._show_manage_menu)

    def _on_text_changed(self, text):
        self.value_changed.emit(text)

    def _show_manage_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px 8px 12px;
                color: #2B2B2B;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #F7F7F7;
                color: #2B2B2B;
            }
        """
        )

        # 添加当前输入到选项
        add_current = QAction("保存当前输入为选项", self)
        add_current.triggered.connect(self._add_current_to_options)
        menu.addAction(add_current)

        # 添加新选项
        add_new = QAction("添加新选项...", self)
        add_new.triggered.connect(self._add_new_option)
        menu.addAction(add_new)

        menu.addSeparator()

        # 删除选项子菜单
        if self._options:
            delete_menu = menu.addMenu("删除选项")
            delete_menu.setStyleSheet(menu.styleSheet())
            for opt in self._options:
                display_text = opt[:40] + "..." if len(opt) > 40 else opt
                action = QAction(display_text, self)
                action.setData(opt)
                action.triggered.connect(lambda checked, o=opt: self._delete_option(o))
                delete_menu.addAction(action)

        menu.exec(self.manage_btn.mapToGlobal(self.manage_btn.rect().bottomLeft()))

    def _add_current_to_options(self):
        current_text = self.combo.currentText().strip()
        if not current_text:
            QMessageBox.warning(self, "提示", "请先输入内容")
            return

        if current_text in self._options:
            QMessageBox.information(self, "提示", "该选项已存在")
            return

        self._options.append(current_text)
        self.combo.addItem(current_text)

        if self.yaml_handler:
            self.yaml_handler.add_option(self.field_name, current_text)

        self.options_changed.emit(self.field_name, self._options)

    def _add_new_option(self):
        text, ok = QInputDialog.getText(self, "添加选项", "请输入新选项:")
        if ok and text.strip():
            text = text.strip()
            if text in self._options:
                QMessageBox.information(self, "提示", "该选项已存在")
                return

            self._options.append(text)
            self.combo.addItem(text)

            if self.yaml_handler:
                self.yaml_handler.add_option(self.field_name, text)

            self.options_changed.emit(self.field_name, self._options)

    def _delete_option(self, option: str):
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选项:\n{option[:60]}...?" if len(option) > 60 else f"确定要删除选项:\n{option}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._options.remove(option)
            idx = self.combo.findText(option)
            if idx >= 0:
                self.combo.removeItem(idx)

            if self.yaml_handler:
                self.yaml_handler.remove_option(self.field_name, option)

            self.options_changed.emit(self.field_name, self._options)

    def get_value(self) -> str:
        return self.combo.currentText().strip()

    def set_value(self, value: str):
        self.combo.setCurrentText(value)

    def clear(self):
        self.combo.setCurrentText("")

