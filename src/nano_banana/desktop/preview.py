"""预览相关控件，从主窗体拆出。"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout

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


class ImagePreviewLabel(ClickableLabel):
    """始终按控件可用区域完整显示原图。"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._source_pixmap = QPixmap()

    def setSourcePixmap(self, pixmap: QPixmap):
        self._source_pixmap = pixmap
        self._update_scaled_pixmap()

    def clearSourcePixmap(self):
        self._source_pixmap = QPixmap()
        self.setPixmap(QPixmap())

    def _update_scaled_pixmap(self):
        if self._source_pixmap.isNull():
            return

        available_size = self.contentsRect().size()
        if available_size.width() <= 0 or available_size.height() <= 0:
            return

        scaled = self._source_pixmap.scaled(
            available_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scaled_pixmap()


class ImagePreviewDialog(QDialog):
    """图片预览对话框 - 显示大图"""
    
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("图片预览")
        self.setModal(True)

        # 最小尺寸不超过屏幕可用区域，避免小屏/高DPI缩放下窗口被裁切
        screen = self.screen().availableGeometry()
        max_width = int(screen.width() * 0.9)
        max_height = int(screen.height() * 0.9)
        self.setMinimumSize(min(800, max_width), min(600, max_height))
        
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
