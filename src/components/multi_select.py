"""多选组件 - 支持勾选多个选项"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QPushButton,
    QFrame,
    QInputDialog,
    QMessageBox,
    QMenu,
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction


class MultiSelectInput(QWidget):
    """多选输入组件，支持勾选多个选项"""

    value_changed = pyqtSignal(list)  # 选中的选项列表
    options_changed = pyqtSignal(str, list)  # field_name, new_options

    def __init__(
        self, field_name: str, options: list = None, parent=None, yaml_handler=None
    ):
        super().__init__(parent)
        self.field_name = field_name
        self.yaml_handler = yaml_handler
        self._options = options or []
        self._checkboxes = []

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 选项容器（直接显示，不滚动）
        self.options_container = QFrame()
        self.options_container.setStyleSheet("""
            QFrame {
                border: 1px solid #C8C8C8;
                border-radius: 6px;
                background-color: #FFFFFF;
            }
        """)
        self.options_layout = QVBoxLayout(self.options_container)
        self.options_layout.setContentsMargins(8, 8, 8, 8)
        self.options_layout.setSpacing(4)

        # 添加所有选项复选框
        for opt in self._options:
            self._add_checkbox(opt)

        layout.addWidget(self.options_container)

        # 底部工具栏
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 4, 0, 0)
        toolbar_layout.setSpacing(8)

        # 全选/取消全选
        select_all_btn = QPushButton("全选")
        select_all_btn.setFixedHeight(28)
        select_all_btn.clicked.connect(self._select_all)
        toolbar_layout.addWidget(select_all_btn)

        clear_btn = QPushButton("清除")
        clear_btn.setFixedHeight(28)
        clear_btn.clicked.connect(self._clear_selection)
        toolbar_layout.addWidget(clear_btn)

        toolbar_layout.addStretch()

        # 管理按钮
        manage_btn = QPushButton("管理选项")
        manage_btn.setFixedHeight(28)
        manage_btn.clicked.connect(self._show_manage_menu)
        toolbar_layout.addWidget(manage_btn)

        layout.addWidget(toolbar)

    def _add_checkbox(self, text: str):
        """添加一个复选框"""
        cb = QCheckBox(text)
        cb.stateChanged.connect(self._on_selection_changed)
        cb.setStyleSheet("""
            QCheckBox {
                padding: 4px 0;
            }
        """)
        self.options_layout.addWidget(cb)
        self._checkboxes.append(cb)

    def _on_selection_changed(self):
        """选择改变时触发"""
        self.value_changed.emit(self.get_value())

    def _select_all(self):
        """全选"""
        for cb in self._checkboxes:
            cb.setChecked(True)

    def _clear_selection(self):
        """取消所有选择"""
        for cb in self._checkboxes:
            cb.setChecked(False)

    def _show_manage_menu(self):
        """显示管理菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
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
        """)

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

        menu.exec(self.sender().mapToGlobal(self.sender().rect().bottomLeft()))

    def _add_new_option(self):
        """添加新选项"""
        text, ok = QInputDialog.getText(self, "添加选项", "请输入新选项:")
        if ok and text.strip():
            text = text.strip()
            if text in self._options:
                QMessageBox.information(self, "提示", "该选项已存在")
                return

            self._options.append(text)
            self._add_checkbox(text)

            if self.yaml_handler:
                self.yaml_handler.add_option(self.field_name, text)

            self.options_changed.emit(self.field_name, self._options)

    def _delete_option(self, option: str):
        """删除选项"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选项:\n{option[:60]}...?" if len(option) > 60 else f"确定要删除选项:\n{option}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 移除选项
            idx = self._options.index(option)
            self._options.remove(option)

            # 移除复选框
            cb = self._checkboxes.pop(idx)
            self.options_layout.removeWidget(cb)
            cb.deleteLater()

            if self.yaml_handler:
                self.yaml_handler.remove_option(self.field_name, option)

            self.options_changed.emit(self.field_name, self._options)

    def get_value(self) -> list:
        """获取选中的选项列表"""
        return [cb.text() for cb in self._checkboxes if cb.isChecked()]

    def set_value(self, values: list):
        """设置选中的选项"""
        if not values:
            values = []
        for cb in self._checkboxes:
            cb.setChecked(cb.text() in values)

    def clear(self):
        """清除所有选择"""
        for cb in self._checkboxes:
            cb.setChecked(False)

