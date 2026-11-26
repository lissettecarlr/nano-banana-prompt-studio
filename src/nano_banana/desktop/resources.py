"""桌面端静态资源定位。"""
import sys
from pathlib import Path


def images_dir() -> Path:
    """打包后在 exe 同级的 images/，源码运行时在仓库根目录的 images/。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "images"
    return Path(__file__).resolve().parents[3] / "images"


def logo_path() -> Path:
    return images_dir() / "logo.png"
