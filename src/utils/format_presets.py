"""预设文件格式化工具 - 统一JSON字段顺序"""
import json
import os
import sys
from pathlib import Path

# 添加项目根目录到路径，以便独立运行
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))


def format_json_data(data: dict) -> dict:
    """按照新的分类顺序格式化JSON数据"""
    
    # 定义新的字段顺序（按优先级）
    order = [
        "风格模式",
        "画面气质",
        "场景",
        "相机",
        "审美控制",
        "画幅设置",
        "反向提示词"
    ]
    
    # 按照顺序构建新字典
    formatted = {}
    for key in order:
        if key in data:
            formatted[key] = data[key]
    
    # 添加任何其他未列出的字段（向后兼容）
    for key, value in data.items():
        if key not in formatted:
            formatted[key] = value
    
    return formatted


def format_preset_file(file_path: Path) -> bool:
    """格式化单个预设文件"""
    try:
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 格式化
        formatted_data = format_json_data(data)
        
        # 写回文件（保持缩进格式）
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(formatted_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 已格式化: {file_path.name}")
        return True
    except Exception as e:
        print(f"✗ 格式化失败 {file_path.name}: {e}")
        return False


def format_all_presets(presets_dir: Path = None):
    """格式化所有预设文件"""
    if presets_dir is None:
        # 默认预设目录
        presets_dir = Path(__file__).parent.parent / "presets"
    
    if not presets_dir.exists():
        print(f"预设目录不存在: {presets_dir}")
        return
    
    # 查找所有JSON文件
    json_files = list(presets_dir.glob("*.json"))
    
    if not json_files:
        print(f"未找到预设文件: {presets_dir}")
        return
    
    print(f"找到 {len(json_files)} 个预设文件，开始格式化...\n")
    
    success_count = 0
    for file_path in json_files:
        if format_preset_file(file_path):
            success_count += 1
    
    print(f"\n完成！成功格式化 {success_count}/{len(json_files)} 个文件")


if __name__ == "__main__":
    import sys
    
    # 如果提供了目录路径，使用它；否则使用默认路径
    if len(sys.argv) > 1:
        presets_dir = Path(sys.argv[1])
    else:
        presets_dir = None
    
    format_all_presets(presets_dir)

