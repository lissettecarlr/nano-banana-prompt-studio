"""AI 修改提示词对话框。"""
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
    QStackedWidget,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QKeySequence, QPixmap

from nano_banana.core import Change, PromptEvent, Studio
from nano_banana.desktop.workers import PromptService
from nano_banana.desktop.window_utils import (
    extract_image_paths,
    fit_window_to_screen,
    get_last_dir,
    remember_last_dir,
    save_clipboard_image,
)


class AIModifyDialog(QDialog):
    """AI修改提示词对话框 - 流式输出版"""
    
    # 修改完成信号，传递修改后的数据
    modified = pyqtSignal(dict)
    
    def __init__(self, studio: Studio, current_data: dict, parent=None):
        super().__init__(parent)
        self.studio = studio
        self.current_data = current_data  # 完整文档（含特别要求、线稿等 overlay）
        self.prompt_service = PromptService(studio)
        self._is_generating = False
        self._full_content = ""
        self._result: PromptEvent | None = None
        self.selected_images: List[str] = []
        self.diff_items: List[Change] = []  # Studio 算好的差异
        self.diff_checkboxes: List[QCheckBox] = []  # 与 diff_items 一一对应
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
        self.setWindowTitle("AI 修改提示词")
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
    
    def _on_generate(self):
        """开始生成"""
        if self._is_generating:
            # 如果正在生成，点击变为取消
            self.prompt_service.cancel()
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
        if not self.prompt_service.is_configured():
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
        self._result = None
        self.diff_items = []
        self.diff_checkboxes = []
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
        
        # 文档原样交给 Studio：哪些部分给模型看、怎么序列化由核心决定
        self.prompt_service.modify(
            self.current_data,
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

    def _on_result(self, event: PromptEvent):
        """修改结束：event.document 是解析好的新文档，event.changes 是相对原文档的差异。"""
        self._result = event
        self._full_content = event.text
        self._is_generating = False
        self._set_generating_ui(False)

        if event.document is None:
            self.status_label.setText("修改完成，但内容不是有效的JSON")
            self.status_label.setStyleSheet("color: #FF9800; font-size: 12px;")
            self.apply_btn.setEnabled(False)
            return

        self.status_label.setText("修改完成")
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
        self.apply_btn.setFocus()
        self._show_differences(list(event.changes))

    def _show_differences(self, changes: List[Change]):
        """显示修改差异"""
        self.diff_items = changes
        self.diff_checkboxes = []

        if not changes:
            self.result_stack.setCurrentIndex(2)  # 切换到文本显示
            self.compare_display.setHtml("<h3>没有检测到任何修改</h3>")
            return

        # 清空布局（保留最后的stretch）
        while self.compare_layout.count() > 1:
            item = self.compare_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        title = QLabel("以下字段已被修改，请选择要应用的更新：")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #262626; margin-bottom: 8px;")
        self.compare_layout.insertWidget(0, title)

        for change in changes:
            self._create_diff_item_widget(change)

        # 切换到对比视图
        self.result_stack.setCurrentIndex(1)

    def _create_diff_item_widget(self, change: Change):
        """为差异项创建带复选框的widget"""
        path = change.label
        diff_type = change.kind
        old_value = change.old
        new_value = change.new
        
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
        self.diff_checkboxes.append(checkbox)
        header_layout.addWidget(checkbox)
        
        # 根据类型显示不同的图标和颜色
        if diff_type == 'removed':
            icon_text = "❌"
            path_style = "color: #d32f2f; font-weight: 600;"
        elif diff_type == 'added':
            icon_text = "➕"
            path_style = "color: #2e7d32; font-weight: 600;"
        else:  # changed
            icon_text = "🔄"
            path_style = "color: #1976d2; font-weight: 600;"
        
        path_label = QLabel(f"{icon_text} {path}")
        path_label.setStyleSheet(f"font-size: 14px; {path_style}")
        header_layout.addWidget(path_label)
        header_layout.addStretch()
        
        item_layout.addLayout(header_layout)
        
        # 显示旧值和新值
        if diff_type == 'removed':
            old_label = QLabel(f"<span style='text-decoration: line-through; color: #888;'>{self._format_value_for_html(old_value)}</span>")
            old_label.setStyleSheet("font-size: 12px; color: #666; padding-left: 26px;")
            item_layout.addWidget(old_label)
        elif diff_type == 'added':
            new_label = QLabel(f"<span style='color: #2e7d32;'>{self._format_value_for_html(new_value)}</span>")
            new_label.setStyleSheet("font-size: 12px; color: #666; padding-left: 26px;")
            item_layout.addWidget(new_label)
        else:  # changed
            old_label = QLabel(f"<span style='text-decoration: line-through; color: #888;'>{self._format_value_for_html(old_value)}</span>")
            old_label.setStyleSheet("font-size: 12px; color: #666; padding-left: 26px;")
            item_layout.addWidget(old_label)
            
            new_label = QLabel(f"<span style='color: #2e7d32;'>{self._format_value_for_html(new_value)}</span>")
            new_label.setStyleSheet("font-size: 12px; color: #666; padding-left: 26px;")
            item_layout.addWidget(new_label)
        
        # 插入到stretch之前
        self.compare_layout.insertWidget(self.compare_layout.count() - 1, item_frame)

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
    
    def _on_generate_error(self, error_msg: str):
        """生成出错"""
        self._is_generating = False
        self._set_generating_ui(False)
        self.status_label.setText(f"错误: {error_msg}")
        self.status_label.setStyleSheet("color: #F44336; font-size: 12px;")
        QMessageBox.critical(self, "AI生成错误", error_msg)

    def _on_apply(self):
        """把勾选的差异应用到原文档上（未勾选的部分和 overlay 保持原样）。"""
        if self._result is None or self._result.document is None:
            QMessageBox.critical(self, "错误", "没有有效的修改数据可应用")
            return
        selected = [
            change
            for change, checkbox in zip(self.diff_items, self.diff_checkboxes)
            if checkbox.isChecked()
        ]
        try:
            final_data = self.studio.apply_changes(self.current_data, selected)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "错误", f"应用修改时出错:\n{exc}")
            return
        self.modified.emit(final_data)
        self.accept()

    def _on_cancel(self):
        """取消/关闭对话框"""
        if self._is_generating:
            self.prompt_service.cancel()
        self.reject()
