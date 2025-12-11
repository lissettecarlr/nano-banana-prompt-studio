"""主应用程序窗口"""
import json
import os
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QSplitter,
    QPushButton,
    QTextEdit,
    QLabel,
    QFrame,
    QMessageBox,
    QComboBox,
    QInputDialog,
    QMenu,
    QCheckBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction, QPixmap, QIcon

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

from components.combo_input import ComboInput
from components.field_group import FieldGroup
from components.aspect_ratio_selector import AspectRatioSelector
from components.multi_select import MultiSelectInput
from utils.yaml_handler import YamlHandler
from utils.preset_manager import PresetManager
from utils.resource_path import get_images_dir
from components.ai_dialog import AIGenerateDialog
from components.ai_image_dialog import AIImageGenerateDialog
from styles import LIGHT_THEME


class PromptGeneratorApp(QMainWindow):
    """提示词生成器主窗口"""

    def __init__(self):
        super().__init__()
        self.yaml_handler = YamlHandler()
        self.preset_manager = PresetManager()
        self.field_widgets = {}  # 存储所有字段的widget引用
        self.current_preset_name = None

        self._setup_window()
        self._setup_ui()
        self._load_presets_to_selector()

    def _setup_window(self):
        self.setWindowTitle("Nano Banana 提示词生成器")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        self.setStyleSheet(LIGHT_THEME)
        
        # 设置窗口图标
        icon_path = get_images_dir() / "logo.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 标题区域（含预设选择器）
        header = self._create_header()
        main_layout.addWidget(header)

        # 预设工具栏
        preset_bar = self._create_preset_bar()
        main_layout.addWidget(preset_bar)

        # 主内容区域 - 使用分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)

        # 左侧：表单区域
        form_area = self._create_form_area()
        splitter.addWidget(form_area)

        # 右侧：预览区域
        preview_area = self._create_preview_area()
        splitter.addWidget(preview_area)

        # 设置分割比例
        splitter.setSizes([700, 500])
        main_layout.addWidget(splitter, 1)

        # 底部按钮区域
        button_bar = self._create_button_bar()
        main_layout.addWidget(button_bar)

    def _create_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 10)

        # Logo
        logo_label = QLabel()
        logo_path = get_images_dir() / "logo.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            # 缩放logo到合适大小，保持高质量
            scaled_pixmap = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        logo_label.setFixedSize(52, 52)
        layout.addWidget(logo_label)

        # 标题
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(12, 0, 0, 0)
        title_layout.setSpacing(4)

        title = QLabel("Nano Banana 提示词生成器")
        title.setObjectName("appTitle")
        title_layout.addWidget(title)

        subtitle = QLabel("AI绘画提示词可视化编辑工具")
        subtitle.setObjectName("appSubtitle")
        title_layout.addWidget(subtitle)

        layout.addWidget(title_container)
        layout.addStretch()

        return header

    def _create_preset_bar(self) -> QWidget:
        """创建预设工具栏"""
        bar = QFrame()
        bar.setObjectName("presetBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # 预设标签
        label = QLabel("预设:")
        label.setObjectName("presetLabel")
        layout.addWidget(label)

        # 预设选择器
        self.preset_selector = QComboBox()
        self.preset_selector.setObjectName("presetSelector")
        self.preset_selector.setMinimumWidth(250)
        self.preset_selector.setPlaceholderText("选择预设...")
        self.preset_selector.currentTextChanged.connect(self._on_preset_selected)
        layout.addWidget(self.preset_selector)

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setToolTip("刷新预设列表")
        refresh_btn.clicked.connect(self._load_presets_to_selector)
        layout.addWidget(refresh_btn)

        # AI提示词生成按钮
        ai_btn = QPushButton("AI提示词生成")
        ai_btn.setObjectName("aiGenerateButton")
        ai_btn.setToolTip("使用AI根据描述自动生成提示词")
        ai_btn.clicked.connect(self._show_ai_generate_dialog)
        layout.addWidget(ai_btn)

        # 添加AI修改按钮
        ai_modify_btn = QPushButton("AI提示词修改")
        ai_modify_btn.setObjectName("aiGenerateButton")  # 使用相同的对象名以保持样式一致
        ai_modify_btn.setToolTip("使用AI根据描述修改当前提示词")
        ai_modify_btn.clicked.connect(self._show_ai_modify_dialog)
        layout.addWidget(ai_modify_btn)

        # AI 生图按钮
        ai_image_btn = QPushButton("Banana图片生成")
        ai_image_btn.setObjectName("aiGenerateButton")
        ai_image_btn.setToolTip("使用 Gemini 根据提示词生成图片")
        ai_image_btn.clicked.connect(self._show_ai_image_dialog)
        layout.addWidget(ai_image_btn)

        layout.addStretch()

        # 保存预设按钮
        save_btn = QPushButton("保存为预设")
        save_btn.clicked.connect(self._save_as_preset)
        layout.addWidget(save_btn)

        # 管理预设按钮
        manage_btn = QPushButton("管理预设")
        manage_btn.clicked.connect(self._show_preset_menu)
        layout.addWidget(manage_btn)

        return bar

    def _create_form_area(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 16, 0)

        # ===== 画幅设置 =====
        aspect_container = QWidget()
        aspect_layout = QVBoxLayout(aspect_container)
        aspect_layout.setContentsMargins(0, 0, 0, 0)
        aspect_layout.setSpacing(0)

        # 启用开关
        self.aspect_enabled = QCheckBox("启用画幅设置")
        self.aspect_enabled.setObjectName("aspectToggle")
        self.aspect_enabled.setChecked(False)  # 默认不启用
        self.aspect_enabled.stateChanged.connect(self._on_aspect_toggle_changed)
        aspect_layout.addWidget(self.aspect_enabled)

        # 画幅设置分组
        self.aspect_group = FieldGroup("画幅设置")
        self.aspect_selector = AspectRatioSelector()
        self.aspect_selector.value_changed.connect(self._on_field_changed)
        self.aspect_group.add_widget(self.aspect_selector)
        self.aspect_group.setVisible(False)  # 默认隐藏
        aspect_layout.addWidget(self.aspect_group)

        layout.addWidget(aspect_container)

        # ===== 基础设置 =====
        basic_group = FieldGroup("基础设置")
        self._add_field(basic_group, "风格模式", "风格模式")
        self._add_field(basic_group, "画面气质", "画面气质")
        layout.addWidget(basic_group)

        # ===== 相机设置 =====
        camera_group = FieldGroup("相机设置")
        self._add_field(camera_group, "机位角度", "机位角度")
        self._add_field(camera_group, "构图", "构图")
        self._add_field(camera_group, "镜头特性", "镜头特性")
        self._add_field(camera_group, "传感器画质", "传感器画质")
        layout.addWidget(camera_group)

        # ===== 场景 - 环境 =====
        env_group = FieldGroup("场景 · 环境")
        self._add_field(env_group, "地点设定", "地点设定")
        self._add_field(env_group, "光线", "光线")
        self._add_field(env_group, "天气氛围", "天气氛围")
        layout.addWidget(env_group)

        # ===== 场景 - 主体描述 =====
        subject_group = FieldGroup("场景 · 主体")
        self._add_field(subject_group, "整体描述", "整体描述")
        layout.addWidget(subject_group)

        # ===== 主体 - 外形特征 =====
        appearance_group = FieldGroup("主体 · 外形特征")
        self._add_field(appearance_group, "身材", "身材")
        self._add_field(appearance_group, "面部", "面部")
        self._add_field(appearance_group, "头发", "头发")
        self._add_field(appearance_group, "眼睛", "眼睛")
        layout.addWidget(appearance_group)

        # ===== 主体 - 表情与动作 =====
        action_group = FieldGroup("主体 · 表情与动作")
        self._add_field(action_group, "情绪", "情绪")
        self._add_field(action_group, "动作", "动作")
        layout.addWidget(action_group)

        # ===== 主体 - 服装 =====
        clothing_group = FieldGroup("主体 · 服装")
        self._add_field(clothing_group, "穿着", "穿着")
        self._add_field(clothing_group, "服装细节", "服装细节")
        self._add_field(clothing_group, "配饰", "配饰")
        layout.addWidget(clothing_group)

        # ===== 背景 =====
        bg_group = FieldGroup("背景")
        self._add_field(bg_group, "背景描述", "背景描述")
        self._add_field(bg_group, "景深", "景深")
        layout.addWidget(bg_group)

        # ===== 审美控制 =====
        aesthetic_group = FieldGroup("审美控制")
        self._add_field(aesthetic_group, "呈现意图", "呈现意图")
        self._add_field(aesthetic_group, "材质真实度", "材质真实度")
        self._add_field(aesthetic_group, "整体色调", "整体色调")
        self._add_field(aesthetic_group, "对比度", "对比度")
        self._add_field(aesthetic_group, "特殊效果", "特殊效果")
        layout.addWidget(aesthetic_group)

        # ===== 反向提示词 =====
        negative_container = QWidget()
        negative_layout = QVBoxLayout(negative_container)
        negative_layout.setContentsMargins(0, 0, 0, 0)
        negative_layout.setSpacing(0)

        # 启用开关
        self.negative_prompt_enabled = QCheckBox("启用反向提示词")
        self.negative_prompt_enabled.setObjectName("negativePromptToggle")
        self.negative_prompt_enabled.setChecked(False)  # 默认不启用
        self.negative_prompt_enabled.stateChanged.connect(self._on_negative_toggle_changed)
        negative_layout.addWidget(self.negative_prompt_enabled)

        # 反向提示词分组
        self.negative_group = FieldGroup("反向提示词")
        self._add_multi_select_field(self.negative_group, "禁止元素", "禁止元素")
        self._add_multi_select_field(self.negative_group, "禁止风格", "禁止风格")
        self.negative_group.setVisible(False)  # 默认隐藏
        negative_layout.addWidget(self.negative_group)

        layout.addWidget(negative_container)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _add_field(self, group: FieldGroup, label: str, field_name: str):
        """添加一个字段到分组"""
        options = self.yaml_handler.get_field_options(field_name)
        widget = ComboInput(
            field_name=field_name, options=options, yaml_handler=self.yaml_handler
        )
        widget.value_changed.connect(self._on_field_changed)
        group.add_field(label, widget)
        self.field_widgets[field_name] = widget

    def _add_multi_select_field(self, group: FieldGroup, label: str, field_name: str):
        """添加一个多选字段到分组"""
        options = self.yaml_handler.get_field_options(field_name)
        widget = MultiSelectInput(
            field_name=field_name, options=options, yaml_handler=self.yaml_handler
        )
        widget.value_changed.connect(self._on_field_changed)
        group.add_field(label, widget)
        self.field_widgets[field_name] = widget

    def _create_preview_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(12)

        # 预览标题
        title = QLabel("JSON 预览")
        title.setObjectName("previewTitle")
        layout.addWidget(title)

        # JSON文本框
        self.json_preview = QTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setPlaceholderText("填写表单后，这里将实时显示生成的JSON提示词...")
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

        # 清空按钮
        clear_btn = QPushButton("清空表单")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.clicked.connect(self._clear_form)
        layout.addWidget(clear_btn)

        layout.addStretch()

        # 复制按钮
        copy_btn = QPushButton("复制到剪贴板")
        copy_btn.setObjectName("primaryButton")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        layout.addWidget(copy_btn)

        return bar

    def _on_field_changed(self, value: str = None):
        """字段值改变时自动更新预览"""
        self._generate_json()

    def _on_aspect_toggle_changed(self, state: int):
        """画幅设置开关切换"""
        enabled = state == 2  # Qt.CheckState.Checked = 2
        self.aspect_group.setVisible(enabled)
        self._generate_json()

    def _on_negative_toggle_changed(self, state: int):
        """反向提示词开关切换"""
        enabled = state == 2  # Qt.CheckState.Checked = 2
        self.negative_group.setVisible(enabled)
        self._generate_json()

    def _generate_json(self):
        """生成JSON提示词"""
        data = self._collect_form_data()
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        self.json_preview.setText(json_str)

    def _collect_form_data(self) -> dict:
        """收集表单数据并组织成目标格式"""

        def get_value(field_name: str) -> str:
            widget = self.field_widgets.get(field_name)
            return widget.get_value() if widget else ""

        # 收集材质真实度列表
        material_value = get_value("材质真实度")
        materials = [m.strip() for m in material_value.split(",") if m.strip()] if material_value else []

        # 收集禁止元素列表（多选）
        forbidden_elements = self.field_widgets.get("禁止元素").get_value() if "禁止元素" in self.field_widgets else []

        # 收集禁止风格列表（多选）
        forbidden_styles = self.field_widgets.get("禁止风格").get_value() if "禁止风格" in self.field_widgets else []

        data = {
            "风格模式": get_value("风格模式"),
            "画面气质": get_value("画面气质"),
            "相机": {
                "机位角度": get_value("机位角度"),
                "构图": get_value("构图"),
                "镜头特性": get_value("镜头特性"),
                "传感器画质": get_value("传感器画质"),
            },
            "场景": {
                "环境": {
                    "地点设定": get_value("地点设定"),
                    "光线": get_value("光线"),
                    "天气氛围": get_value("天气氛围"),
                },
                "主体": {
                    "整体描述": get_value("整体描述"),
                    "外形特征": {
                        "身材": get_value("身材"),
                        "面部": get_value("面部"),
                        "头发": get_value("头发"),
                        "眼睛": get_value("眼睛"),
                    },
                    "表情与动作": {
                        "情绪": get_value("情绪"),
                        "动作": get_value("动作"),
                    },
                    "服装": {
                        "穿着": get_value("穿着"),
                        "细节": get_value("服装细节"),
                    },
                    "配饰": get_value("配饰"),
                },
                "背景": {
                    "描述": get_value("背景描述"),
                    "景深": get_value("景深"),
                },
            },
            "审美控制": {
                "呈现意图": get_value("呈现意图"),
                "材质真实度": materials if materials else [get_value("材质真实度")],
                "色彩风格": {
                    "整体色调": get_value("整体色调"),
                    "对比度": get_value("对比度"),
                    "特殊效果": get_value("特殊效果"),
                },
            },
        }

        # 仅当启用画幅设置时才添加
        if self.aspect_enabled.isChecked():
            aspect_values = self.aspect_selector.get_values()
            data["画幅设置"] = {
                "比例": aspect_values["比例"],
                "推荐分辨率": aspect_values["分辨率"],
                "用途": aspect_values["用途"],
            }

        # 仅当启用反向提示词时才添加
        if self.negative_prompt_enabled.isChecked():
            data["反向提示词"] = {
                "禁止元素": forbidden_elements,
                "禁止风格": forbidden_styles,
            }

        return data

    # ========== 预设相关方法 ==========

    def _load_presets_to_selector(self):
        """加载预设到选择器"""
        self.preset_selector.blockSignals(True)
        self.preset_selector.clear()
        self.preset_selector.addItem("")  # 空选项

        presets = self.preset_manager.get_all_presets()
        for preset in presets:
            self.preset_selector.addItem(preset['name'], preset['name'])

        self.preset_selector.blockSignals(False)
        self._show_toast(f"已加载 {len(presets)} 个预设")

    def _on_preset_selected(self, text: str):
        """选择预设时加载"""
        if not text or text == "":
            return

        # 获取实际的预设名称
        idx = self.preset_selector.currentIndex()
        preset_name = self.preset_selector.itemData(idx)

        if preset_name:
            self._load_preset(preset_name)

    def _load_preset(self, name: str):
        """加载预设到表单"""
        data = self.preset_manager.load_preset(name)
        if not data:
            self._show_toast(f"加载预设失败: {name}")
            return

        # 解析嵌套数据并填充表单
        self._fill_form_from_data(data)
        self.current_preset_name = name
        self._show_toast(f"已加载预设: {name}")

    def _fill_form_from_data(self, data: dict):
        """从数据填充表单"""
        _MISSING = object()

        def _get(d, *keys):
            """按路径取值，缺失则返回 _MISSING 用于“不覆盖”"""
            cur = d
            for k in keys:
                if not isinstance(cur, dict) or k not in cur:
                    return _MISSING
                cur = cur[k]
            return cur

        def _get_list_as_str(d, *keys):
            val = _get(d, *keys)
            if val is _MISSING:
                return _MISSING
            return self._list_to_str(val)

        # 字段映射: 仅当预设里存在该键时才覆盖
        field_mapping = {
            "风格模式": lambda d: _get(d, "风格模式"),
            "画面气质": lambda d: _get(d, "画面气质"),
            "机位角度": lambda d: _get(d, "相机", "机位角度"),
            "构图": lambda d: _get(d, "相机", "构图"),
            "镜头特性": lambda d: _get(d, "相机", "镜头特性"),
            "传感器画质": lambda d: _get(d, "相机", "传感器画质"),
            "地点设定": lambda d: _get(d, "场景", "环境", "地点设定"),
            "光线": lambda d: _get(d, "场景", "环境", "光线"),
            "天气氛围": lambda d: _get(d, "场景", "环境", "天气氛围"),
            "整体描述": lambda d: _get(d, "场景", "主体", "整体描述"),
            "身材": lambda d: _get(d, "场景", "主体", "外形特征", "身材"),
            "面部": lambda d: _get(d, "场景", "主体", "外形特征", "面部"),
            "头发": lambda d: _get(d, "场景", "主体", "外形特征", "头发"),
            "眼睛": lambda d: _get(d, "场景", "主体", "外形特征", "眼睛"),
            "情绪": lambda d: _get(d, "场景", "主体", "表情与动作", "情绪"),
            "动作": lambda d: _get(d, "场景", "主体", "表情与动作", "动作"),
            "穿着": lambda d: _get(d, "场景", "主体", "服装", "穿着"),
            "服装细节": lambda d: _get(d, "场景", "主体", "服装", "细节"),
            "配饰": lambda d: _get(d, "场景", "主体", "配饰"),
            "背景描述": lambda d: _get(d, "场景", "背景", "描述"),
            "景深": lambda d: _get(d, "场景", "背景", "景深"),
            "呈现意图": lambda d: _get(d, "审美控制", "呈现意图"),
            "材质真实度": lambda d: _get_list_as_str(d, "审美控制", "材质真实度"),
            "整体色调": lambda d: _get(d, "审美控制", "色彩风格", "整体色调"),
            "对比度": lambda d: _get(d, "审美控制", "色彩风格", "对比度"),
            "特殊效果": lambda d: _get(d, "审美控制", "色彩风格", "特殊效果"),
        }

        for field_name, getter in field_mapping.items():
            if field_name in self.field_widgets:
                value = getter(data)
                if value is not _MISSING:
                    self.field_widgets[field_name].set_value("" if value is None else value)

        # 多选字段需要传入列表；缺失键不覆盖
        multi_select_fields = {
            "禁止元素": lambda d: _get(d, "反向提示词", "禁止元素"),
            "禁止风格": lambda d: _get(d, "反向提示词", "禁止风格"),
        }
        for field_name, getter in multi_select_fields.items():
            if field_name in self.field_widgets:
                value = getter(data)
                if value is not _MISSING:
                    self.field_widgets[field_name].set_value(value if value else [])

        # 处理画幅设置开关状态；仅当预设提供该块时覆盖
        aspect_data = data.get("画幅设置", _MISSING)
        if aspect_data is not _MISSING and isinstance(aspect_data, dict):
            has_aspect = bool(
                aspect_data.get("比例") or aspect_data.get("推荐分辨率") or aspect_data.get("用途")
            )
            self.aspect_enabled.setChecked(has_aspect)
            self.aspect_group.setVisible(has_aspect)
            if has_aspect:
                self.aspect_selector.set_values(
                    ratio=aspect_data.get("比例", ""),
                    resolution=aspect_data.get("推荐分辨率", ""),
                    usage=aspect_data.get("用途", ""),
                )

        # 处理反向提示词开关状态；仅当预设提供该块时覆盖
        negative_data = data.get("反向提示词", _MISSING)
        if negative_data is not _MISSING and isinstance(negative_data, dict):
            has_negative = bool(
                negative_data.get("禁止元素") or negative_data.get("禁止风格")
            )
            self.negative_prompt_enabled.setChecked(has_negative)
            self.negative_group.setVisible(has_negative)

        self._generate_json()

    def _list_to_str(self, lst) -> str:
        """列表转字符串"""
        if isinstance(lst, list):
            return ", ".join(str(item) for item in lst if item)
        return str(lst) if lst else ""

    def _save_as_preset(self):
        """保存当前配置为预设"""
        default_name = self.current_preset_name or ""
        name, ok = QInputDialog.getText(
            self,
            "保存预设",
            "请输入预设名称:",
            text=default_name
        )

        if ok and name.strip():
            name = name.strip()
            data = self._collect_form_data()

            if self.preset_manager.save_preset(name, data):
                self.current_preset_name = name
                self._load_presets_to_selector()
                # 选中刚保存的预设
                for i in range(self.preset_selector.count()):
                    if self.preset_selector.itemData(i) == name:
                        self.preset_selector.setCurrentIndex(i)
                        break
                self._show_toast(f"预设已保存: {name}")
            else:
                self._show_toast("保存预设失败")

    def _show_preset_menu(self):
        """显示预设管理菜单"""
        menu = QMenu(self)
        # 使用与全局主题一致的样式
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
            QMenu::separator {
                height: 1px;
                background-color: #EAEAEA;
                margin: 4px 8px;
            }
        """)

        # 刷新列表
        refresh_action = QAction("刷新预设列表", self)
        refresh_action.triggered.connect(self._load_presets_to_selector)
        menu.addAction(refresh_action)

        menu.addSeparator()

        # 删除预设子菜单
        presets = self.preset_manager.get_all_presets()
        if presets:
            delete_menu = menu.addMenu("删除预设")
            delete_menu.setStyleSheet(menu.styleSheet())
            for preset in presets:
                action = QAction(preset['name'], self)
                action.triggered.connect(
                    lambda checked, n=preset['name']: self._delete_preset(n)
                )
                delete_menu.addAction(action)
        else:
            no_preset = QAction("(暂无预设)", self)
            no_preset.setEnabled(False)
            menu.addAction(no_preset)

        menu.exec(self.sender().mapToGlobal(self.sender().rect().bottomLeft()))

    def _delete_preset(self, name: str):
        """删除预设"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除预设「{name}」吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.preset_manager.delete_preset(name):
                self._load_presets_to_selector()
                if self.current_preset_name == name:
                    self.current_preset_name = None
                self._show_toast(f"已删除预设: {name}")
            else:
                self._show_toast("删除预设失败")

    # ========== AI 生成相关方法 ==========

    def _show_ai_generate_dialog(self):
        """显示AI生成对话框"""
        from components.ai_dialog import AIGenerateDialog
        dialog = AIGenerateDialog(self)
        dialog.generated.connect(self._on_ai_generated)
        dialog.exec()

    def _show_ai_modify_dialog(self):
        """显示AI修改对话框"""
        from components.ai_dialog import AIModifyDialog
        # 获取当前表单数据
        current_data = self._collect_form_data()
        dialog = AIModifyDialog(current_data, self)
        dialog.modified.connect(self._on_ai_modified)
        dialog.exec()

    def _show_ai_image_dialog(self):
        """显示AI 生图对话框"""
        prompt_data = self._collect_form_data()
        prompt_text = json.dumps(prompt_data, ensure_ascii=False, indent=2)
        dialog = AIImageGenerateDialog(prompt_text, self)
        dialog.exec()

    def _on_ai_generated(self, data: dict):
        """AI生成完成后应用到表单"""
        self._fill_form_from_data(data)
        self.current_preset_name = None
        self._show_toast("已应用AI生成的提示词")

    def _on_ai_modified(self, data: dict):
        """AI修改完成后应用到表单"""
        self._fill_form_from_data(data)
        self.current_preset_name = None
        self._show_toast("已应用AI修改的提示词")

    # ========== 其他方法 ==========

    def _copy_to_clipboard(self):
        """复制JSON到剪贴板"""
        json_text = self.json_preview.toPlainText()
        if not json_text:
            self._generate_json()
            json_text = self.json_preview.toPlainText()

        if CLIPBOARD_AVAILABLE:
            try:
                pyperclip.copy(json_text)
                self._show_toast("已复制到剪贴板")
            except Exception:
                from PyQt6.QtWidgets import QApplication
                QApplication.clipboard().setText(json_text)
                self._show_toast("已复制到剪贴板")
        else:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(json_text)
            self._show_toast("已复制到剪贴板")

    def _clear_form(self):
        """清空表单"""
        reply = QMessageBox.question(
            self,
            "确认清空",
            "确定要清空所有表单内容吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for widget in self.field_widgets.values():
                widget.clear()
            self.aspect_selector.clear()
            self.json_preview.clear()
            self.current_preset_name = None
            self.preset_selector.setCurrentIndex(0)
            # 重置画幅设置开关
            self.aspect_enabled.setChecked(False)
            self.aspect_group.setVisible(False)
            # 重置反向提示词开关
            self.negative_prompt_enabled.setChecked(False)
            self.negative_group.setVisible(False)
            self._show_toast("表单已清空")

    def _show_toast(self, message: str):
        """显示简短提示"""
        self.statusBar().showMessage(message, 3000)
