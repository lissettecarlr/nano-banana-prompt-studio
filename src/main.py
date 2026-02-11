"""
Nano Banana 图片生成工具
AI绘画提示词可视化编辑工具

使用方法:
    python main.py
"""
import sys
import os

# 确保src目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QStyleFactory
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor

from app import PromptGeneratorApp


def setup_light_palette(app: QApplication):
    """强制设置浅色调色板，完全覆盖系统主题"""
    palette = QPalette()
    
    # 定义颜色
    white = QColor("#FFFFFF")
    off_white = QColor("#FAFAFA")
    light_gray = QColor("#F5F5F5")
    border_gray = QColor("#E0E0E0")
    text_primary = QColor("#2B2B2B")
    text_secondary = QColor("#757575")
    text_disabled = QColor("#9E9E9E")
    accent = QColor("#B8956B")
    selection_bg = QColor("#FBF7F2")
    
    # 窗口背景
    palette.setColor(QPalette.ColorRole.Window, white)
    palette.setColor(QPalette.ColorRole.WindowText, text_primary)
    
    # 基础背景（输入框等）
    palette.setColor(QPalette.ColorRole.Base, white)
    palette.setColor(QPalette.ColorRole.AlternateBase, off_white)
    
    # 文本
    palette.setColor(QPalette.ColorRole.Text, text_primary)
    palette.setColor(QPalette.ColorRole.BrightText, white)
    
    # 按钮
    palette.setColor(QPalette.ColorRole.Button, white)
    palette.setColor(QPalette.ColorRole.ButtonText, text_primary)
    
    # 高亮/选中
    palette.setColor(QPalette.ColorRole.Highlight, accent)
    palette.setColor(QPalette.ColorRole.HighlightedText, white)
    
    # 工具提示
    palette.setColor(QPalette.ColorRole.ToolTipBase, text_primary)
    palette.setColor(QPalette.ColorRole.ToolTipText, white)
    
    # 占位符文本
    palette.setColor(QPalette.ColorRole.PlaceholderText, text_disabled)
    
    # 链接
    palette.setColor(QPalette.ColorRole.Link, accent)
    palette.setColor(QPalette.ColorRole.LinkVisited, QColor("#A07D52"))
    
    # 禁用状态
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, text_disabled)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, text_disabled)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, text_disabled)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, light_gray)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, light_gray)
    
    # 边框/中间色调
    palette.setColor(QPalette.ColorRole.Mid, border_gray)
    palette.setColor(QPalette.ColorRole.Midlight, off_white)
    palette.setColor(QPalette.ColorRole.Dark, text_secondary)
    palette.setColor(QPalette.ColorRole.Shadow, border_gray)
    palette.setColor(QPalette.ColorRole.Light, white)
    
    app.setPalette(palette)


def main():
    # 高DPI支持
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    app.setStyle(QStyleFactory.create("Fusion"))
    
    # ===== 应用自定义浅色调色板 =====
    setup_light_palette(app)

    # 设置应用信息
    app.setApplicationName("Nano Banana 生图工具")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("NanoBanana")

    # 设置默认字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # 创建并显示主窗口
    window = PromptGeneratorApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
