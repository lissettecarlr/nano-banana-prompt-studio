"""画幅设置组件 - 预设快捷选择 + 可微调字段"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFrame,
    QButtonGroup,
)
from PyQt6.QtCore import pyqtSignal, Qt


# 画幅预设配置
ASPECT_PRESETS = {
    "手机壁纸": {
        "比例": "9:16",
        "分辨率": "2048×3640 (2K)",
        "用途": "手机壁纸",
    },
    "PC壁纸": {
        "比例": "16:9",
        "分辨率": "3840×2160 (4K)",
        "用途": "电脑桌面壁纸",
    },
    "平板壁纸": {
        "比例": "4:3",
        "分辨率": "2732×2048 (iPad)",
        "用途": "平板壁纸",
    },
    "社交头像": {
        "比例": "1:1",
        "分辨率": "1024×1024",
        "用途": "社交头像",
    }
}

# 下拉选项
RATIO_OPTIONS = ["9:16", "16:9", "4:3", "3:4", "1:1", "2:3", "3:2", "21:9"]

RESOLUTION_OPTIONS = [
    "1024×1024",
    "1920×1080 (1080P)",
    "2048×3640 (2K竖)",
    "3640×2048 (2K横)",
    "2560×1440 (2K)",
    "3840×2160 (4K)",
    "2732×2048 (iPad)",
    "2400×3600",
    "3600×2400",
    "3440×1440",
    "4096×4096",
]

USAGE_OPTIONS = [
    "手机壁纸",
    "电脑桌面壁纸",
    "平板壁纸",
    "社交头像",
    "超宽屏壁纸",
]


class NoScrollComboBox(QComboBox):
    """禁用滚轮的下拉框"""
    def wheelEvent(self, event):
        event.ignore()


class AspectRatioSelector(QWidget):
    """画幅设置组件"""

    value_changed = pyqtSignal()  # 任意值改变时触发

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_preset = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ===== 预设按钮区域 =====
        preset_container = QWidget()
        preset_layout = QHBoxLayout(preset_container)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(8)

        self.preset_buttons = {}
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        for i, (name, config) in enumerate(ASPECT_PRESETS.items()):
            icon = config.get('icon', '')
            btn_text = f"{icon} {name}" if icon else name
            btn = QPushButton(btn_text)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("presetName", name)
            btn.setObjectName("aspectPresetBtn")
            btn.setMinimumHeight(36)
            self.button_group.addButton(btn, i)
            self.preset_buttons[name] = btn
            preset_layout.addWidget(btn)

        preset_layout.addStretch()
        layout.addWidget(preset_container)

        # ===== 详细参数区域 =====
        params_container = QFrame()
        params_container.setObjectName("aspectParamsContainer")
        params_layout = QHBoxLayout(params_container)
        params_layout.setContentsMargins(12, 12, 12, 12)
        params_layout.setSpacing(16)

        # 比例
        ratio_group = self._create_field_group("比例", RATIO_OPTIONS)
        self.ratio_combo = ratio_group["combo"]
        params_layout.addWidget(ratio_group["widget"])

        # 分辨率
        resolution_group = self._create_field_group("分辨率", RESOLUTION_OPTIONS)
        self.resolution_combo = resolution_group["combo"]
        params_layout.addWidget(resolution_group["widget"])

        # 用途
        usage_group = self._create_field_group("用途", USAGE_OPTIONS)
        self.usage_combo = usage_group["combo"]
        params_layout.addWidget(usage_group["widget"])

        params_layout.addStretch()
        layout.addWidget(params_container)

    def _create_field_group(self, label_text: str, options: list) -> dict:
        """创建一个字段组"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label = QLabel(label_text)
        label.setObjectName("aspectFieldLabel")
        layout.addWidget(label)

        combo = NoScrollComboBox()
        combo.setEditable(True)
        combo.addItems(options)
        combo.setCurrentText("")
        combo.lineEdit().setPlaceholderText("选择或输入...")
        combo.setMinimumWidth(180)
        combo.setObjectName("aspectFieldCombo")
        layout.addWidget(combo)

        return {"widget": container, "combo": combo}

    def _connect_signals(self):
        self.button_group.buttonClicked.connect(self._on_preset_clicked)
        self.ratio_combo.currentTextChanged.connect(self._on_field_changed)
        self.resolution_combo.currentTextChanged.connect(self._on_field_changed)
        self.usage_combo.currentTextChanged.connect(self._on_field_changed)

    def _on_preset_clicked(self, button: QPushButton):
        """预设按钮点击"""
        preset_name = button.property("presetName")
        if preset_name and preset_name in ASPECT_PRESETS:
            config = ASPECT_PRESETS[preset_name]
            self._current_preset = preset_name

            # 填充字段（阻止信号避免重复触发）
            self.ratio_combo.blockSignals(True)
            self.resolution_combo.blockSignals(True)
            self.usage_combo.blockSignals(True)

            self.ratio_combo.setCurrentText(config["比例"])
            self.resolution_combo.setCurrentText(config["分辨率"])
            self.usage_combo.setCurrentText(config["用途"])

            self.ratio_combo.blockSignals(False)
            self.resolution_combo.blockSignals(False)
            self.usage_combo.blockSignals(False)

            self.value_changed.emit()

    def _on_field_changed(self):
        """字段手动修改时，取消预设选中状态"""
        # 检查当前值是否匹配任何预设
        current_values = {
            "比例": self.ratio_combo.currentText(),
            "分辨率": self.resolution_combo.currentText(),
            "用途": self.usage_combo.currentText(),
        }

        matched_preset = None
        for name, config in ASPECT_PRESETS.items():
            if (config["比例"] == current_values["比例"] and
                config["分辨率"] == current_values["分辨率"] and
                config["用途"] == current_values["用途"]):
                matched_preset = name
                break

        # 更新按钮状态
        if matched_preset:
            self.preset_buttons[matched_preset].setChecked(True)
            self._current_preset = matched_preset
        else:
            # 取消所有选中
            checked_btn = self.button_group.checkedButton()
            if checked_btn:
                self.button_group.setExclusive(False)
                checked_btn.setChecked(False)
                self.button_group.setExclusive(True)
            self._current_preset = None

        self.value_changed.emit()

    def get_values(self) -> dict:
        """获取当前值"""
        return {
            "比例": self.ratio_combo.currentText().strip(),
            "分辨率": self.resolution_combo.currentText().strip(),
            "用途": self.usage_combo.currentText().strip(),
        }

    def set_values(self, ratio: str = "", resolution: str = "", usage: str = ""):
        """设置值"""
        self.ratio_combo.blockSignals(True)
        self.resolution_combo.blockSignals(True)
        self.usage_combo.blockSignals(True)

        self.ratio_combo.setCurrentText(ratio)
        self.resolution_combo.setCurrentText(resolution)
        self.usage_combo.setCurrentText(usage)

        self.ratio_combo.blockSignals(False)
        self.resolution_combo.blockSignals(False)
        self.usage_combo.blockSignals(False)

        # 检查是否匹配预设并更新按钮
        self._on_field_changed()

    def clear(self):
        """清空"""
        checked_btn = self.button_group.checkedButton()
        if checked_btn:
            self.button_group.setExclusive(False)
            checked_btn.setChecked(False)
            self.button_group.setExclusive(True)

        self.ratio_combo.setCurrentText("")
        self.resolution_combo.setCurrentText("")
        self.usage_combo.setCurrentText("")
        self._current_preset = None

