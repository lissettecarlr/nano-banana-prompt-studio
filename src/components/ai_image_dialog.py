"""AI 生图对话框"""

import os
from io import BytesIO
from typing import List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from utils.ai_config import AIConfigManager
from components.gemini_client import (
    ASPECT_RATIO_LIST,
    IMAGE_SIZE_LIST,
    THINKING_LEVEL_LIST,
    GeminiClient,
)


class GeminiImageThread(QThread):
    """后台线程：调用 Gemini 接口生成图片"""

    image_ready = pyqtSignal(bytes)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(
        self,
        prompt: str,
        image_paths: List[str],
        aspect_ratio: str,
        image_size: str,
        thinking_level: str,
    ):
        super().__init__()
        self.prompt = prompt
        self.image_paths = image_paths
        self.aspect_ratio = aspect_ratio
        self.image_size = image_size
        self.thinking_level = thinking_level

    def run(self):
        try:
            self.progress.emit("正在初始化 Gemini 客户端...")
            config_manager = AIConfigManager()
            gemini_config = config_manager.get_gemini_config()

            base_url = (gemini_config.get("base_url") or "").strip()
            api_key = (gemini_config.get("api_key") or "").strip()
            model = (gemini_config.get("model") or "gemini-3-pro-image-preview").strip() or "gemini-3-pro-image-preview"

            if not base_url or not api_key:
                self.error.emit("请先在配置中填写 Gemini Base URL 和 API Key")
                return

            client = GeminiClient(
                base_url=base_url,
                api_key=api_key,
                image_model=model,
            )
            client.set_aspect_ratio(self.aspect_ratio)
            client.set_image_size(self.image_size)
            client.set_thinking_level(self.thinking_level)

            self.progress.emit("正在生成图片...")
            image = client.generate_image(
                text=self.prompt,
                images=self.image_paths if self.image_paths else None,
            )
            if image is None:
                self.error.emit("未生成图片，请尝试调整提示词或参数")
                return

            buffer = BytesIO()
            image.save(buffer, format="PNG")
            self.image_ready.emit(buffer.getvalue())
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class GeminiImageConfigDialog(QDialog):
    """Gemini API 配置对话框"""

    config_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = AIConfigManager()
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        self.setWindowTitle("Gemini API 配置")
        self.setMinimumWidth(500)
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
            QTextEdit {
                padding: 8px;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                background-color: white;
            }
            QTextEdit:focus {
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

        # 标题区域
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)
        
        title = QLabel("⚙ Gemini API 配置")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #262626;")
        title_layout.addWidget(title)
        
        info = QLabel("请填写 Gemini 接口地址与密钥")
        info.setWordWrap(True)
        info.setStyleSheet("color: #8c8c8c; font-size: 13px;")
        title_layout.addWidget(info)
        
        layout.addWidget(title_container)

        # 表单容器
        form_frame = QFrame()
        form_frame.setStyleSheet(
            "background-color: #ffffff; border: 1px solid #e8e8e8; "
            "border-radius: 12px; padding: 4px;"
        )
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(18)

        self.base_url_input = QComboBox()
        self.base_url_input.setEditable(True)
        self.base_url_input.addItems([
            "https://generativelanguage.googleapis.com",
        ])
        form_layout.addWidget(self._build_labeled_widget("Base URL", self.base_url_input))

        self.api_key_input = QTextEdit()
        self.api_key_input.setFixedHeight(70)
        self.api_key_input.setPlaceholderText("sk-...")
        form_layout.addWidget(self._build_labeled_widget("API Key", self.api_key_input))

        self.model_input = QComboBox()
        self.model_input.setEditable(True)
        self.model_input.addItems([
            "gemini-3-pro-image-preview",
            "gemini-2.0-flash-exp",
        ])
        form_layout.addWidget(self._build_labeled_widget("模型名称", self.model_input))

        layout.addWidget(form_frame)

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

    def _build_labeled_widget(self, label_text: str, widget: QWidget) -> QWidget:
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
        config = self.config_manager.get_gemini_config()
        self.base_url_input.setCurrentText(config.get("base_url", ""))
        self.api_key_input.setPlainText(config.get("api_key", ""))
        self.model_input.setCurrentText(config.get("model", ""))

    def _save_config(self):
        base_url = self.base_url_input.currentText().strip()
        api_key = self.api_key_input.toPlainText().strip()
        model = self.model_input.currentText().strip() or "gemini-3-pro-image-preview"

        if not api_key:
            QMessageBox.warning(self, "提示", "请输入 Gemini API Key")
            return

        payload = {
            "gemini_base_url": base_url,
            "gemini_api_key": api_key,
            "gemini_model": model,
        }

        if self.config_manager.save_config(payload):
            self.config_saved.emit()
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "保存配置失败，请重试")


