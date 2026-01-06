"""YAML配置文件处理工具"""
import os
import yaml
from pathlib import Path
from utils.resource_path import get_config_path


class YamlHandler:
    """处理YAML配置文件的读写操作"""

    def __init__(self):
        self.config_path = get_config_path()
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        """确保配置文件存在"""
        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.save_options({})

    def load_options(self) -> dict:
        """加载所有选项配置"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if data else {}
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return {}

    def save_options(self, options: dict):
        """保存所有选项配置"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    options,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def get_field_options(self, field_name: str) -> list:
        """获取指定字段的选项列表"""
        options = self.load_options()
        return options.get(field_name, [])

    def add_option(self, field_name: str, value: str):
        """为指定字段添加一个选项"""
        options = self.load_options()
        if field_name not in options:
            options[field_name] = []
        if value and value not in options[field_name]:
            options[field_name].append(value)
            self.save_options(options)

    def remove_option(self, field_name: str, value: str):
        """从指定字段删除一个选项"""
        options = self.load_options()
        if field_name in options and value in options[field_name]:
            options[field_name].remove(value)
            self.save_options(options)

    def update_option(self, field_name: str, old_value: str, new_value: str):
        """更新指定字段的某个选项"""
        options = self.load_options()
        if field_name in options and old_value in options[field_name]:
            idx = options[field_name].index(old_value)
            options[field_name][idx] = new_value
            self.save_options(options)

    def get_line_art_prompt(self) -> str:
        """获取角色线稿生成的提示词"""
        options = self.load_options()
        return options.get("角色线稿提示词", "")

    def save_line_art_prompt(self, prompt: str):
        """保存角色线稿生成的提示词"""
        options = self.load_options()
        options["角色线稿提示词"] = prompt
        self.save_options(options)
