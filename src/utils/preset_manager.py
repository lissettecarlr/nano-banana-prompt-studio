"""预设管理器"""
import os
import json
from pathlib import Path
from datetime import datetime
from utils.resource_path import get_presets_dir


class PresetManager:
    """管理提示词预设的保存和加载"""

    def __init__(self):
        self.presets_dir = get_presets_dir()
        self._ensure_dir_exists()

    def _ensure_dir_exists(self):
        """确保预设目录存在"""
        self.presets_dir.mkdir(parents=True, exist_ok=True)

    def get_all_presets(self) -> list[dict]:
        """获取所有预设列表，返回 [{name, path, modified_time}, ...]"""
        presets = []
        for file in self.presets_dir.glob("*.json"):
            try:
                stat = file.stat()
                presets.append({
                    "name": file.stem,
                    "path": str(file),
                    "modified_time": datetime.fromtimestamp(stat.st_mtime),
                })
            except Exception:
                continue
        # 按修改时间倒序排列
        presets.sort(key=lambda x: x["modified_time"], reverse=True)
        return presets

    def save_preset(self, name: str, data: dict) -> bool:
        """保存预设"""
        try:
            # 清理文件名中的非法字符
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_', '（', '）', '(', ')')).strip()
            if not safe_name:
                safe_name = f"preset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            file_path = self.presets_dir / f"{safe_name}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存预设失败: {e}")
            return False

    def load_preset(self, name: str) -> dict | None:
        """加载预设"""
        try:
            file_path = self.presets_dir / f"{name}.json"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载预设失败: {e}")
        return None

    def delete_preset(self, name: str) -> bool:
        """删除预设"""
        try:
            file_path = self.presets_dir / f"{name}.json"
            if file_path.exists():
                file_path.unlink()
                return True
        except Exception as e:
            print(f"删除预设失败: {e}")
        return False

    def rename_preset(self, old_name: str, new_name: str) -> bool:
        """重命名预设"""
        try:
            old_path = self.presets_dir / f"{old_name}.json"
            new_path = self.presets_dir / f"{new_name}.json"
            if old_path.exists() and not new_path.exists():
                old_path.rename(new_path)
                return True
        except Exception as e:
            print(f"重命名预设失败: {e}")
        return False

