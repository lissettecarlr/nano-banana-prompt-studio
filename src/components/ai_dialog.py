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
        self.model_input.setPlaceholderText("gpt-4o-mini")
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
        self.url_input.setText(config.get("base_url", ""))
        self.key_input.setText(config.get("api_key", ""))
        self.model_input.setText(config.get("model", ""))
    
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
        
        if not base_url:
            base_url = "https://api.openai.com/v1"
        
        if not model:
            model = "gpt-4o-mini"
        
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
        
        # 配置状态提示
        self.config_status = QLabel()
        self.config_status.setStyleSheet(
            "font-size: 12px; padding: 4px 12px; border-radius: 12px; "
            "background-color: #e6f7ff; color: #0958d9;"
        )
        self.config_status.hide()  # 隐藏模型URL/模型名显示
        header.addWidget(self.config_status)
        self._update_config_status()
        
        # 配置按钮
        self.config_btn = QPushButton("⚙ 配置")
        self.config_btn.setStyleSheet("""
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
        self.config_btn.clicked.connect(self._show_config)
        header.addWidget(self.config_btn)
        
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
        
        input_label = QLabel("📝 描述你想要的画面")
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
        output_label = QLabel("✨ AI 生成结果")
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
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
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
        
        self.apply_btn = QPushButton("应用到表单")
        self.apply_btn.setObjectName("secondaryButton")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setStyleSheet(button_style)
        self.apply_btn.clicked.connect(self._on_apply)
        footer_layout.addWidget(self.apply_btn)
        
        self.generate_btn = QPushButton("生成")
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
    
    def _update_config_status(self):
        """更新配置状态显示"""
        if self.ai_service.is_configured():
            config = self.config_manager.load_config()
            model = config.get("model", "未知")
            base_url = config.get("base_url", "")
            # 简化显示
            if "openai.com" in base_url:
                provider = "OpenAI"
            elif "deepseek" in base_url:
                provider = "DeepSeek"
            elif "dashscope" in base_url:
                provider = "通义千问"
            else:
                provider = base_url.split("//")[-1].split("/")[0]
            self.config_status.setText(f"✓ {provider} / {model}")
            self.config_status.setStyleSheet(
                "font-size: 12px; padding: 4px 12px; border-radius: 12px; "
                "background-color: #f6ffed; color: #52c41a; font-weight: 500;"
            )
        else:
            self.config_status.setText("⚠ 未配置")
            self.config_status.setStyleSheet(
                "font-size: 12px; padding: 4px 12px; border-radius: 12px; "
                "background-color: #fff7e6; color: #fa8c16; font-weight: 500;"
            )
    
    def _show_config(self):
        """显示配置对话框"""
        dialog = AIConfigDialog(self)
        dialog.config_saved.connect(self._update_config_status)
        dialog.exec()
    
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
        self.config_btn.setEnabled(not generating)
        self.add_image_btn.setEnabled(not generating)
        self.remove_image_btn.setEnabled(not generating)
        self.clear_image_btn.setEnabled(not generating)
        self.image_list.setEnabled(not generating)
        
        if generating:
            self.generate_btn.setText("停止")
            self.status_label.setText("生成中...")
            self.status_label.setStyleSheet("color: #2196F3; font-size: 12px;")
        else:
            self.generate_btn.setText("生成")
    
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
        
        # 配置状态提示
        self.config_status = QLabel()
        self.config_status.setStyleSheet(
            "font-size: 12px; padding: 4px 12px; border-radius: 12px; "
            "background-color: #e6f7ff; color: #0958d9;"
        )
        self.config_status.hide()  # 隐藏模型URL/模型名显示
        header.addWidget(self.config_status)
        self._update_config_status()
        
        # 配置按钮
        self.config_btn = QPushButton("⚙ 配置")
        self.config_btn.setStyleSheet("""
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
        self.config_btn.clicked.connect(self._show_config)
        header.addWidget(self.config_btn)
        
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
        
        input_label = QLabel("📝 描述你想要的修改")
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
        output_label = QLabel("✨ AI 修改结果")
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
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
                border-radius: 6px;
                padding: 12px;
                min-height: 400px;
            }
        """)
        self.result_stack.addWidget(self.output_display)
        
        # 对比结果显示
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
        
        self.apply_btn = QPushButton("应用到表单")
        self.apply_btn.setObjectName("secondaryButton")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setStyleSheet(button_style)
        self.apply_btn.clicked.connect(self._on_apply)
        footer_layout.addWidget(self.apply_btn)
        
        self.generate_btn = QPushButton("修改")
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
    
    def _update_config_status(self):
        """更新配置状态显示"""
        if self.ai_service.is_configured():
            config = self.config_manager.load_config()
            model = config.get("model", "未知")
            base_url = config.get("base_url", "")
            # 简化显示
            if "openai.com" in base_url:
                provider = "OpenAI"
            elif "deepseek" in base_url:
                provider = "DeepSeek"
            elif "dashscope" in base_url:
                provider = "通义千问"
            else:
                provider = base_url.split("//")[-1].split("/")[0]
            self.config_status.setText(f"✓ {provider} / {model}")
            self.config_status.setStyleSheet(
                "font-size: 12px; padding: 4px 12px; border-radius: 12px; "
                "background-color: #f6ffed; color: #52c41a; font-weight: 500;"
            )
        else:
            self.config_status.setText("⚠ 未配置")
            self.config_status.setStyleSheet(
                "font-size: 12px; padding: 4px 12px; border-radius: 12px; "
                "background-color: #fff7e6; color: #fa8c16; font-weight: 500;"
            )
    
    def _show_config(self):
        """显示配置对话框"""
        dialog = AIConfigDialog(self)
        dialog.config_saved.connect(self._update_config_status)
        dialog.exec()

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
            QMessageBox.warning(self, "提示", "请输入修改描述或上传参考图片")
            return
        
        # 清空输出并开始
        self.output_display.clear()
        self.compare_display.clear()
        self._full_content = ""
        self._is_generating = True
        self._set_generating_ui(True)
        self.apply_btn.setEnabled(False)
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
        self.config_btn.setEnabled(not generating)
        self.add_image_btn.setEnabled(not generating)
        self.remove_image_btn.setEnabled(not generating)
        self.clear_image_btn.setEnabled(not generating)
        self.image_list.setEnabled(not generating)
        
        if generating:
            self.generate_btn.setText("停止")
            self.status_label.setText("修改中...")
            self.status_label.setStyleSheet("color: #2196F3; font-size: 12px;")
        else:
            self.generate_btn.setText("修改")
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
            
        differences = []
        self._compare_dicts(self.current_data, self.modified_data, differences, "")
        
        if differences:
            diff_text = "<h3>以下字段已被修改：</h3><hr>"
            diff_text += "<br>".join(differences)
        else:
            diff_text = "<h3>没有检测到任何修改</h3>"
            
        self.compare_display.setHtml(diff_text)

    def _compare_dicts(self, old_dict, new_dict, differences, path):
        """递归比较两个字典的差异"""
        all_keys = set(old_dict.keys()) | set(new_dict.keys())
        
        for key in all_keys:
            current_path = f"{path}.{key}" if path else key
            
            # 如果键只存在于旧字典中
            if key not in new_dict:
                old_value = old_dict[key]
                if isinstance(old_value, dict):
                    differences.append(f'<div><strong>❌ {current_path}</strong>: [整个对象被删除]</div>')
                else:
                    differences.append(f'<div><strong>❌ {current_path}</strong>: <span style="text-decoration: line-through; color: #888;">{self._format_value(old_value)}</span></div>')
                continue
                
            # 如果键只存在于新字典中
            if key not in old_dict:
                new_value = new_dict[key]
                if isinstance(new_value, dict):
                    differences.append(f'<div><strong>➕ {current_path}</strong>: [新增对象]</div>')
                else:
                    differences.append(f'<div><strong>➕ {current_path}</strong>: <span style="color: #2E7D32;">{self._format_value(new_value)}</span></div>')
                continue
                
            # 如果键在两个字典中都存在
            old_value = old_dict[key]
            new_value = new_dict[key]
            
            # 如果都是字典，递归比较
            if isinstance(old_value, dict) and isinstance(new_value, dict):
                self._compare_dicts(old_value, new_value, differences, current_path)
            # 如果值不同
            elif old_value != new_value:
                if isinstance(old_value, list) and isinstance(new_value, list):
                    old_str = ", ".join(str(x) for x in old_value)
                    new_str = ", ".join(str(x) for x in new_value)
                    differences.append(f'<div><strong>🔄 {current_path}</strong>:<br>'
                                      f'<span style="text-decoration: line-through; color: #888;">&nbsp;&nbsp;{old_str}</span><br>'
                                      f'<span style="color: #2E7D32;">&nbsp;&nbsp;{new_str}</span></div>')
                else:
                    differences.append(f'<div><strong>🔄 {current_path}</strong>:<br>'
                                      f'<span style="text-decoration: line-through; color: #888;">&nbsp;&nbsp;{self._format_value(old_value)}</span><br>'
                                      f'<span style="color: #2E7D32;">&nbsp;&nbsp;{self._format_value(new_value)}</span></div>')

    def _format_value(self, value):
        """格式化值用于显示"""
        if isinstance(value, str) and len(value) > 50:
            return value[:50] + "..."
        return str(value)

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
            if self.modified_data:
                self.modified.emit(self.modified_data)
                self.accept()
            elif self._full_content:
                data = json.loads(self._full_content)
                self.modified.emit(data)
                self.accept()
            else:
                QMessageBox.critical(self, "错误", "没有有效的修改数据可应用")
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "错误", f"JSON格式错误:\n{str(e)}")

    def _on_cancel(self):
        """取消/关闭对话框"""
        if self._is_generating:
            self.ai_service.cancel()
        self.reject()