class AIImageGenerateDialog(QDialog):
    """AI 生图交互对话框"""

    def __init__(self, default_prompt: str, parent=None):
        super().__init__(parent)
        self.config_manager = AIConfigManager()
        self.selected_images: List[str] = []
        self.generated_image_bytes: Optional[bytes] = None
        self.generated_pixmap: Optional[QPixmap] = None
        self.worker_thread: Optional[GeminiImageThread] = None
        self.prompt_text = (default_prompt or "").strip()

        self._setup_ui()
        self._update_config_status()

    def _setup_ui(self):
        self.setWindowTitle("AI 生图")
        self.setModal(True)
        self.resize(1100, 750)
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
            QComboBox {
                padding: 6px 12px;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                background-color: white;
                min-height: 28px;
            }
            QComboBox:hover {
                border-color: #40a9ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
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
        
        title = QLabel("Gemini AI 文生图")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #262626;")
        title_layout.addWidget(title)
        
        subtitle = QLabel("使用 banana pro生成图片")
        subtitle.setStyleSheet("font-size: 13px; color: #8c8c8c;")
        title_layout.addWidget(subtitle)
        
        header.addWidget(title_container)
        header.addStretch()

        self.config_status_label = QLabel()
        self.config_status_label.setStyleSheet(
            "font-size: 12px; padding: 4px 12px; border-radius: 12px; "
            "background-color: #e6f7ff; color: #0958d9;"
        )
        self.config_status_label.hide()  # 隐藏模型URL/模型名显示
        header.addWidget(self.config_status_label)

        config_btn = QPushButton("⚙ 配置")
        config_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 16px;
                background-color: #fafafa;
                border: 1px solid #d9d9d9;
            }
            QPushButton:hover {
                background-color: #ffffff;
                border-color: #1890ff;
            }
        """)
        config_btn.clicked.connect(self._open_config_dialog)
        header.addWidget(config_btn)

        main_layout.addLayout(header)

        # 提示信息
        prompt_hint = QLabel("修改提示词请关闭此界面，在主界面进行修改")
        prompt_hint.setStyleSheet(
            "color: #096dd9; background-color: #e6f7ff; border: 1px solid #91d5ff;"
            "border-radius: 8px; padding: 10px 16px; font-size: 13px;"
        )
        main_layout.addWidget(prompt_hint)

        # 左右分栏布局
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # 左侧：参数和控制区
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        left_panel.setMaximumWidth(400)
        left_panel.setMinimumWidth(350)

        # 参数设置区
        param_frame = QFrame()
        param_frame.setObjectName("paramFrame")
        param_frame.setStyleSheet(
            "QFrame#paramFrame {"
            "  background-color: #ffffff;"
            "  border: 1px solid #e8e8e8;"
            "  border-radius: 12px;"
            "}"
        )
        param_layout = QVBoxLayout(param_frame)
        param_layout.setContentsMargins(20, 20, 20, 20)
        param_layout.setSpacing(16)

        param_title = QLabel("⚡ 生成参数")
        param_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #262626;")
        param_layout.addWidget(param_title)

        # 宽高比
        aspect_container = self._create_param_row("宽高比", ASPECT_RATIO_LIST)
        self.aspect_combo = aspect_container.findChild(QComboBox)
        param_layout.addWidget(aspect_container)

        # 输出尺寸
        size_container = self._create_param_row("输出尺寸", IMAGE_SIZE_LIST)
        self.size_combo = size_container.findChild(QComboBox)
        param_layout.addWidget(size_container)

        # 思考级别
        thinking_container = self._create_param_row("思考级别", THINKING_LEVEL_LIST, default="low")
        self.thinking_combo = thinking_container.findChild(QComboBox)
        param_layout.addWidget(thinking_container)

        left_layout.addWidget(param_frame)

        # 参考图片区
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
        img_label = QLabel("🖼 参考图片")
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

        # 右侧：预览区
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        preview_frame = QFrame()
        preview_frame.setObjectName("previewFrame")
        preview_frame.setStyleSheet(
            "QFrame#previewFrame {"
            "  background-color: #ffffff;"
            "  border: 1px solid #e8e8e8;"
            "  border-radius: 12px;"
            "}"
        )
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(20, 20, 20, 20)
        preview_layout.setSpacing(12)

        preview_title = QLabel("生成预览")
        preview_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #262626;")
        preview_layout.addWidget(preview_title)

        # 预览画布
        preview_canvas = QFrame()
        preview_canvas.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 #fafafa, stop:1 #f0f0f0); "
            "border: 2px dashed #d9d9d9; border-radius: 8px;"
        )
        canvas_layout = QVBoxLayout(preview_canvas)
        canvas_layout.setContentsMargins(20, 20, 20, 20)

        self.preview_area = QLabel("图片生成后会显示在这里")
        self.preview_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_area.setMinimumHeight(400)
        self.preview_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_area.setStyleSheet("color: #bfbfbf; font-size: 14px; border: none;")
        canvas_layout.addWidget(self.preview_area)

        preview_layout.addWidget(preview_canvas, 1)

        right_layout.addWidget(preview_frame, 1)

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

        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("color: #595959; font-size: 13px;")
        footer_layout.addWidget(self.status_label)
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
        
        self.save_btn = QPushButton("保存图片")
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet(button_style)
        self.save_btn.clicked.connect(self._save_image)
        footer_layout.addWidget(self.save_btn)

        self.generate_btn = QPushButton("生成图片")
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
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        footer_layout.addWidget(self.generate_btn)

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(button_style)
        close_btn.clicked.connect(self._handle_close_clicked)
        footer_layout.addWidget(close_btn)

        main_layout.addWidget(footer)

    def _create_param_row(self, label_text: str, items: list, default: str = None) -> QWidget:
        """创建参数行"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 13px; color: #595959; min-width: 70px;")
        layout.addWidget(label)

        combo = QComboBox()
        combo.addItems(items)
        if default:
            combo.setCurrentText(default)
        layout.addWidget(combo, 1)

        return container

    def _update_config_status(self):
        api_key = self.config_manager.get_gemini_api_key()
        base_url = self.config_manager.get_gemini_base_url()
        if api_key:
            provider = base_url.split("/")[2] if base_url and "/" in base_url else "已配置"
            self.config_status_label.setText(f"✓ {provider}")
            self.config_status_label.setStyleSheet(
                "font-size: 12px; padding: 4px 12px; border-radius: 12px; "
                "background-color: #f6ffed; color: #52c41a; font-weight: 500;"
            )
        else:
            self.config_status_label.setText("⚠ 未配置")
            self.config_status_label.setStyleSheet(
                "font-size: 12px; padding: 4px 12px; border-radius: 12px; "
                "background-color: #fff7e6; color: #fa8c16; font-weight: 500;"
            )

    def _open_config_dialog(self):
        dialog = GeminiImageConfigDialog(self)
        dialog.config_saved.connect(self._update_config_status)
        dialog.exec()

    def _add_images(self):
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
        # 加载图片并创建缩略图
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            # 创建 120x120 的缩略图，保持宽高比
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
            # 设置文本居中显示在图标下方
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        else:
            # 如果图片加载失败，仍然添加一个文本项
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(f"{path} (加载失败)")
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.image_list.addItem(item)

    def _remove_selected_images(self):
        for item in self.image_list.selectedItems():
            path = item.data(Qt.ItemDataRole.UserRole)
            self.selected_images = [p for p in self.selected_images if p != path]
            idx = self.image_list.row(item)
            self.image_list.takeItem(idx)

    def _clear_images(self):
        self.selected_images.clear()
        self.image_list.clear()

    def _on_generate_clicked(self):
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.information(self, "提示", "已有任务进行中，请稍候")
            return

        prompt = (self.prompt_text or "").strip()
        if not prompt:
            QMessageBox.warning(self, "提示", "当前提示词为空，请先在主界面填写内容")
            return

        if not self.config_manager.get_gemini_api_key():
            reply = QMessageBox.question(
                self,
                "未配置 API",
                "尚未配置 Gemini API，是否现在配置？",
                QMessageBox.StandardButton.Yes,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._open_config_dialog()
            return

        self.generated_image_bytes = None
        self.generated_pixmap = None
        self.preview_area.setText("正在生成，请稍候...")
        self.preview_area.setPixmap(QPixmap())
        self.save_btn.setEnabled(False)
        self._set_generating_state(True)
        self._set_status("提交到 Gemini 服务", "#1890ff")

        self.worker_thread = GeminiImageThread(
            prompt=prompt,
            image_paths=self.selected_images,
            aspect_ratio=self.aspect_combo.currentText(),
            image_size=self.size_combo.currentText(),
            thinking_level=self.thinking_combo.currentText(),
        )
        self.worker_thread.progress.connect(lambda msg: self._set_status(f"⏳ {msg}", "#1890ff"))
        self.worker_thread.image_ready.connect(self._on_image_ready)
        self.worker_thread.error.connect(self._on_generation_error)
        self.worker_thread.finished.connect(self._on_thread_finished)
        self.worker_thread.start()

    def _on_thread_finished(self):
        self._set_generating_state(False)
        self.worker_thread = None

    def _on_image_ready(self, image_bytes: bytes):
        self.generated_image_bytes = image_bytes
        pixmap = QPixmap.fromImage(QImage.fromData(image_bytes))
        self.generated_pixmap = pixmap
        self._refresh_preview_pixmap()
        self.save_btn.setEnabled(True)
        self._set_status("生成完成", "#52c41a")

    def _on_generation_error(self, message: str):
        self._set_status(f"生成失败：{message}", "#ff4d4f")
        self.preview_area.setText("生成失败，请调整参数后重试")

    def _set_generating_state(self, generating: bool):
        self.aspect_combo.setEnabled(not generating)
        self.size_combo.setEnabled(not generating)
        self.thinking_combo.setEnabled(not generating)
        self.image_list.setEnabled(not generating)
        self.add_image_btn.setEnabled(not generating)
        self.remove_image_btn.setEnabled(not generating)
        self.clear_image_btn.setEnabled(not generating)
        self.generate_btn.setEnabled(not generating)

    def _save_image(self):
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

        suffix = os.path.splitext(file_path)[1].lower()
        format_name = "PNG" if suffix in ("", ".png") else "JPEG"
        image = QImage.fromData(self.generated_image_bytes)
        if not image.save(file_path, format_name):
            QMessageBox.critical(self, "错误", "保存图片失败，请重试")
        else:
            self._set_status(f"图片已保存到 {file_path}", "#52c41a")

    def _set_status(self, text: str, color: str = "#757575"):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    def _handle_close_clicked(self):
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.information(self, "提示", "图片生成中，请等待完成")
            return
        self.reject()

    def _refresh_preview_pixmap(self):
        if not self.generated_pixmap:
            self.preview_area.setPixmap(QPixmap())
            return
        scaled = self.generated_pixmap.scaled(
            self.preview_area.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_area.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_preview_pixmap()

    def closeEvent(self, event):
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.information(self, "提示", "图片生成中，请等待完成")
            event.ignore()
            return
        super().closeEvent(event)
