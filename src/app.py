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
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QSizePolicy,
    QDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QAction, QPixmap, QIcon, QImage, QCursor, QDesktopServices

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
from components.ai_image_dialog import GeminiImageThread
from components.gemini_client import ASPECT_RATIO_LIST, IMAGE_SIZE_LIST
from utils.ai_config import AIConfigManager
from styles import LIGHT_THEME


class ClickableLabel(QLabel):
    """可点击的标签，用于图片预览"""
    
    clicked = pyqtSignal()  # 需要导入 pyqtSignal
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ImagePreviewDialog(QDialog):
    """图片预览对话框 - 显示大图"""
    
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("图片预览")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
            }
            QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 图片显示区域
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False)
        layout.addWidget(self.image_label)
        
        # 显示图片
        self._update_image()
        
        # 设置窗口大小，适应图片但不超过屏幕
        screen = self.screen().availableGeometry()
        max_width = int(screen.width() * 0.9)
        max_height = int(screen.height() * 0.9)
        
        img_width = self.pixmap.width()
        img_height = self.pixmap.height()
        
        # 计算合适的显示尺寸
        if img_width <= max_width and img_height <= max_height:
            self.resize(img_width, img_height)
        else:
            # 需要缩放
            scale = min(max_width / img_width, max_height / img_height)
            self.resize(int(img_width * scale), int(img_height * scale))
    
    def _update_image(self):
        """更新显示的图片"""
        if not self.pixmap:
            return
        
        # 获取标签的实际尺寸
        label_size = self.image_label.size()
        if label_size.width() <= 0 or label_size.height() <= 0:
            # 如果尺寸还未确定，先设置原始图片
            self.image_label.setPixmap(self.pixmap)
            return
        
        # 缩放图片以适应标签大小，保持宽高比
        scaled = self.pixmap.scaled(
            label_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)
    
    def resizeEvent(self, event):
        """窗口大小改变时更新图片"""
        super().resizeEvent(event)
        self._update_image()
    
    def keyPressEvent(self, event):
        """按ESC或Enter关闭对话框"""
        if event.key() == Qt.Key.Key_Escape or event.key() == Qt.Key.Key_Return:
            self.close()
        super().keyPressEvent(event)
    
    def mousePressEvent(self, event):
        """点击任意位置关闭对话框"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.close()
        super().mousePressEvent(event)


class PromptGeneratorApp(QMainWindow):
    """提示词生成器主窗口"""

    def __init__(self):
        super().__init__()
        self.yaml_handler = YamlHandler()
        self.preset_manager = PresetManager()
        self.config_manager = AIConfigManager()
        self.field_widgets = {}  # 存储所有字段的widget引用
        self.current_preset_name = None
        
        # 生图相关
        self.selected_images = []
        self.image_buttons = []  # 存储图片按钮的列表
        self.generated_image_bytes = None
        self.generated_pixmap = None
        self.worker_thread = None

        self._setup_window()
        self._setup_ui()
        self._load_presets_to_selector()

    def _setup_window(self):
        self.setWindowTitle("Nano Banana 生图工具")
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

        # 主内容区域 - 使用分割器（三列布局）
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(8)

        # 左侧：表单区域
        form_area = self._create_form_area()
        self.main_splitter.addWidget(form_area)

        # 中间：JSON预览区域（可折叠）
        self.json_preview_area = self._create_json_preview_area()
        self.main_splitter.addWidget(self.json_preview_area)

        # 右侧：生图区域
        image_generate_area = self._create_image_generate_area()
        self.main_splitter.addWidget(image_generate_area)

        # 设置分割比例，默认隐藏中间列
        self.main_splitter.setSizes([600, 0, 600])
        # 默认隐藏中间列
        self.json_preview_area.setVisible(False)
        self.json_preview_visible = False
        main_layout.addWidget(self.main_splitter, 1)

        # 底部按钮区域
        button_bar = self._create_button_bar()
        main_layout.addWidget(button_bar)

    def _create_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 10)

        # Logo - 可点击
        logo_label = ClickableLabel()
        logo_path = get_images_dir() / "logo.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            # 缩放logo到合适大小，保持高质量
            scaled_pixmap = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        logo_label.setFixedSize(52, 52)
        logo_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        logo_label.setToolTip("点击访问 GitHub 仓库")
        logo_label.clicked.connect(self._open_github_link)
        layout.addWidget(logo_label)

        # 标题 - 可点击
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(12, 0, 0, 0)
        title_layout.setSpacing(4)

        title = ClickableLabel("Nano Banana 图片生成工具")
        title.setObjectName("appTitle")
        title.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        title.setToolTip("点击访问 GitHub 仓库")
        title.clicked.connect(self._open_github_link)
        title_layout.addWidget(title)

        subtitle = ClickableLabel("一站式AI图片生成工具，通过结构化提示词控制图片生成质量")
        subtitle.setObjectName("appSubtitle")
        subtitle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        subtitle.setToolTip("点击访问 GitHub 仓库")
        subtitle.clicked.connect(self._open_github_link)
        title_layout.addWidget(subtitle)

        layout.addWidget(title_container)
        layout.addStretch()

        return header

    def _open_github_link(self):
        """打开GitHub仓库链接"""
        url = QUrl("https://github.com/lissettecarlr/nano-banana-prompt-studio")
        QDesktopServices.openUrl(url)

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
        refresh_btn.setObjectName("secondaryButton")
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

        # 移除独立的AI生图按钮，已整合到主界面右侧

        layout.addStretch()

        # 管理预设按钮
        manage_btn = QPushButton("管理预设")
        manage_btn.setObjectName("secondaryButton")
        manage_btn.clicked.connect(self._show_preset_menu)
        layout.addWidget(manage_btn)

        # AI配置按钮
        ai_config_btn = QPushButton("AI配置")
        ai_config_btn.setObjectName("secondaryButton")
        ai_config_btn.clicked.connect(self._open_ai_config_dialog)
        layout.addWidget(ai_config_btn)

        return bar

    def _create_form_area(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 16, 0)

        # ===== 1. 基础设置 =====
        basic_group = FieldGroup("基础设置", color_class="basic")
        self._add_field(basic_group, "风格模式", "风格模式")
        self._add_field(basic_group, "画面气质", "画面气质")
        layout.addWidget(basic_group)

        # ===== 2. 场景设置 =====
        scene_group = FieldGroup("场景设置", color_class="scene")
        
        # 环境
        self._add_field(scene_group, "地点设定", "地点设定")
        self._add_field(scene_group, "光线", "光线")
        self._add_field(scene_group, "天气氛围", "天气氛围")
        
        # 主体整体描述
        self._add_field(scene_group, "整体描述", "整体描述")
        
        # 背景
        self._add_field(scene_group, "背景描述", "背景描述")
        self._add_field(scene_group, "景深", "景深")
        
        layout.addWidget(scene_group)

        # ===== 3. 主体细节 =====
        subject_group = FieldGroup("主体细节", color_class="subject")
        
        # 外形特征
        self._add_field(subject_group, "身材", "身材")
        self._add_field(subject_group, "面部", "面部")
        self._add_field(subject_group, "头发", "头发")
        self._add_field(subject_group, "眼睛", "眼睛")
        
        # 表情与动作
        self._add_field(subject_group, "情绪", "情绪")
        self._add_field(subject_group, "动作", "动作")
        
        # 服装配饰
        self._add_field(subject_group, "穿着", "穿着")
        self._add_field(subject_group, "服装细节", "服装细节")
        self._add_field(subject_group, "配饰", "配饰")
        
        layout.addWidget(subject_group)

        # ===== 4. 相机与构图 =====
        camera_group = FieldGroup("相机与构图", color_class="camera")
        self._add_field(camera_group, "机位角度", "机位角度")
        self._add_field(camera_group, "构图", "构图")
        self._add_field(camera_group, "镜头特性", "镜头特性")
        self._add_field(camera_group, "传感器画质", "传感器画质")
        layout.addWidget(camera_group)

        # ===== 5. 审美控制 =====
        aesthetic_group = FieldGroup("审美控制", color_class="aesthetic")
        self._add_field(aesthetic_group, "呈现意图", "呈现意图")
        self._add_field(aesthetic_group, "材质真实度", "材质真实度")
        self._add_field(aesthetic_group, "整体色调", "整体色调")
        self._add_field(aesthetic_group, "对比度", "对比度")
        self._add_field(aesthetic_group, "特殊效果", "特殊效果")
        layout.addWidget(aesthetic_group)

        # ===== 6. 特别要求（可选） =====
        special_container = QWidget()
        special_layout = QVBoxLayout(special_container)
        special_layout.setContentsMargins(0, 0, 0, 0)
        special_layout.setSpacing(0)

        # 启用开关
        self.special_requirement_enabled = QCheckBox("启用特别要求")
        self.special_requirement_enabled.setObjectName("specialRequirementToggle")
        self.special_requirement_enabled.setChecked(False)  # 默认不启用
        self.special_requirement_enabled.stateChanged.connect(self._on_special_requirement_toggle_changed)
        special_layout.addWidget(self.special_requirement_enabled)

        # 特别要求分组
        self.special_requirement_group = FieldGroup("特别要求", color_class="special")
        self.special_requirement_input = QTextEdit()
        self.special_requirement_input.setPlaceholderText("请输入额外的特别要求，这些内容不会纳入AI提示词生成和修改，只在生成图片时补充...")
        self.special_requirement_input.setMaximumHeight(100)
        self.special_requirement_input.setStyleSheet("""
            QTextEdit {
                padding: 8px;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #40a9ff;
            }
        """)
        self.special_requirement_group.add_widget(self.special_requirement_input)
        self.special_requirement_group.setVisible(False)  # 默认隐藏
        special_layout.addWidget(self.special_requirement_group)

        layout.addWidget(special_container)

        # ===== 7. 角色线稿生成（专用模式） =====
        line_art_container = QWidget()
        line_art_layout = QVBoxLayout(line_art_container)
        line_art_layout.setContentsMargins(0, 0, 0, 0)
        line_art_layout.setSpacing(0)

        # 角色线稿生成开关 - 使用与其他选项一致的命名格式
        self.line_art_mode_enabled = QCheckBox("启用角色线稿生成")
        self.line_art_mode_enabled.setObjectName("lineArtModeToggle")
        self.line_art_mode_enabled.setChecked(False)  # 默认不启用
        self.line_art_mode_enabled.setToolTip("启用后将使用专用线稿提示词，并禁用其他表单设置（除额外要求外）")
        self.line_art_mode_enabled.stateChanged.connect(self._on_line_art_mode_toggle_changed)
        line_art_layout.addWidget(self.line_art_mode_enabled)

        # 添加说明提示
        self.line_art_hint = QLabel("启用后，除特别要求外，其他提示词被禁用。")
        self.line_art_hint.setStyleSheet("color: #999999; font-size: 12px; margin-left: 24px; margin-bottom: 4px;")
        line_art_layout.addWidget(self.line_art_hint)

        # 线稿提示词分组
        self.line_art_group = FieldGroup("线稿提示词", color_class="special")
        
        # 提示词编辑框
        self.line_art_prompt_input = QTextEdit()
        self.line_art_prompt_input.setPlaceholderText("请输入角色线稿生成的提示词...")
        self.line_art_prompt_input.setMinimumHeight(120)
        self.line_art_prompt_input.setMaximumHeight(200)
        self.line_art_prompt_input.setStyleSheet("""
            QTextEdit {
                padding: 8px;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #40a9ff;
            }
        """)
        self.line_art_group.add_widget(self.line_art_prompt_input)
        
        # 保存按钮容器
        save_btn_container = QWidget()
        save_btn_layout = QHBoxLayout(save_btn_container)
        save_btn_layout.setContentsMargins(0, 8, 0, 0)
        save_btn_layout.addStretch()
        
        self.save_line_art_prompt_btn = QPushButton("保存提示词")
        self.save_line_art_prompt_btn.setObjectName("secondaryButton")
        self.save_line_art_prompt_btn.clicked.connect(self._save_line_art_prompt)
        save_btn_layout.addWidget(self.save_line_art_prompt_btn)
        
        self.line_art_group.add_widget(save_btn_container)
        self.line_art_group.setVisible(False)  # 默认隐藏
        line_art_layout.addWidget(self.line_art_group)

        layout.addWidget(line_art_container)

        # ===== 8. 反向提示词（可选） =====
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
        self.negative_group = FieldGroup("反向提示词", color_class="negative")
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

    def _create_json_preview_area(self) -> QWidget:
        """创建JSON预览区域（可折叠）"""
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

    def _toggle_json_preview(self):
        """切换JSON预览列的显示/隐藏"""
        self.json_preview_visible = not self.json_preview_visible
        self.json_preview_area.setVisible(self.json_preview_visible)
        
        # 更新按钮文字
        if self.json_preview_visible:
            self.json_toggle_btn.setText("JSON隐藏")
        else:
            self.json_toggle_btn.setText("JSON浏览")
        
        # 调整分割器大小
        if self.json_preview_visible:
            # 显示时，平均分配三列
            self.main_splitter.setSizes([500, 300, 500])
        else:
            # 隐藏时，左右两列平分
            self.main_splitter.setSizes([600, 0, 600])

    def _create_image_generate_area(self) -> QWidget:
        """创建生图区域"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(12)

        # 标题
        title = QLabel("图片生成")
        title.setObjectName("previewTitle")
        layout.addWidget(title)

        # 上方：参数和参考图片区域（合并）
        param_frame = QFrame()
        param_frame.setObjectName("paramFrame")
        param_frame.setStyleSheet("""
            QFrame#paramFrame {
                background-color: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
            }
        """)
        param_layout = QVBoxLayout(param_frame)
        param_layout.setContentsMargins(16, 12, 16, 12)
        param_layout.setSpacing(12)

        # 宽高比和输出尺寸合并成一行
        param_row = QWidget()
        param_row_layout = QHBoxLayout(param_row)
        param_row_layout.setContentsMargins(0, 0, 0, 0)
        param_row_layout.setSpacing(12)
        
        aspect_container = self._create_param_row("宽高比", ASPECT_RATIO_LIST)
        self.aspect_combo = aspect_container.findChild(QComboBox)
        param_row_layout.addWidget(aspect_container, 1)
        
        size_container = self._create_param_row("输出尺寸", IMAGE_SIZE_LIST)
        self.size_combo = size_container.findChild(QComboBox)
        param_row_layout.addWidget(size_container, 1)
        
        param_layout.addWidget(param_row)

        # 参考图片区域：合并到参数设置中
        img_row = QWidget()
        img_row_layout = QHBoxLayout(img_row)
        img_row_layout.setContentsMargins(0, 0, 0, 0)
        img_row_layout.setSpacing(12)

        # 添加参考图按钮
        self.add_image_btn = QPushButton("添加参考图")
        self.add_image_btn.setObjectName("secondaryButton")
        self.add_image_btn.clicked.connect(self._add_images)
        img_row_layout.addWidget(self.add_image_btn)

        # 图片按钮容器（显示图一、图二等）
        self.image_buttons_container = QWidget()
        self.image_buttons_layout = QHBoxLayout(self.image_buttons_container)
        self.image_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.image_buttons_layout.setSpacing(8)
        self.image_buttons_layout.addStretch()
        
        # 提示文本
        self.image_hint_label = QLabel("点击删除参考图")
        self.image_hint_label.setStyleSheet("font-size: 11px; color: #8c8c8c;")
        self.image_buttons_layout.addWidget(self.image_hint_label)
        
        img_row_layout.addWidget(self.image_buttons_container, 1)

        param_layout.addWidget(img_row)
        layout.addWidget(param_frame)

        # 下方：预览区域
        preview_frame = QFrame()
        preview_frame.setObjectName("previewFrame")
        preview_frame.setStyleSheet("""
            QFrame#previewFrame {
                background-color: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
            }
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        preview_layout.setSpacing(12)

        preview_title = QLabel("生成预览")
        preview_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #262626;")
        preview_layout.addWidget(preview_title)

        # 预览画布
        preview_canvas = QFrame()
        preview_canvas.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 #fafafa, stop:1 #f0f0f0); "
            "border: 2px dashed #d9d9d9; border-radius: 6px;"
        )
        canvas_layout = QVBoxLayout(preview_canvas)
        canvas_layout.setContentsMargins(16, 16, 16, 16)

        self.preview_area = ClickableLabel("图片生成后会显示在这里")
        self.preview_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_area.setMinimumHeight(300)
        self.preview_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_area.setStyleSheet("color: #bfbfbf; font-size: 13px; border: none;")
        # 禁用自动缩放，使用手动缩放以保持宽高比
        self.preview_area.setScaledContents(False)
        # 连接点击事件
        self.preview_area.clicked.connect(self._show_image_preview)
        canvas_layout.addWidget(self.preview_area)

        preview_layout.addWidget(preview_canvas, 1)
        layout.addWidget(preview_frame, 1)

        # 状态标签
        self.image_status_label = QLabel("准备就绪")
        self.image_status_label.setStyleSheet("color: #595959; font-size: 12px;")
        layout.addWidget(self.image_status_label)

        return container

    def _create_param_row(self, label_text: str, items: list, default: str = None) -> QWidget:
        """创建参数行"""
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(12)

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 12px; color: #595959; min-width: 60px;")
        container_layout.addWidget(label)

        combo = QComboBox()
        combo.addItems(items)
        if default:
            combo.setCurrentText(default)
        combo.setStyleSheet("""
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
        """)
        container_layout.addWidget(combo, 1)

        return container

    def _create_button_bar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(12)

        # 左侧按钮组
        # 清空按钮
        clear_btn = QPushButton("清空表单")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.clicked.connect(self._clear_form)
        layout.addWidget(clear_btn)

        # 复制按钮（从右侧移过来，样式和清空表单一致）
        copy_btn = QPushButton("复制表单")
        copy_btn.setObjectName("secondaryButton")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        layout.addWidget(copy_btn)

        # JSON浏览/隐藏按钮
        self.json_toggle_btn = QPushButton("JSON浏览")
        self.json_toggle_btn.setObjectName("secondaryButton")
        self.json_toggle_btn.clicked.connect(self._toggle_json_preview)
        layout.addWidget(self.json_toggle_btn)

        layout.addStretch()

        # 右侧按钮组：生图相关按钮
        self.save_image_btn = QPushButton("保存图片")
        self.save_image_btn.setObjectName("secondaryButton")
        self.save_image_btn.setEnabled(False)
        self.save_image_btn.clicked.connect(self._save_image)
        layout.addWidget(self.save_image_btn)

        self.generate_image_btn = QPushButton("生成图片")
        self.generate_image_btn.setObjectName("primaryButton")
        self.generate_image_btn.clicked.connect(self._on_generate_image_clicked)
        layout.addWidget(self.generate_image_btn)

        return bar

    def _on_field_changed(self, value: str = None):
        """字段值改变时自动更新预览"""
        self._generate_json()

    def _on_negative_toggle_changed(self, state: int):
        """反向提示词开关切换"""
        enabled = state == 2  # Qt.CheckState.Checked = 2
        self.negative_group.setVisible(enabled)
        self._generate_json()

    def _on_special_requirement_toggle_changed(self, state: int):
        """特别要求开关切换"""
        enabled = state == 2  # Qt.CheckState.Checked = 2
        self.special_requirement_group.setVisible(enabled)
        # 特别要求不纳入JSON预览，所以不需要调用 _generate_json()

    def _on_line_art_mode_toggle_changed(self, state: int):
        """角色线稿模式开关切换"""
        enabled = state == 2  # Qt.CheckState.Checked = 2
        
        # 显示/隐藏线稿提示词分组
        self.line_art_group.setVisible(enabled)
        
        # 如果启用，加载当前的线稿提示词到编辑框
        if enabled:
            current_prompt = self.yaml_handler.get_line_art_prompt()
            self.line_art_prompt_input.setText(current_prompt)
        
        # 需要禁用/启用的控件列表（不包括特别要求）
        controls_to_toggle = [
            self.negative_prompt_enabled,
        ]
        
        # 表单字段控件
        for widget in self.field_widgets.values():
            widget.setEnabled(not enabled)
        
        # 其他开关控件
        for ctrl in controls_to_toggle:
            ctrl.setEnabled(not enabled)
        
        # 反向提示词分组
        self.negative_group.setEnabled(not enabled)
        
        # 如果启用线稿模式，收起其他已展开的可选分组（除特别要求外）
        if enabled:
            self.negative_prompt_enabled.setChecked(False)
        
        self._generate_json()

    def _save_line_art_prompt(self):
        """保存线稿提示词到配置文件"""
        prompt_text = self.line_art_prompt_input.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "提示", "提示词不能为空")
            return
            
        try:
            self.yaml_handler.save_line_art_prompt(prompt_text)
            self._show_toast("提示词保存成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

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

        # 按照新的分类顺序组织数据
        data = {
            # 1. 基础设置
            "风格模式": get_value("风格模式"),
            "画面气质": get_value("画面气质"),
            # 2. 场景设置
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
            # 3. 相机与构图
            "相机": {
                "机位角度": get_value("机位角度"),
                "构图": get_value("构图"),
                "镜头特性": get_value("镜头特性"),
                "传感器画质": get_value("传感器画质"),
            },
            # 4. 审美控制
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

        # 保存为预设
        save_action = QAction("保存为预设", self)
        save_action.triggered.connect(self._save_as_preset)
        menu.addAction(save_action)

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

    # ========== 生图相关方法 ==========

    def _add_images(self):
        """添加参考图片"""
        if len(self.selected_images) >= 3:
            QMessageBox.information(self, "提示", "最多只能选择 3 张参考图")
            return

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择参考图片",
            "",
            "图像文件 (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not files:
            return

        remaining = 3 - len(self.selected_images)
        for path in files[:remaining]:
            if path not in self.selected_images:
                self.selected_images.append(path)
                self._append_image_item(path)

    def _number_to_chinese(self, num: int) -> str:
        """将数字转换为中文数字"""
        chinese_nums = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
        if 1 <= num <= 10:
            return chinese_nums[num]
        return str(num)

    def _append_image_item(self, path: str):
        """添加图片按钮"""
        index = len(self.selected_images) - 1  # 图片已添加到列表，所以索引是长度减1
        chinese_num = self._number_to_chinese(index + 1)
        btn = QPushButton(f"图{chinese_num}")
        btn.setToolTip(path)
        btn.setStyleSheet("""
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
        """)
        # 连接删除事件，确保正确捕获索引
        btn.clicked.connect(lambda checked, idx=index: self._remove_image_by_index(idx))
        self.image_buttons.append(btn)
        # 在提示文本之前插入按钮
        self.image_buttons_layout.insertWidget(self.image_buttons_layout.count() - 1, btn)

    def _remove_image_by_index(self, index: int):
        """根据索引删除图片"""
        if 0 <= index < len(self.selected_images):
            # 删除图片路径
            self.selected_images.pop(index)
            # 删除按钮
            btn = self.image_buttons.pop(index)
            btn.setParent(None)
            btn.deleteLater()
            # 更新剩余按钮的文本和事件
            self._refresh_image_buttons()

    def _refresh_image_buttons(self):
        """刷新图片按钮的文本和事件"""
        for i, btn in enumerate(self.image_buttons):
            chinese_num = self._number_to_chinese(i + 1)
            btn.setText(f"图{chinese_num}")
            # 断开旧连接
            try:
                btn.clicked.disconnect()
            except TypeError:
                pass  # 如果没有连接，忽略错误
            # 连接新事件，使用lambda并确保正确捕获索引
            btn.clicked.connect(lambda checked, idx=i: self._remove_image_by_index(idx))

    def _clear_images(self):
        """清空所有图片"""
        # 删除所有按钮
        for btn in self.image_buttons:
            btn.setParent(None)
            btn.deleteLater()
        self.image_buttons.clear()
        self.selected_images.clear()

    def _on_generate_image_clicked(self):
        """生成图片按钮点击"""
        # 先检查是否有任务进行中，如果有则直接返回（此时按钮应该已被禁用）
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.information(self, "提示", "已有任务进行中，请稍候")
            return

        # 检查是否启用了角色线稿模式
        if self.line_art_mode_enabled.isChecked():
            # 使用UI中的线稿提示词
            line_art_prompt = self.line_art_prompt_input.toPlainText().strip()
            if not line_art_prompt:
                QMessageBox.warning(self, "提示", "线稿提示词不能为空")
                return
            prompt_text = line_art_prompt
            
            # 如果启用了特别要求，追加到线稿提示词后面
            if self.special_requirement_enabled.isChecked():
                special_text = self.special_requirement_input.toPlainText().strip()
                if special_text:
                    prompt_text = prompt_text + "\n\n额外要求：" + special_text
        else:
            # 正常模式：使用表单数据
            prompt_data = self._collect_form_data()
            prompt_text = json.dumps(prompt_data, ensure_ascii=False, indent=2)
            
            if not prompt_text or prompt_text.strip() == "{}":
                QMessageBox.warning(self, "提示", "当前提示词为空，请先填写表单内容")
                return

            # 如果启用了特别要求，追加到prompt后面
            if self.special_requirement_enabled.isChecked():
                special_text = self.special_requirement_input.toPlainText().strip()
                if special_text:
                    prompt_text = prompt_text + "\n\n特别要求：" + special_text

        if not self.config_manager.get_gemini_api_key():
            reply = QMessageBox.question(
                self,
                "未配置 API",
                "尚未配置 Gemini API，是否现在配置？",
                QMessageBox.StandardButton.Yes,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._open_image_config_dialog()
            return

        # 验证通过后，立即禁用按钮，防止重复点击
        self._set_image_generating_state(True)
        
        self.generated_image_bytes = None
        self.generated_pixmap = None
        self.preview_area.setText("正在生成，请稍候...")
        self.preview_area.setPixmap(QPixmap())
        self.save_image_btn.setEnabled(False)
        
        # 根据模式显示不同的状态信息
        if self.line_art_mode_enabled.isChecked():
            self._set_image_status("提交到 Gemini 服务（角色线稿模式）", "#1890ff")
        else:
            self._set_image_status("提交到 Gemini 服务", "#1890ff")
        # 禁用点击预览功能
        self._enable_image_preview(False)

        self.worker_thread = GeminiImageThread(
            prompt=prompt_text,
            image_paths=self.selected_images,
            aspect_ratio=self.aspect_combo.currentText(),
            image_size=self.size_combo.currentText(),
            thinking_level="low",  # 移除思考级别参数，使用默认值
        )
        self.worker_thread.progress.connect(lambda msg: self._set_image_status(f"⏳ {msg}", "#1890ff"))
        self.worker_thread.image_ready.connect(self._on_image_ready)
        self.worker_thread.error.connect(self._on_generation_error)
        self.worker_thread.finished.connect(self._on_thread_finished)
        self.worker_thread.start()

    def _on_thread_finished(self):
        """线程完成"""
        self._set_image_generating_state(False)
        self.worker_thread = None

    def _on_image_ready(self, image_bytes: bytes):
        """图片生成完成"""
        self.generated_image_bytes = image_bytes
        pixmap = QPixmap.fromImage(QImage.fromData(image_bytes))
        self.generated_pixmap = pixmap
        self._refresh_preview_pixmap()
        self.save_image_btn.setEnabled(True)
        self._set_image_status("生成完成，点击图片可查看大图", "#52c41a")
        # 启用点击预览功能
        self._enable_image_preview(True)

    def _on_generation_error(self, message: str):
        """生成错误"""
        self._set_image_status(f"生成失败：{message}", "#ff4d4f")
        self.preview_area.setText("生成失败，请调整参数后重试")
        # 禁用点击预览功能
        self._enable_image_preview(False)
        # 确保在错误时也恢复按钮状态（虽然 _on_thread_finished 也会调用，但这里明确调用更安全）
        self._set_image_generating_state(False)

    def _set_image_generating_state(self, generating: bool):
        """设置生成状态"""
        self.aspect_combo.setEnabled(not generating)
        self.size_combo.setEnabled(not generating)
        self.add_image_btn.setEnabled(not generating)
        # 禁用所有图片按钮
        for btn in self.image_buttons:
            btn.setEnabled(not generating)
        self.generate_image_btn.setEnabled(not generating)

    def _save_image(self):
        """保存图片"""
        if not self.generated_image_bytes:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存为",
            "generated.png",
            "PNG 图片 (*.png);;JPEG 图片 (*.jpg *.jpeg)"
        )
        if not file_path:
            return

        import os
        suffix = os.path.splitext(file_path)[1].lower()
        format_name = "PNG" if suffix in ("", ".png") else "JPEG"
        image = QImage.fromData(self.generated_image_bytes)
        if not image.save(file_path, format_name):
            QMessageBox.critical(self, "错误", "保存图片失败，请重试")
        else:
            self._set_image_status(f"图片已保存到 {file_path}", "#52c41a")

    def _set_image_status(self, text: str, color: str = "#757575"):
        """设置状态文本"""
        self.image_status_label.setText(text)
        self.image_status_label.setStyleSheet(f"color: {color}; font-size: 12px;")

    def _open_ai_config_dialog(self):
        """打开统一的AI配置对话框"""
        from components.ai_dialog import UnifiedAIConfigDialog
        dialog = UnifiedAIConfigDialog(self)
        dialog.exec()
    
    def _open_image_config_dialog(self):
        """打开配置对话框（已废弃，保留以兼容）"""
        from components.ai_dialog import UnifiedAIConfigDialog
        dialog = UnifiedAIConfigDialog(self)
        dialog.exec()

    def _refresh_preview_pixmap(self):
        """刷新预览图片"""
        if not self.generated_pixmap:
            self.preview_area.setPixmap(QPixmap())
            self.preview_area.setScaledContents(False)
            return
        
        # 获取预览区域的实际可用尺寸
        preview_size = self.preview_area.size()
        if preview_size.width() <= 0 or preview_size.height() <= 0:
            # 如果尺寸还未确定，先设置原始图片
            self.preview_area.setPixmap(self.generated_pixmap)
            return
        
        # 直接使用 QPixmap.scaled() 方法，保持宽高比，确保图片完整显示
        scaled = self.generated_pixmap.scaled(
            preview_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        
        self.preview_area.setPixmap(scaled)
        self.preview_area.setScaledContents(False)  # 禁用自动缩放，使用手动缩放
    
    def _enable_image_preview(self, enabled: bool):
        """启用/禁用图片预览功能"""
        if enabled and self.generated_pixmap:
            # 设置手型光标，提示可点击
            self.preview_area.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            # 恢复默认光标
            self.preview_area.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
    
    def _show_image_preview(self):
        """显示图片预览对话框"""
        if not self.generated_pixmap:
            return
        
        dialog = ImagePreviewDialog(self.generated_pixmap, self)
        dialog.exec()

    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        if hasattr(self, 'preview_area') and self.generated_pixmap:
            self._refresh_preview_pixmap()

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
            # 重置特别要求开关
            self.special_requirement_enabled.setChecked(False)
            self.special_requirement_group.setVisible(False)
            self.special_requirement_input.clear()
            # 清空生图相关
            if hasattr(self, 'selected_images'):
                self._clear_images()
            self.generated_image_bytes = None
            self.generated_pixmap = None
            if hasattr(self, 'preview_area'):
                self.preview_area.setText("图片生成后会显示在这里")
                self.preview_area.setPixmap(QPixmap())
            if hasattr(self, 'save_image_btn'):
                self.save_image_btn.setEnabled(False)
            if hasattr(self, 'image_status_label'):
                self._set_image_status("准备就绪")
            # 禁用预览功能
            self._enable_image_preview(False)
            self._show_toast("表单已清空")

    def _show_toast(self, message: str):
        """显示简短提示"""
        self.statusBar().showMessage(message, 3000)
