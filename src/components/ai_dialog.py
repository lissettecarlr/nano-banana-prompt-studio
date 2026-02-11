"""AI生成提示词对话框 - 流式输出版"""
import json
import os
from typing import List
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QFrame,
    QWidget,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QScrollArea,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap

from utils.ai_config import AIConfigManager
from utils.ai_service import AIService


class AIConfigDialog(QDialog):
    """AI配置对话框"""
    
    config_saved = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = AIConfigManager()
        self._setup_ui()
        self._load_config()
    
    def _setup_ui(self):
        self.setWindowTitle("AI API 配置")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 说明
        info_label = QLabel(
            "请配置 OpenAI 兼容的 API 信息。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #757575; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(info_label)
        
        # Base URL
        url_container = QWidget()
        url_layout = QVBoxLayout(url_container)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.setSpacing(4)
        
        url_label = QLabel("API Base URL")
        url_label.setStyleSheet("font-weight: 500; font-size: 13px;")
        url_layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.openai.com/v1")
        url_layout.addWidget(self.url_input)
        
        url_hint = QLabel(" 通义千问: https://dashscope.aliyuncs.com/compatible-mode/v1")
        url_hint.setStyleSheet("color: #9E9E9E; font-size: 11px;")
        url_hint.setWordWrap(True)
        url_layout.addWidget(url_hint)
        
        layout.addWidget(url_container)
        
        # API Key
        key_container = QWidget()
        key_layout = QVBoxLayout(key_container)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(4)
        
        key_label = QLabel("API Key")
        key_label.setStyleSheet("font-weight: 500; font-size: 13px;")
        key_layout.addWidget(key_label)
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("sk-...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_layout.addWidget(self.key_input)
        
        # 显示/隐藏密钥按钮
        key_actions = QHBoxLayout()
        key_actions.setContentsMargins(0, 0, 0, 0)
        
        self.show_key_btn = QPushButton("显示密钥")
        self.show_key_btn.setFixedWidth(90)
        self.show_key_btn.clicked.connect(self._toggle_key_visibility)
        key_actions.addWidget(self.show_key_btn)
        key_actions.addStretch()
        key_layout.addLayout(key_actions)
        
        layout.addWidget(key_container)
        
        # Model
        model_container = QWidget()
        model_layout = QVBoxLayout(model_container)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(4)
        
        model_label = QLabel("模型名称")
        model_label.setStyleSheet("font-weight: 500; font-size: 13px;")
        model_layout.addWidget(model_label)
        
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("gpt-5.1")
        model_layout.addWidget(self.model_input)
        
        model_hint = QLabel("OpenAI: gpt-4.1, gpt-5.1  |   通义: qwen3-max")
        model_hint.setStyleSheet("color: #9E9E9E; font-size: 11px;")
        model_hint.setWordWrap(True)
        model_layout.addWidget(model_hint)
        
        layout.addWidget(model_container)
        
        layout.addStretch()
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        btn_layout.addStretch()
        
        save_btn = QPushButton("保存配置")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_config)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_config(self):
        """加载现有配置"""
        config = self.config_manager.load_config()
        # 只在配置存在且非空时设置文本，否则使用placeholder
        base_url = config.get("base_url", "")
        if base_url:
            self.url_input.setText(base_url)
        
        api_key = config.get("api_key", "")
        if api_key:
            self.key_input.setText(api_key)
        
        model = config.get("model", "")
        if model:
            self.model_input.setText(model)
    
    def _toggle_key_visibility(self):
        """切换密钥可见性"""
        if self.key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_btn.setText("隐藏密钥")
        else:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_btn.setText("显示密钥")
    
    def _save_config(self):
        """保存配置"""
        base_url = self.url_input.text().strip()
        api_key = self.key_input.text().strip()
        model = self.model_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "提示", "请输入 API Key")
            return
        
        # 直接保存用户输入的值（包括空值），不填充默认值
        config = {
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
        }
        
        if self.config_manager.save_config(config):
            self.config_saved.emit()
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "保存配置失败")


