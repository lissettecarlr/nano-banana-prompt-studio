"""字段分组组件"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFrame,
)
from PyQt6.QtCore import Qt


class FieldGroup(QFrame):
    """带标题的字段分组容器"""

    def __init__(self, title: str, parent=None, color_class: str = None):
        super().__init__(parent)
        self.title = title
        self.color_class = color_class
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("fieldGroup")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(12)

        # 标题
        title_label = QLabel(self.title)
        # 如果指定了颜色类，使用特定的objectName
        if self.color_class:
            title_label.setObjectName(f"groupTitle_{self.color_class}")
        else:
            title_label.setObjectName("groupTitle")
        layout.addWidget(title_label)

        # 内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        layout.addWidget(self.content_widget)

    def add_field(self, label_text: str, widget: QWidget):
        """添加一个字段"""
        field_container = QWidget()
        field_layout = QVBoxLayout(field_container)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(4)

        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        field_layout.addWidget(label)
        field_layout.addWidget(widget)

        self.content_layout.addWidget(field_container)

    def add_widget(self, widget: QWidget):
        """直接添加一个widget"""
        self.content_layout.addWidget(widget)

