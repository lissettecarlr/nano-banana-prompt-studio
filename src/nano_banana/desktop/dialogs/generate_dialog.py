"""AI 生成提示词对话框。"""
import os
from typing import List
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QFrame,
    QWidget,
    QMessageBox,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QKeySequence, QPixmap

from nano_banana.core import PromptEvent, Studio
from nano_banana.desktop.dialogs.config_dialog import UnifiedAIConfigDialog
from nano_banana.desktop.workers import PromptService
from nano_banana.desktop.window_utils import (
    extract_image_paths,
    fit_window_to_screen,
    get_last_dir,
    remember_last_dir,
    save_clipboard_image,
)


class AIGenerateDialog(QDialog):
    """AI生成提示词对话框 - 流式输出版"""
    
    # 生成完成信号，传递生成的数据
    generated = pyqtSignal(dict)
    
    def __init__(self, studio: Studio, parent=None):
        super().__init__(parent)
        self.studio = studio
        self.prompt_service = PromptService(studio)
        self._is_generating = False
        self._full_content = ""
        self._result: PromptEvent | None = None
        self.selected_images: List[str] = []
        self._setup_ui()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if extract_image_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        paths = extract_image_paths(event.mimeData())
        if paths:
            self._add_image_paths(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def keyPressEvent(self, event):
        # 焦点不在文本框时 Ctrl+V 粘贴剪贴板图片
        if event.matches(QKeySequence.StandardKey.Paste):
            path = save_clipboard_image()
            if path:
                self._add_image_paths([path])
                return
        super().keyPressEvent(event)

    def _setup_ui(self):
        self.setWindowTitle("AI 生成提示词")
        fit_window_to_screen(self, 1100, 750, min_width=900, min_height=620)
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
            get_last_dir("reference"),
            "图像文件 (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not files:
            return
        remember_last_dir(files[0], "reference")
        self._add_image_paths(files)

    def _add_image_paths(self, paths: List[str]):
        """拖拽/粘贴/文件对话框共用的添加入口。"""
        remaining = 3 - len(self.selected_images)
        if remaining <= 0:
            self.status_label.setText("最多只能选择 3 张参考图")
            return
        for path in paths[:remaining]:
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

    def _show_config(self):
        """打开独立的 AI 对话配置页。"""
        dialog = UnifiedAIConfigDialog(self.studio, self, initial_tab="chat")
        dialog.exec()
    
    def _on_generate(self):
        """开始生成"""
        if self._is_generating:
            # 如果正在生成，点击变为取消
            self.prompt_service.cancel()
            self._is_generating = False
            self._set_generating_ui(False)
            self.status_label.setText("已取消")
            return
        
        # 检查配置
        if not self.prompt_service.is_configured():
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
        
        self._result = None
        self.prompt_service.generate(
            prompt,
            self.selected_images,
            on_result=self._on_result,
            on_error=self._on_generate_error,
            on_progress=self._on_generate_progress,
            on_chunk=self._on_stream_chunk,
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
    
    def _on_result(self, event: PromptEvent):
        """生成结束：event.document 是 Studio 解析并升级好的文档。"""
        self._is_generating = False
        self._set_generating_ui(False)
        self._result = event
        self._full_content = event.text
        if event.document is None:
            self.status_label.setText("生成完成，但内容不是有效的JSON")
            self.status_label.setStyleSheet("color: #FF9800; font-size: 12px;")
        else:
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

    def _on_generate_error(self, error: str):
        """生成错误"""
        self._is_generating = False
        self._set_generating_ui(False)
        self.status_label.setText(f"错误: {error}")
        self.status_label.setStyleSheet("color: #F44336; font-size: 12px;")
    
    def _on_apply(self):
        """应用生成的内容到表单"""
        if self._result is None or not self._full_content.strip():
            QMessageBox.warning(self, "提示", "没有可应用的内容")
            return
        if self._result.document is None:
            QMessageBox.warning(
                self,
                "JSON解析失败",
                f"AI返回的内容不是有效的JSON格式:\n{self._result.parse_error}\n\n"
                "你可以手动复制内容进行修改。",
            )
            return
        self.generated.emit(self._result.document)
        self.accept()

    def _on_cancel(self):
        """关闭按钮点击"""
        if self._is_generating:
            self.prompt_service.cancel()
        self.reject()
    
    def closeEvent(self, event):
        """关闭事件"""
        if self._is_generating:
            self.prompt_service.cancel()
        super().closeEvent(event)
