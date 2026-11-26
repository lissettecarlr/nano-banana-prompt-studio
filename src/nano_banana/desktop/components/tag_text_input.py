"""可管理标签的自由文本输入组件。"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class TagTextInput(QWidget):
    """独立管理标签，并通过点击标签填充自由文本。"""

    value_changed = pyqtSignal(str)
    options_changed = pyqtSignal(str, list)

    def __init__(
        self, field_name: str, options: list | None = None, parent=None, option_store=None
    ):
        super().__init__(parent)
        self.field_name = field_name
        self.option_store = option_store
        self._options = list(options or [])
        self._tag_widgets = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        add_row = QHBoxLayout()
        add_row.setContentsMargins(0, 0, 0, 0)
        add_row.setSpacing(6)
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("输入新标签...")
        self.tag_input.returnPressed.connect(self._add_new_tag)
        add_row.addWidget(self.tag_input, 1)

        # 固定宽度，高度跟随行高，字体/DPI变化时自动与输入框对齐
        self.add_tag_btn = QPushButton("+")
        self.add_tag_btn.setFixedWidth(38)
        self.add_tag_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.add_tag_btn.setToolTip("添加标签")
        self.add_tag_btn.setAccessibleName("添加标签")
        self.add_tag_btn.setObjectName("secondaryButton")
        self.add_tag_btn.clicked.connect(self._add_new_tag)
        add_row.addWidget(self.add_tag_btn)
        layout.addLayout(add_row)

        self.tags_widget = QWidget()
        self.tags_layout = QHBoxLayout(self.tags_widget)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(6)
        self.tags_layout.addStretch()

        tags_scroll = QScrollArea()
        tags_scroll.setWidgetResizable(True)
        tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tags_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tags_scroll.setFrameShape(QFrame.Shape.NoFrame)
        # 高度按字体计算，系统字号/DPI变大时标签不被裁剪
        tags_scroll.setFixedHeight(self.fontMetrics().height() + 24)
        tags_scroll.setWidget(self.tags_widget)
        layout.addWidget(tags_scroll)

        for option in self._options:
            self._add_tag_widget(option)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("请输入反向提示词...")
        self.text_edit.setMinimumHeight(72)
        self.text_edit.setMaximumHeight(110)
        self.text_edit.textChanged.connect(
            lambda: self.value_changed.emit(self.get_value())
        )
        layout.addWidget(self.text_edit)

    def _add_tag_widget(self, text: str):
        tag_widget = QWidget()
        tag_layout = QHBoxLayout(tag_widget)
        tag_layout.setContentsMargins(0, 0, 0, 0)
        tag_layout.setSpacing(0)

        apply_button = QPushButton(text)
        apply_button.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_button.setStyleSheet("""
            QPushButton {
                padding: 5px 8px;
                border: 1px solid #D0D0D0;
                border-right: none;
                border-radius: 4px 0 0 4px;
                background-color: #F7F7F7;
                color: #4A4A4A;
            }
            QPushButton:hover {
                border-color: #B08D57;
                background-color: #F8F2E8;
                color: #8A6B42;
            }
        """)
        apply_button.clicked.connect(
            lambda _checked=False, value=text: self._apply_tag(value)
        )
        tag_layout.addWidget(apply_button)

        delete_button = QPushButton("×")
        delete_button.setFixedWidth(26)
        delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_button.setToolTip(f"删除标签：{text}")
        delete_button.setAccessibleName(f"删除标签：{text}")
        delete_button.setStyleSheet("""
            QPushButton {
                padding: 5px 4px;
                border: 1px solid #D0D0D0;
                border-radius: 0 4px 4px 0;
                background-color: #F7F7F7;
                color: #777777;
            }
            QPushButton:hover {
                border-color: #DC3545;
                background-color: #FFF1F0;
                color: #DC3545;
            }
        """)
        delete_button.clicked.connect(
            lambda _checked=False, value=text: self._delete_tag(value)
        )
        tag_layout.addWidget(delete_button)

        self.tags_layout.insertWidget(self.tags_layout.count() - 1, tag_widget)
        self._tag_widgets[text] = tag_widget

    def _apply_tag(self, tag: str):
        current = self.get_value()
        if not current:
            self.set_value(tag)
            return

        if tag not in current:
            separator = "" if current.endswith((",", "，", " ", "\n")) else ", "
            self.set_value(f"{current}{separator}{tag}")

    def _add_new_tag(self):
        value = self.tag_input.text().strip()
        if not value:
            QMessageBox.warning(self, "提示", "请输入标签内容")
            return
        if value in self._options:
            QMessageBox.information(self, "提示", "该标签已存在")
            return

        self._options.append(value)
        self._add_tag_widget(value)
        self.tag_input.clear()
        if self.option_store:
            self.option_store.add_option(self.field_name, value)
        self.options_changed.emit(self.field_name, list(self._options))

    def _delete_tag(self, value: str):
        if value not in self._options:
            return

        self._options.remove(value)
        tag_widget = self._tag_widgets.pop(value)
        self.tags_layout.removeWidget(tag_widget)
        tag_widget.deleteLater()
        if self.option_store:
            self.option_store.remove_option(self.field_name, value)
        self.options_changed.emit(self.field_name, list(self._options))

    def get_value(self) -> str:
        return self.text_edit.toPlainText().strip()

    def set_value(self, value):
        self.text_edit.setPlainText(str(value) if value else "")

    def clear(self):
        self.text_edit.clear()