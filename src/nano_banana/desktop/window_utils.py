"""窗口尺寸自适应与 UI 状态持久化工具。"""
import os
import tempfile
import time

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication, QWidget

IMAGE_FILE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


_settings_file: str | None = None


def use_settings_file(path: str | os.PathLike | None) -> None:
    """把 UI 状态改存到指定 ini 文件（传 None 恢复系统默认位置）。

    QSettings(组织, 应用) 固定用系统原生存储（Windows 上是注册表），
    setDefaultFormat 对它无效，所以测试 / 便携模式需要显式指定文件。
    """
    global _settings_file
    _settings_file = os.fspath(path) if path else None


def app_settings() -> QSettings:
    """应用级 UI 状态存储（窗口几何、上次目录等）。"""
    if _settings_file:
        return QSettings(_settings_file, QSettings.Format.IniFormat)
    return QSettings("NanoBanana", "NanoBananaStudio")


def get_last_dir(key: str = "default") -> str:
    return app_settings().value(f"last_dir/{key}", "", str)


def remember_last_dir(path: str, key: str = "default") -> None:
    """记录文件对话框最近使用的目录，path 可以是文件或目录。"""
    if not path:
        return
    directory = path if os.path.isdir(path) else os.path.dirname(path)
    if directory:
        app_settings().setValue(f"last_dir/{key}", directory)


def extract_image_paths(mime_data) -> list:
    """从拖拽的 mimeData 中提取本地图片文件路径。"""
    if not mime_data or not mime_data.hasUrls():
        return []
    paths = []
    for url in mime_data.urls():
        if not url.isLocalFile():
            continue
        path = url.toLocalFile()
        if os.path.splitext(path)[1].lower() in IMAGE_FILE_EXTS:
            paths.append(path)
    return paths


def save_clipboard_image() -> str:
    """把剪贴板中的图片存为临时 PNG 并返回路径，无图片返回空串。"""
    image = QApplication.clipboard().image()
    if image.isNull():
        return ""
    path = os.path.join(
        tempfile.gettempdir(), f"nano_banana_paste_{int(time.time() * 1000)}.png"
    )
    return path if image.save(path, "PNG") else ""


def fit_window_to_screen(
    window: QWidget,
    preferred_width: int,
    preferred_height: int,
    min_width: int = 0,
    min_height: int = 0,
    margin: float = 0.94,
) -> None:
    """按当前屏幕可用区域钳制窗口的最小尺寸与初始尺寸。

    固定的 setMinimumSize/resize 在小分辨率或高DPI缩放
    （如 1366x768、1920x1080@150% 时逻辑分辨率仅 1280x720）下
    会超出屏幕，导致窗口底部按钮不可见。
    """
    screen = window.screen() or QGuiApplication.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        max_width = int(available.width() * margin)
        max_height = int(available.height() * margin)
    else:
        max_width, max_height = preferred_width, preferred_height

    if min_width or min_height:
        window.setMinimumSize(min(min_width, max_width), min(min_height, max_height))
    window.resize(min(preferred_width, max_width), min(preferred_height, max_height))
