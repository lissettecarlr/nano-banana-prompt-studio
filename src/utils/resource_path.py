"""资源路径处理工具，支持打包后的exe运行"""
import sys
import os
from pathlib import Path


def get_base_path() -> Path:
    """
    获取应用的基础路径
    - 开发环境: 返回src目录
    - 打包后: 返回exe所在目录
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后运行
        return Path(sys.executable).parent
    else:
        # 开发环境
        return Path(__file__).parent.parent


def get_resource_path(relative_path: str) -> Path:
    """
    获取资源文件的绝对路径
    :param relative_path: 相对于基础目录的路径
    """
    base = get_base_path()
    return base / relative_path


def get_config_path() -> Path:
    """获取配置文件路径"""
    return get_resource_path("config/options.yaml")


def get_presets_dir() -> Path:
    """获取预设目录路径"""
    return get_resource_path("presets")


def get_images_dir() -> Path:
    """获取图片目录路径"""
    if getattr(sys, 'frozen', False):
        return get_resource_path("images")
    else:
        return Path(__file__).parent.parent.parent / "images"