class UnifiedAIConfigDialog(QDialog):
    """统一的AI配置对话框 - 包含提示词生成和图片生成两个AI的配置"""
    
    config_saved = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = AIConfigManager()
        self._setup_ui()
        self._load_config()
    
    def _setup_ui(self):
        self.setWindowTitle("AI 配置")
        self.setMinimumWidth(600)
        self.setModal(True)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fa;
            }
            QComboBox {
                padding: 8px 12px;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                background-color: white;
                min-height: 32px;
            }
            QComboBox:hover {
                border-color: #40a9ff;
            }
            QLineEdit, QTextEdit {
                padding: 8px;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #40a9ff;
            }
            QPushButton {
                padding: 8px 24px;
                border-radius: 6px;
                border: 1px solid #d9d9d9;
                background-color: #ffffff;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                border-color: #40a9ff;
                color: #40a9ff;
            }
            QPushButton#primaryButton {
                background-color: #1890ff;
                color: white;
                border: none;
                font-weight: 500;
            }
            QPushButton#primaryButton:hover {
                background-color: #40a9ff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("AI 配置")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #262626;")
        layout.addWidget(title)
        
        # 使用滚动区域以支持更多内容
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)
        
        # ===== 第一部分：提示词生成/修改AI配置 =====
        prompt_frame = QFrame()
        prompt_frame.setObjectName("promptConfigFrame")
        prompt_frame.setStyleSheet("""
            QFrame#promptConfigFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f7ff, stop:1 #ffffff);
                border: 2px solid #1890ff;
                border-radius: 12px;
                padding: 4px;
            }
        """)
        prompt_layout = QVBoxLayout(prompt_frame)
        prompt_layout.setContentsMargins(20, 20, 20, 20)
        prompt_layout.setSpacing(16)
        
        # 标题区域，带背景
        prompt_title_container = QWidget()
        prompt_title_container.setStyleSheet("""
            QWidget {
                background-color: #1890ff;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        prompt_title_layout = QHBoxLayout(prompt_title_container)
        prompt_title_layout.setContentsMargins(0, 0, 0, 0)
        prompt_title_layout.setSpacing(10)
        
        prompt_title = QLabel("提示词生成/修改 AI")
        prompt_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        prompt_title_layout.addWidget(prompt_title)
        prompt_title_layout.addStretch()
        
        prompt_layout.addWidget(prompt_title_container)
        
        prompt_layout.addWidget(self._build_labeled_widget("Base URL", self._create_url_input("prompt")))
        prompt_layout.addWidget(self._build_labeled_widget("API Key", self._create_key_input("prompt")))
        prompt_layout.addWidget(self._build_labeled_widget("模型名称", self._create_model_input("prompt")))
        
        content_layout.addWidget(prompt_frame)
        
        # ===== 第二部分：图片生成AI配置 =====
        image_frame = QFrame()
        image_frame.setObjectName("imageConfigFrame")
        image_frame.setStyleSheet("""
            QFrame#imageConfigFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fff7e6, stop:1 #ffffff);
                border: 2px solid #fa8c16;
                border-radius: 12px;
                padding: 4px;
            }
        """)
        image_layout = QVBoxLayout(image_frame)
        image_layout.setContentsMargins(20, 20, 20, 20)
        image_layout.setSpacing(16)
        
        # 标题区域，带背景
        image_title_container = QWidget()
        image_title_container.setStyleSheet("""
            QWidget {
                background-color: #fa8c16;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        image_title_layout = QHBoxLayout(image_title_container)
        image_title_layout.setContentsMargins(0, 0, 0, 0)
        image_title_layout.setSpacing(10)
        
        image_title = QLabel("图片生成 AI")
        image_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        image_title_layout.addWidget(image_title)
        image_title_layout.addStretch()
        
        image_layout.addWidget(image_title_container)
        

        image_layout.addWidget(self._build_labeled_widget("Base URL", self._create_url_input("image")))
        image_layout.addWidget(self._build_labeled_widget("API Key", self._create_key_input("image")))
        image_layout.addWidget(self._build_labeled_widget("模型名称", self._create_model_input("image")))
        
        content_layout.addWidget(image_frame)
        
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)
        
        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存配置")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(save_btn)
        
        layout.addLayout(btn_row)
    
    def _create_url_input(self, prefix: str) -> QWidget:
        """创建URL输入框"""
        widget = QLineEdit()
        if prefix == "prompt":
            widget.setPlaceholderText("https://api.openai.com/v1")
            self.prompt_url_input = widget
        else:
            widget.setPlaceholderText("https://generativelanguage.googleapis.com")
            self.image_url_input = widget
        return widget
    
    def _create_key_input(self, prefix: str) -> QWidget:
        """创建API Key输入框"""
        widget = QTextEdit()
        widget.setFixedHeight(70)
        widget.setPlaceholderText("sk-...")
        if prefix == "prompt":
            self.prompt_key_input = widget
        else:
            self.image_key_input = widget
        return widget
    
    def _create_model_input(self, prefix: str) -> QWidget:
        """创建模型输入框"""
        widget = QLineEdit()
        if prefix == "prompt":
            widget.setPlaceholderText("gpt-5.1")
            self.prompt_model_input = widget
        else:
            widget.setPlaceholderText("gemini-3-pro-image-preview")
            self.image_model_input = widget
        return widget
    
    def _build_labeled_widget(self, label_text: str, widget: QWidget) -> QWidget:
        """创建带标签的输入组件"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)
        
        label = QLabel(label_text)
        label.setStyleSheet("font-weight: 600; font-size: 13px; color: #262626;")
        container_layout.addWidget(label)
        container_layout.addWidget(widget)
        return container
    
    def _load_config(self):
        """加载现有配置"""
        config = self.config_manager.load_config()
        
        # 提示词生成AI配置 - 只在配置存在且非空时设置文本，否则使用placeholder
        base_url = config.get("base_url", "")
        if base_url:
            self.prompt_url_input.setText(base_url)
        
        api_key = config.get("api_key", "")
        if api_key:
            self.prompt_key_input.setPlainText(api_key)
        
        model = config.get("model", "")
        if model:
            self.prompt_model_input.setText(model)
        
        # 图片生成AI配置 - 只在配置存在且非空时设置文本，否则使用placeholder
        gemini_base_url = config.get("gemini_base_url", "")
        if gemini_base_url:
            self.image_url_input.setText(gemini_base_url)
        
        gemini_api_key = config.get("gemini_api_key", "")
        if gemini_api_key:
            self.image_key_input.setPlainText(gemini_api_key)
        
        gemini_model = config.get("gemini_model", "")
        if gemini_model:
            self.image_model_input.setText(gemini_model)
    
    def _save_config(self):
        """保存配置"""
        # 提示词生成AI配置 - 直接获取用户输入，不填充默认值
        prompt_base_url = self.prompt_url_input.text().strip()
        prompt_api_key = self.prompt_key_input.toPlainText().strip()
        prompt_model = self.prompt_model_input.text().strip()
        
        # 图片生成AI配置 - 直接获取用户输入，不填充默认值
        image_base_url = self.image_url_input.text().strip()
        image_api_key = self.image_key_input.toPlainText().strip()
        image_model = self.image_model_input.text().strip()
        
        # 验证必填项
        if not prompt_api_key and not image_api_key:
            QMessageBox.warning(self, "提示", "请至少配置一个AI服务的API Key")
            return
        
        # 直接保存用户输入的值（包括空值），不填充默认值
        config = {
            "base_url": prompt_base_url,
            "api_key": prompt_api_key,
            "model": prompt_model,
            "gemini_base_url": image_base_url,
            "gemini_api_key": image_api_key,
            "gemini_model": image_model,
        }
        
        if self.config_manager.save_config(config):
            self.config_saved.emit()
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "保存配置失败，请重试")


class AIGenerateDialog(QDialog):
    """AI生成提示词对话框 - 流式输出版"""
    
    # 生成完成信号，传递生成的数据
    generated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_service = AIService()
        self.config_manager = AIConfigManager()
        self._is_generating = False
        self._full_content = ""
        self.selected_images: List[str] = []
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("AI 生成提示词")
        self.setMinimumSize(1100, 750)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fa;
            }
            QPushButton {
                padding: 8px 20px;
                border-radius: 6px;
                border: 1px solid #d9d9d9;
                background-color: #ffffff;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                border-color: #40a9ff;
                color: #40a9ff;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #bfbfbf;
                border-color: #d9d9d9;
            }
            QPushButton#primaryButton {
                background-color: #1890ff;
                color: white;
                border: none;
                font-weight: 500;
            }
            QPushButton#primaryButton:hover {
                background-color: #40a9ff;
            }
            QPushButton#primaryButton:disabled {
                background-color: #d9d9d9;
            }
            QListWidget {
                border: 1px solid #e8e8e8;
                border-radius: 6px;
                background-color: white;
                padding: 8px;
            }
            QListWidget::item {
                border: 2px solid #e8e8e8;
                border-radius: 6px;
                padding: 4px;
                background-color: #fafafa;
            }
            QListWidget::item:selected {
                border-color: #1890ff;
                background-color: #e6f7ff;
            }
            QListWidget::item:hover {
                border-color: #40a9ff;
                background-color: #f0f5ff;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 28, 28, 28)
        main_layout.setSpacing(20)
        
        # 顶部标题栏
        header = QHBoxLayout()
        header.setSpacing(16)
        
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)
        
        title = QLabel("AI 生成提示词")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #262626;")
        title_layout.addWidget(title)
        
        subtitle = QLabel("根据文字描述和参考图片生成提示词")
        subtitle.setStyleSheet("font-size: 13px; color: #8c8c8c;")
        title_layout.addWidget(subtitle)
        
        header.addWidget(title_container)
        header.addStretch()
        
        main_layout.addLayout(header)
        
        # 左右分栏布局
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # 左侧：输入区域（分为上下两部分）
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        left_panel.setMaximumWidth(400)
        left_panel.setMinimumWidth(350)
        
        # 文本输入区域
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_frame.setStyleSheet(
            "QFrame#inputFrame {"
            "  background-color: #ffffff;"
            "  border: 1px solid #e8e8e8;"
            "  border-radius: 12px;"
            "}"
        )
        input_frame_layout = QVBoxLayout(input_frame)
        input_frame_layout.setContentsMargins(20, 20, 20, 20)
        input_frame_layout.setSpacing(12)
        
        input_label = QLabel("描述你想要的画面")
        input_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #262626;")
        input_frame_layout.addWidget(input_label)
        
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(
            "例如：\n"
            "- 一个穿着白色连衣裙的少女站在樱花树下，春天的午后，阳光透过花瓣洒落\n"
            "- 赛博朋克风格的城市夜景，霓虹灯闪烁，雨后的街道倒映着五彩灯光\n"
            "- 蔚蓝档案风格的星野，穿着中秋节主题的汉服，在海边看月亮"
        )
        font = QFont("Microsoft YaHei", 12)
        self.prompt_input.setFont(font)
        self.prompt_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 8px;
                min-height: 120px;
            }
            QTextEdit:focus {
                border-color: #40a9ff;
            }
        """)
        input_frame_layout.addWidget(self.prompt_input)
        
        left_layout.addWidget(input_frame)
        
        # 图片上传区域
        upload_frame = QFrame()
        upload_frame.setObjectName("uploadFrame")
        upload_frame.setStyleSheet(
            "QFrame#uploadFrame {"
            "  background-color: #ffffff;"
            "  border: 1px solid #e8e8e8;"
            "  border-radius: 12px;"
            "}"
        )
        upload_layout = QVBoxLayout(upload_frame)
        upload_layout.setContentsMargins(20, 20, 20, 20)
        upload_layout.setSpacing(12)
        
        img_header = QHBoxLayout()
        img_label = QLabel("参考图片")
        img_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #262626;")
        img_header.addWidget(img_label)
        
        img_count = QLabel("最多 3 张")
        img_count.setStyleSheet("font-size: 12px; color: #8c8c8c; padding: 2px 8px; background-color: #fafafa; border-radius: 4px;")
        img_header.addWidget(img_count)
        img_header.addStretch()
        
        upload_layout.addLayout(img_header)
        
        self.image_list = QListWidget()
        self.image_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.image_list.setMinimumHeight(150)
        self.image_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.image_list.setIconSize(QPixmap(120, 120).size())
        self.image_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.image_list.setSpacing(10)
        self.image_list.setWordWrap(True)
        upload_layout.addWidget(self.image_list)
        
        # 图片操作按钮
        img_btn_layout = QHBoxLayout()
        img_btn_layout.setSpacing(8)
        
        self.add_image_btn = QPushButton("+ 添加")
        self.add_image_btn.clicked.connect(self._add_images)
        self.add_image_btn.setStyleSheet("QPushButton { min-width: 60px; padding: 6px 12px; }")
        img_btn_layout.addWidget(self.add_image_btn)
        
        self.remove_image_btn = QPushButton("移除")
        self.remove_image_btn.clicked.connect(self._remove_selected_images)
        self.remove_image_btn.setStyleSheet("QPushButton { min-width: 60px; padding: 6px 12px; }")
        img_btn_layout.addWidget(self.remove_image_btn)
        
        self.clear_image_btn = QPushButton("清空")
        self.clear_image_btn.clicked.connect(self._clear_images)
        self.clear_image_btn.setStyleSheet("QPushButton { min-width: 60px; padding: 6px 12px; }")
        img_btn_layout.addWidget(self.clear_image_btn)
        
        upload_layout.addLayout(img_btn_layout)
        
        helper = QLabel("支持 PNG/JPG/WebP/BMP 格式")
        helper.setStyleSheet("color: #8c8c8c; font-size: 12px;")
        upload_layout.addWidget(helper)
        
        left_layout.addWidget(upload_frame)
        left_layout.addStretch()
        
        content_layout.addWidget(left_panel)
        
        # 右侧：AI生成结果显示
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)
        
        output_frame = QFrame()
        output_frame.setObjectName("outputFrame")
        output_frame.setStyleSheet(
            "QFrame#outputFrame {"
            "  background-color: #ffffff;"
            "  border: 1px solid #e8e8e8;"
            "  border-radius: 12px;"
            "}"
        )
        output_frame_layout = QVBoxLayout(output_frame)
        output_frame_layout.setContentsMargins(20, 20, 20, 20)
        output_frame_layout.setSpacing(12)
        
        output_header = QHBoxLayout()
        output_label = QLabel("AI 生成结果")
        output_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #262626;")
        output_header.addWidget(output_label)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #757575; font-size: 12px;")
        output_header.addWidget(self.status_label)
        output_header.addStretch()
        output_frame_layout.addLayout(output_header)
        
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setPlaceholderText("生成的内容将在这里实时显示...")
        mono_font = QFont("Consolas", 11)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.output_display.setFont(mono_font)
        self.output_display.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #262626;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 12px;
                min-height: 400px;
            }
        """)
        output_frame_layout.addWidget(self.output_display, 1)
        
        right_layout.addWidget(output_frame, 1)
        
        content_layout.addWidget(right_panel, 1)
        
        main_layout.addLayout(content_layout, 1)
        
        # 底部操作栏
        footer = QFrame()
        footer.setStyleSheet(
            "background-color: #ffffff; border: 1px solid #e8e8e8; border-radius: 10px; padding: 4px;"
        )
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 12, 16, 12)
        footer_layout.setSpacing(12)
        
        footer_layout.addStretch()
        
        # 统一按钮样式
        button_style = """
            QPushButton {
                padding: 10px 24px;
                font-size: 14px;
                min-width: 100px;
                max-width: 100px;
            }
        """
        
        self.cancel_btn = QPushButton("关闭")
        self.cancel_btn.setStyleSheet(button_style)
        self.cancel_btn.clicked.connect(self._on_cancel)
        footer_layout.addWidget(self.cancel_btn)
        
        self.apply_btn = QPushButton("应用提示词")
        self.apply_btn.setObjectName("secondaryButton")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setStyleSheet(button_style)
        self.apply_btn.clicked.connect(self._on_apply)
        footer_layout.addWidget(self.apply_btn)
        
        self.generate_btn = QPushButton("开始AI生成")
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.setStyleSheet(button_style + """
            QPushButton#primaryButton {
                background-color: #1890ff;
                color: white;
                border: none;
                font-weight: 500;
            }
            QPushButton#primaryButton:hover {
                background-color: #40a9ff;
            }
            QPushButton#primaryButton:disabled {
                background-color: #d9d9d9;
            }
        """)
        self.generate_btn.clicked.connect(self._on_generate)
        footer_layout.addWidget(self.generate_btn)
        
        main_layout.addWidget(footer)
    
    def _add_images(self):
        """添加图片"""
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
    
    def _append_image_item(self, path: str):
        """添加图片项到列表"""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            thumbnail = pixmap.scaled(
                120, 120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            icon = QIcon(thumbnail)
            item = QListWidgetItem(self.image_list)
            item.setIcon(icon)
            item.setText(os.path.basename(path))
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        else:
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(f"{path} (加载失败)")
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.image_list.addItem(item)
    
    def _remove_selected_images(self):
        """移除选中的图片"""
        for item in self.image_list.selectedItems():
            path = item.data(Qt.ItemDataRole.UserRole)
            self.selected_images = [p for p in self.selected_images if p != path]
            idx = self.image_list.row(item)
            self.image_list.takeItem(idx)
    
    def _clear_images(self):
        """清空所有图片"""
        self.selected_images.clear()
        self.image_list.clear()
    
    def _on_generate(self):
        """开始生成"""
        if self._is_generating:
            # 如果正在生成，点击变为取消
            self.ai_service.cancel()
            self._is_generating = False
            self._set_generating_ui(False)
            self.status_label.setText("已取消")
            return
        
        # 检查配置
        if not self.ai_service.is_configured():
            reply = QMessageBox.question(
                self,
                "未配置 API",
                "尚未配置 AI API，是否现在配置？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._show_config()
            return
        
        # 检查输入
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt and not self.selected_images:
            QMessageBox.warning(self, "提示", "请输入画面描述或上传参考图片")
            return
        
        # 清空输出并开始
        self.output_display.clear()
        self._full_content = ""
        self._is_generating = True
        self._set_generating_ui(True)
        self.apply_btn.setEnabled(False)
        # 将应用按钮恢复为普通样式
        self.apply_btn.setObjectName("secondaryButton")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 24px;
                font-size: 14px;
                min-width: 100px;
                max-width: 100px;
            }
        """)
        
        # 传递图片路径列表
        image_paths = self.selected_images.copy() if self.selected_images else None
        
        self.ai_service.generate_async(
            prompt,
            image_paths=image_paths,
            on_finished=self._on_generate_finished,
            on_error=self._on_generate_error,
            on_progress=self._on_generate_progress,
            on_stream_chunk=self._on_stream_chunk,
            on_stream_done=self._on_stream_done,
        )
    
    def _set_generating_ui(self, generating: bool):
        """设置生成中的UI状态"""
        self.prompt_input.setReadOnly(generating)
        self.add_image_btn.setEnabled(not generating)
        self.remove_image_btn.setEnabled(not generating)
        self.clear_image_btn.setEnabled(not generating)
        self.image_list.setEnabled(not generating)
        
        if generating:
            self.generate_btn.setText("停止")
            self.status_label.setText("生成中...")
            self.status_label.setStyleSheet("color: #2196F3; font-size: 12px;")
        else:
            self.generate_btn.setText("开始AI生成")
    
    def _on_generate_progress(self, message: str):
        """进度更新"""
        self.status_label.setText(message)
    
    def _on_stream_chunk(self, chunk: str):
        """收到流式内容块"""
        self._full_content += chunk
        # 追加到显示区域
        cursor = self.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.output_display.setTextCursor(cursor)
        # 滚动到底部
        scrollbar = self.output_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _on_stream_done(self, full_content: str):
        """流式完成"""
        self._is_generating = False
        self._set_generating_ui(False)
        self._full_content = full_content
        self.status_label.setText("生成完成")
        self.status_label.setStyleSheet("color: #4CAF50; font-size: 12px;")
        self.apply_btn.setEnabled(True)
        # 将应用按钮改为蓝色高亮样式
        self.apply_btn.setObjectName("primaryButton")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 24px;
                font-size: 14px;
                min-width: 100px;
                max-width: 100px;
            }
            QPushButton#primaryButton {
                background-color: #1890ff;
                color: white;
                border: none;
                font-weight: 500;
            }
            QPushButton#primaryButton:hover {
                background-color: #40a9ff;
            }
            QPushButton#primaryButton:disabled {
                background-color: #d9d9d9;
            }
        """)
    
    def _on_generate_finished(self, data: dict):
        """生成完成（JSON解析后）"""
        # 流式模式下这个不会被调用
        pass
    
    def _on_generate_error(self, error: str):
        """生成错误"""
        self._is_generating = False
        self._set_generating_ui(False)
        self.status_label.setText(f"错误: {error}")
        self.status_label.setStyleSheet("color: #F44336; font-size: 12px;")
    
    def _on_apply(self):
        """应用生成的内容到表单"""
        content = self._full_content.strip()
        
        if not content:
            QMessageBox.warning(self, "提示", "没有可应用的内容")
            return
        
        # 清理代码块标记
        if content.startswith("``json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # 解析JSON
        try:
            result = json.loads(content)
            self.generated.emit(result)
            self.accept()
        except json.JSONDecodeError as e:
            QMessageBox.warning(
                self, 
                "JSON解析失败", 
                f"AI返回的内容不是有效的JSON格式:\n{str(e)}\n\n你可以手动复制内容进行修改。"
            )
    
    def _on_cancel(self):
        """关闭按钮点击"""
        if self._is_generating:
            self.ai_service.cancel()
        self.reject()
    
    def closeEvent(self, event):
        """关闭事件"""
        if self._is_generating:
            self.ai_service.cancel()
        super().closeEvent(event)


class AIModifyDialog(QDialog):
    """AI修改提示词对话框 - 流式输出版"""
    
    # 修改完成信号，传递修改后的数据
    modified = pyqtSignal(dict)
    
    def __init__(self, current_data: dict, parent=None):
        super().__init__(parent)
        self.current_data = current_data
        self.modified_data = None
        self.ai_service = AIService()
        self.config_manager = AIConfigManager()
        self._is_generating = False
        self._full_content = ""
        self.selected_images: List[str] = []
        self.diff_items = []  # 存储差异项信息
        self.diff_checkboxes = {}  # 存储路径到复选框的映射
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("AI 修改提示词")
        self.setMinimumSize(1100, 750)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fa;
            }
            QPushButton {
                padding: 8px 20px;
                border-radius: 6px;
                border: 1px solid #d9d9d9;
                background-color: #ffffff;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                border-color: #40a9ff;
                color: #40a9ff;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #bfbfbf;
                border-color: #d9d9d9;
            }
            QPushButton#primaryButton {
                background-color: #1890ff;
                color: white;
                border: none;
                font-weight: 500;
            }
            QPushButton#primaryButton:hover {
                background-color: #40a9ff;
            }
            QPushButton#primaryButton:disabled {
                background-color: #d9d9d9;
            }
            QListWidget {
                border: 1px solid #e8e8e8;
                border-radius: 6px;
                background-color: white;
                padding: 8px;
            }
            QListWidget::item {
                border: 2px solid #e8e8e8;
                border-radius: 6px;
                padding: 4px;
                background-color: #fafafa;
            }
            QListWidget::item:selected {
                border-color: #1890ff;
                background-color: #e6f7ff;
            }
            QListWidget::item:hover {
                border-color: #40a9ff;
                background-color: #f0f5ff;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 28, 28, 28)
        main_layout.setSpacing(20)
        
        # 顶部标题栏
        header = QHBoxLayout()
        header.setSpacing(16)
        
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)
        
        title = QLabel("AI 修改提示词")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #262626;")
        title_layout.addWidget(title)
        
        subtitle = QLabel("根据文字描述和参考图片修改提示词")
        subtitle.setStyleSheet("font-size: 13px; color: #8c8c8c;")
        title_layout.addWidget(subtitle)
        
        header.addWidget(title_container)
        header.addStretch()
        
        main_layout.addLayout(header)
        
        # 左右分栏布局
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # 左侧：输入区域（分为上下两部分）
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        left_panel.setMaximumWidth(400)
        left_panel.setMinimumWidth(350)
        
        # 文本输入区域
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_frame.setStyleSheet(
            "QFrame#inputFrame {"
            "  background-color: #ffffff;"
            "  border: 1px solid #e8e8e8;"
            "  border-radius: 12px;"
            "}"
        )
        input_frame_layout = QVBoxLayout(input_frame)
        input_frame_layout.setContentsMargins(20, 20, 20, 20)
        input_frame_layout.setSpacing(12)
        
        input_label = QLabel("描述你想要的修改")
        input_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #262626;")
        input_frame_layout.addWidget(input_label)
        
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(
            "例如：\n"
            "- 将角色改成穿汉服的样子\n"
            "- 把场景改为雪景\n"
            "- 让画面更加梦幻一些\n"
            "- 改成秋天的感觉"
        )
        font = QFont("Microsoft YaHei", 12)
        self.prompt_input.setFont(font)
        self.prompt_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 8px;
                min-height: 120px;
            }
            QTextEdit:focus {
                border-color: #40a9ff;
            }
        """)
        input_frame_layout.addWidget(self.prompt_input)

        left_layout.addWidget(input_frame)
        
        # 图片上传区域
        upload_frame = QFrame()
        upload_frame.setObjectName("uploadFrame")
        upload_frame.setStyleSheet(
            "QFrame#uploadFrame {"
            "  background-color: #ffffff;"
            "  border: 1px solid #e8e8e8;"
            "  border-radius: 12px;"
            "}"
        )
        upload_layout = QVBoxLayout(upload_frame)
        upload_layout.setContentsMargins(20, 20, 20, 20)
        upload_layout.setSpacing(12)
        
        img_header = QHBoxLayout()
        img_label = QLabel("参考图片")
        img_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #262626;")
        img_header.addWidget(img_label)
        
        img_count = QLabel("最多 3 张")
        img_count.setStyleSheet("font-size: 12px; color: #8c8c8c; padding: 2px 8px; background-color: #fafafa; border-radius: 4px;")
        img_header.addWidget(img_count)
        img_header.addStretch()
        
        upload_layout.addLayout(img_header)
        
        self.image_list = QListWidget()
        self.image_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.image_list.setMinimumHeight(150)
        self.image_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.image_list.setIconSize(QPixmap(120, 120).size())
        self.image_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.image_list.setSpacing(10)
        self.image_list.setWordWrap(True)
        upload_layout.addWidget(self.image_list)
        
        # 图片操作按钮
        img_btn_layout = QHBoxLayout()
        img_btn_layout.setSpacing(8)
        
        self.add_image_btn = QPushButton("+ 添加")
        self.add_image_btn.clicked.connect(self._add_images)
        self.add_image_btn.setStyleSheet("QPushButton { min-width: 60px; padding: 6px 12px; }")
        img_btn_layout.addWidget(self.add_image_btn)
        
        self.remove_image_btn = QPushButton("移除")
        self.remove_image_btn.clicked.connect(self._remove_selected_images)
        self.remove_image_btn.setStyleSheet("QPushButton { min-width: 60px; padding: 6px 12px; }")
        img_btn_layout.addWidget(self.remove_image_btn)
        
        self.clear_image_btn = QPushButton("清空")
        self.clear_image_btn.clicked.connect(self._clear_images)
        self.clear_image_btn.setStyleSheet("QPushButton { min-width: 60px; padding: 6px 12px; }")
        img_btn_layout.addWidget(self.clear_image_btn)
        
        upload_layout.addLayout(img_btn_layout)
        
        helper = QLabel("支持 PNG/JPG/WebP/BMP 格式")
        helper.setStyleSheet("color: #8c8c8c; font-size: 12px;")
        upload_layout.addWidget(helper)
        
        left_layout.addWidget(upload_frame)
        left_layout.addStretch()
        
        content_layout.addWidget(left_panel)
        
        # 右侧：AI生成结果显示
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)
        
        output_frame = QFrame()
        output_frame.setObjectName("outputFrame")
        output_frame.setStyleSheet(
            "QFrame#outputFrame {"
            "  background-color: #ffffff;"
            "  border: 1px solid #e8e8e8;"
            "  border-radius: 12px;"
            "}"
        )
        output_frame_layout = QVBoxLayout(output_frame)
        output_frame_layout.setContentsMargins(20, 20, 20, 20)
        output_frame_layout.setSpacing(12)
        
        output_header = QHBoxLayout()
        output_label = QLabel("AI 修改结果")
        output_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #262626;")
        output_header.addWidget(output_label)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #757575; font-size: 12px;")
        output_header.addWidget(self.status_label)
        output_header.addStretch()
        output_frame_layout.addLayout(output_header)
        
        # 结果显示堆栈
        self.result_stack = QStackedWidget()
        
        # 流式输出显示
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setPlaceholderText("修改的内容将在这里实时显示...")
        mono_font = QFont("Consolas", 11)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.output_display.setFont(mono_font)
        self.output_display.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #262626;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 12px;
                min-height: 400px;
            }
        """)
        self.result_stack.addWidget(self.output_display)
        
        # 对比结果显示 - 使用可交互的复选框列表
        compare_scroll = QScrollArea()
        compare_scroll.setWidgetResizable(True)
        compare_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
            }
        """)
        
        self.compare_widget = QWidget()
        self.compare_layout = QVBoxLayout(self.compare_widget)
        self.compare_layout.setContentsMargins(16, 16, 16, 16)
        self.compare_layout.setSpacing(12)
        self.compare_layout.addStretch()
        
        compare_scroll.setWidget(self.compare_widget)
        self.result_stack.addWidget(compare_scroll)
        
        # 保留一个文本显示作为备用（用于显示"没有检测到任何修改"）
        self.compare_display = QTextEdit()
        self.compare_display.setReadOnly(True)
        self.compare_display.setFont(mono_font)
        self.compare_display.setStyleSheet("""
            QTextEdit {
                background-color: #F8F9FA;
                color: #333333;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 12px;
                min-height: 400px;
            }
        """)
        self.result_stack.addWidget(self.compare_display)
        
        output_frame_layout.addWidget(self.result_stack, 1)
        
        right_layout.addWidget(output_frame, 1)
        
        content_layout.addWidget(right_panel, 1)
        
        main_layout.addLayout(content_layout, 1)
        
        # 底部操作栏
        footer = QFrame()
        footer.setStyleSheet(
            "background-color: #ffffff; border: 1px solid #e8e8e8; border-radius: 10px; padding: 4px;"
        )
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 12, 16, 12)
        footer_layout.setSpacing(12)
        
        footer_layout.addStretch()
        
        # 统一按钮样式
        button_style = """
            QPushButton {
                padding: 10px 24px;
                font-size: 14px;
                min-width: 100px;
                max-width: 100px;
            }
        """
        
        self.cancel_btn = QPushButton("关闭")
        self.cancel_btn.setStyleSheet(button_style)
        self.cancel_btn.clicked.connect(self._on_cancel)
        footer_layout.addWidget(self.cancel_btn)
        
        self.apply_btn = QPushButton("应用提示词")
        self.apply_btn.setObjectName("secondaryButton")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setStyleSheet(button_style)
        self.apply_btn.clicked.connect(self._on_apply)
        footer_layout.addWidget(self.apply_btn)
        
        self.generate_btn = QPushButton("开始AI修改")
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.setStyleSheet(button_style + """
            QPushButton#primaryButton {
                background-color: #1890ff;
                color: white;
                border: none;
                font-weight: 500;
            }
            QPushButton#primaryButton:hover {
                background-color: #40a9ff;
            }
            QPushButton#primaryButton:disabled {
                background-color: #d9d9d9;
            }
        """)
        self.generate_btn.clicked.connect(self._on_generate)
        footer_layout.addWidget(self.generate_btn)
        
        main_layout.addWidget(footer)
    
    def _add_images(self):
        """添加图片"""
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
    
    def _append_image_item(self, path: str):
        """添加图片项到列表"""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            thumbnail = pixmap.scaled(
                120, 120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            icon = QIcon(thumbnail)
            item = QListWidgetItem(self.image_list)
            item.setIcon(icon)
            item.setText(os.path.basename(path))
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        else:
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(f"{path} (加载失败)")
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.image_list.addItem(item)
    
    def _remove_selected_images(self):
        """移除选中的图片"""
        for item in self.image_list.selectedItems():
            path = item.data(Qt.ItemDataRole.UserRole)
            self.selected_images = [p for p in self.selected_images if p != path]
            idx = self.image_list.row(item)
            self.image_list.takeItem(idx)
    
    def _clear_images(self):
        """清空所有图片"""
        self.selected_images.clear()
        self.image_list.clear()
    
    def _on_generate(self):
        """开始生成"""
        if self._is_generating:
            # 如果正在生成，点击变为取消
            self.ai_service.cancel()
            self._is_generating = False
            self._set_generating_ui(False)
            self.status_label.setText("已取消")
            return
        
        # 如果已有生成内容，添加确认提示
        if self._full_content and not self._is_generating:
            reply = QMessageBox.question(
                self,
                "确认重新生成",
                "已有生成结果，是否确定要重新生成？这将覆盖当前结果。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        # 检查配置
        if not self.ai_service.is_configured():
            QMessageBox.information(
                self,
                "未配置 API",
                "尚未配置 AI API，请在主界面点击「AI配置」按钮进行配置。"
            )
            return
        
        # 检查输入
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt and not self.selected_images:
            QMessageBox.warning(self, "提示", "请输入修改描述或上传参考图片")
            return
        
        # 清空输出并开始
        self.output_display.clear()
        self.compare_display.clear()
        self._full_content = ""
        self.diff_items = []
        self.diff_checkboxes = {}
        # 清空对比widget
        while self.compare_layout.count() > 1:
            item = self.compare_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._is_generating = True
        self._set_generating_ui(True)
        self.apply_btn.setEnabled(False)
        # 将应用按钮恢复为普通样式
        self.apply_btn.setObjectName("secondaryButton")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 24px;
                font-size: 14px;
                min-width: 100px;
                max-width: 100px;
            }
        """)
        self.result_stack.setCurrentIndex(0)  # 切换到流式输出视图
        
        # 准备当前JSON数据
        current_json = json.dumps(self.current_data, ensure_ascii=False, indent=2)
        
        # 传递图片路径列表
        image_paths = self.selected_images.copy() if self.selected_images else None
        
        self.ai_service.generate_modify_async(
            current_json,
            prompt,
            image_paths=image_paths,
            on_finished=self._on_generate_finished,
            on_error=self._on_generate_error,
            on_progress=self._on_generate_progress,
            on_stream_chunk=self._on_stream_chunk,
            on_stream_done=self._on_stream_done,
        )

    def _set_generating_ui(self, generating: bool):
        """设置生成中的UI状态"""
        self.prompt_input.setReadOnly(generating)
        self.add_image_btn.setEnabled(not generating)
        self.remove_image_btn.setEnabled(not generating)
        self.clear_image_btn.setEnabled(not generating)
        self.image_list.setEnabled(not generating)
        
        if generating:
            self.generate_btn.setText("停止")
            self.status_label.setText("修改中...")
            self.status_label.setStyleSheet("color: #2196F3; font-size: 12px;")
        else:
            self.generate_btn.setText("开始AI修改")
            self.status_label.setText("")

    def _on_generate_progress(self, message: str):
        """进度更新"""
        self.status_label.setText(message)

    def _on_stream_chunk(self, chunk: str):
        """接收流式内容块"""
        self._full_content += chunk
        # 在输出显示中追加内容
        cursor = self.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.output_display.setTextCursor(cursor)
        self.output_display.ensureCursorVisible()

    def _on_stream_done(self, content: str):
        """流式传输完成"""
        self._full_content = content
        self._is_generating = False
        self._set_generating_ui(False)
        self.status_label.setText("修改完成")
        self.status_label.setStyleSheet("color: #4CAF50; font-size: 12px;")
        
        # 尝试解析JSON验证有效性
        try:
            self.modified_data = json.loads(self._full_content)
            self.apply_btn.setEnabled(True)
            # 将应用按钮改为蓝色高亮样式
            self.apply_btn.setObjectName("primaryButton")
            self.apply_btn.setStyleSheet("""
                QPushButton {
                    padding: 10px 24px;
                    font-size: 14px;
                    min-width: 100px;
                    max-width: 100px;
                }
                QPushButton#primaryButton {
                    background-color: #1890ff;
                    color: white;
                    border: none;
                    font-weight: 500;
                }
                QPushButton#primaryButton:hover {
                    background-color: #40a9ff;
                }
                QPushButton#primaryButton:disabled {
                    background-color: #d9d9d9;
                }
            """)
            self.apply_btn.setFocus()
            # 显示差异对比
            self._show_differences()
            # 切换到对比视图
            self.result_stack.setCurrentIndex(1)
        except json.JSONDecodeError:
            self.status_label.setText("修改完成，但内容不是有效的JSON")
            self.status_label.setStyleSheet("color: #FF9800; font-size: 12px;")
            self.apply_btn.setEnabled(False)

    def _show_differences(self):
        """显示修改差异"""
        if not self.modified_data:
            return
        
        # 清空之前的差异项
        self.diff_items = []
        self.diff_checkboxes = {}
        
        # 收集差异
        self._compare_dicts(self.current_data, self.modified_data, [])
        
        if not self.diff_items:
            # 没有差异，显示提示信息
            self.result_stack.setCurrentIndex(2)  # 切换到文本显示
            self.compare_display.setHtml("<h3>没有检测到任何修改</h3>")
            return
        
        # 清空布局（保留最后的stretch）
        while self.compare_layout.count() > 1:
            item = self.compare_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 添加标题
        title = QLabel("以下字段已被修改，请选择要应用的更新：")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #262626; margin-bottom: 8px;")
        self.compare_layout.insertWidget(0, title)
        
        # 为每个差异项创建复选框
        for diff_item in self.diff_items:
            self._create_diff_item_widget(diff_item)
        
        # 切换到对比视图
        self.result_stack.setCurrentIndex(1)

    def _create_diff_item_widget(self, diff_item):
        """为差异项创建带复选框的widget"""
        path = diff_item['path']
        diff_type = diff_item['type']
        old_value = diff_item['old_value']
        new_value = diff_item['new_value']
        
        # 创建容器
        item_frame = QFrame()
        item_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        item_layout = QVBoxLayout(item_frame)
        item_layout.setContentsMargins(8, 8, 8, 8)
        item_layout.setSpacing(8)
        
        # 创建复选框和路径标签的横向布局
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        checkbox = QCheckBox()
        checkbox.setChecked(True)  # 默认选中
        checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.diff_checkboxes[path] = checkbox
        header_layout.addWidget(checkbox)
        
        # 根据类型显示不同的图标和颜色
        if diff_type == 'deleted':
            icon_text = "❌"
            path_style = "color: #d32f2f; font-weight: 600;"
        elif diff_type == 'added':
            icon_text = "➕"
            path_style = "color: #2e7d32; font-weight: 600;"
        else:  # modified
            icon_text = "🔄"
            path_style = "color: #1976d2; font-weight: 600;"
        
        path_label = QLabel(f"{icon_text} {path}")
        path_label.setStyleSheet(f"font-size: 14px; {path_style}")
        header_layout.addWidget(path_label)
        header_layout.addStretch()
        
        item_layout.addLayout(header_layout)
        
        # 显示旧值和新值
        if diff_type == 'deleted':
            old_label = QLabel(f"<span style='text-decoration: line-through; color: #888;'>{self._format_value_for_html(old_value)}</span>")
            old_label.setStyleSheet("font-size: 12px; color: #666; padding-left: 26px;")
            item_layout.addWidget(old_label)
        elif diff_type == 'added':
            new_label = QLabel(f"<span style='color: #2e7d32;'>{self._format_value_for_html(new_value)}</span>")
            new_label.setStyleSheet("font-size: 12px; color: #666; padding-left: 26px;")
            item_layout.addWidget(new_label)
        else:  # modified
            old_label = QLabel(f"<span style='text-decoration: line-through; color: #888;'>{self._format_value_for_html(old_value)}</span>")
            old_label.setStyleSheet("font-size: 12px; color: #666; padding-left: 26px;")
            item_layout.addWidget(old_label)
            
            new_label = QLabel(f"<span style='color: #2e7d32;'>{self._format_value_for_html(new_value)}</span>")
            new_label.setStyleSheet("font-size: 12px; color: #666; padding-left: 26px;")
            item_layout.addWidget(new_label)
        
        # 插入到stretch之前
        self.compare_layout.insertWidget(self.compare_layout.count() - 1, item_frame)

    def _compare_dicts(self, old_dict, new_dict, key_path):
        """递归比较两个字典的差异，返回结构化的差异列表"""
        all_keys = set(old_dict.keys()) | set(new_dict.keys())
        
        for key in all_keys:
            current_key_path = key_path + [key]
            current_path = ".".join(current_key_path)
            
            # 如果键只存在于旧字典中
            if key not in new_dict:
                old_value = old_dict[key]
                self.diff_items.append({
                    'path': current_path,
                    'type': 'deleted',
                    'old_value': old_value,
                    'new_value': None,
                    'key_path': current_key_path
                })
                continue
                
            # 如果键只存在于新字典中
            if key not in old_dict:
                new_value = new_dict[key]
                self.diff_items.append({
                    'path': current_path,
                    'type': 'added',
                    'old_value': None,
                    'new_value': new_value,
                    'key_path': current_key_path
                })
                continue
                
            # 如果键在两个字典中都存在
            old_value = old_dict[key]
            new_value = new_dict[key]
            
            # 如果都是字典，递归比较
            if isinstance(old_value, dict) and isinstance(new_value, dict):
                self._compare_dicts(old_value, new_value, current_key_path)
            # 如果值不同
            elif old_value != new_value:
                self.diff_items.append({
                    'path': current_path,
                    'type': 'modified',
                    'old_value': old_value,
                    'new_value': new_value,
                    'key_path': current_key_path
                })

    def _format_value(self, value):
        """格式化值用于显示"""
        if isinstance(value, str) and len(value) > 50:
            return value[:50] + "..."
        return str(value)
    
    def _format_value_for_html(self, value):
        """格式化值用于HTML显示"""
        if isinstance(value, str):
            # 转义HTML特殊字符
            value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if len(value) > 100:
                return value[:100] + "..."
            return value
        elif isinstance(value, list):
            if len(value) > 5:
                return ", ".join(str(x) for x in value[:5]) + f" ... (共{len(value)}项)"
            return ", ".join(str(x) for x in value)
        elif isinstance(value, dict):
            return f"{{对象，包含 {len(value)} 个字段}}"
        else:
            return str(value)
    
    def _apply_selected_differences(self, base_data: dict, modified_data: dict) -> dict:
        """根据选中的差异应用更新"""
        result = json.loads(json.dumps(base_data))  # 深拷贝
        
        for diff_item in self.diff_items:
            path = diff_item['path']
            checkbox = self.diff_checkboxes.get(path)
            
            # 如果复选框未选中，跳过
            if not checkbox or not checkbox.isChecked():
                continue
            
            # 获取新值
            new_value = diff_item['new_value']
            key_path = diff_item['key_path']
            
            # 如果是删除操作，跳过（删除操作需要特殊处理）
            if diff_item['type'] == 'deleted':
                continue
            
            # 导航到目标位置并设置新值
            current = result
            for i, key in enumerate(key_path[:-1]):
                if key not in current:
                    # 如果键不存在，创建空字典（用于新增的嵌套结构）
                    current[key] = {}
                elif not isinstance(current[key], dict):
                    # 如果键存在但不是字典，需要替换为字典（这种情况应该很少见）
                    current[key] = {}
                current = current[key]
            
            # 设置新值
            final_key = key_path[-1]
            if diff_item['type'] == 'added' or diff_item['type'] == 'modified':
                current[final_key] = json.loads(json.dumps(new_value))  # 深拷贝
        
        # 处理删除操作
        for diff_item in self.diff_items:
            if diff_item['type'] != 'deleted':
                continue
            
            path = diff_item['path']
            checkbox = self.diff_checkboxes.get(path)
            
            if not checkbox or not checkbox.isChecked():
                continue
            
            key_path = diff_item['key_path']
            
            # 导航到目标位置并删除
            current = result
            try:
                for i, key in enumerate(key_path[:-1]):
                    if key not in current or not isinstance(current[key], dict):
                        break
                    current = current[key]
                else:
                    # 成功导航到父级，删除目标键
                    final_key = key_path[-1]
                    if final_key in current:
                        del current[final_key]
            except (KeyError, TypeError):
                # 如果路径不存在或类型不匹配，忽略删除操作
                pass
        
        return result

    def _on_generate_finished(self, data: dict):
        """生成完成"""
        self.modified.emit(data)
        self.accept()

    def _on_generate_error(self, error_msg: str):
        """生成出错"""
        self._is_generating = False
        self._set_generating_ui(False)
        self.status_label.setText(f"错误: {error_msg}")
        self.status_label.setStyleSheet("color: #F44336; font-size: 12px;")
        QMessageBox.critical(self, "AI生成错误", error_msg)

    def _on_apply(self):
        """应用修改结果"""
        try:
            if not self.modified_data:
                if self._full_content:
                    self.modified_data = json.loads(self._full_content)
                else:
                    QMessageBox.critical(self, "错误", "没有有效的修改数据可应用")
                    return
            
            # 如果有差异项，只应用选中的差异
            if self.diff_items:
                final_data = self._apply_selected_differences(self.current_data, self.modified_data)
                self.modified.emit(final_data)
            else:
                # 没有差异，直接应用全部
                self.modified.emit(self.modified_data)
            
            self.accept()
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "错误", f"JSON格式错误:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用修改时出错:\n{str(e)}")

    def _on_cancel(self):
        """取消/关闭对话框"""
        if self._is_generating:
            self.ai_service.cancel()
        self.reject()
