"""预设文件格式化工具：按 schema 统一 JSON 的字段顺序（维护内置预设时用）。

    python scripts/format_presets.py                 # 格式化内置预设（含分类预设）
    python scripts/format_presets.py path/to/presets  # 格式化指定目录
    python scripts/format_presets.py --check          # 只检查，不写文件；有未格式化的文件时退出码为 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nano_banana.core import StudioPaths
from nano_banana.core.prompt import order_document


def format_json_data(data: dict) -> dict:
    return order_document(data)


def _dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def format_preset_file(file_path: Path, *, check: bool = False) -> bool:
    """格式化单个预设文件。返回文件内容是否（本来就 / 已经被改成）规范格式。"""
    original = file_path.read_text(encoding="utf-8")
    data = json.loads(original)
    if not isinstance(data, dict):
        raise ValueError("预设内容必须是 JSON 对象")
    formatted = _dump(format_json_data(data))
    # 行尾风格（CRLF / 末尾换行）不算差异，只看内容和字段顺序
    if formatted == original.replace("\r\n", "\n").rstrip("\n"):
        return True
    if check:
        return False
    file_path.write_text(formatted, encoding="utf-8", newline="\n")
    return True


def format_all_presets(presets_dir: Path | None = None, *, check: bool = False) -> int:
    """格式化目录下（含子目录）所有预设，返回有问题的文件数。"""
    presets_dir = presets_dir or StudioPaths.default().builtin_presets_dir
    if not presets_dir.exists():
        print(f"预设目录不存在: {presets_dir}")
        return 1
    # 点开头的是存储内部的标记文件（如 .seeded.json），不是预设
    json_files = sorted(p for p in presets_dir.rglob("*.json") if not p.name.startswith("."))
    if not json_files:
        print(f"未找到预设文件: {presets_dir}")
        return 0

    problems = 0
    for file_path in json_files:
        name = file_path.relative_to(presets_dir).as_posix()
        try:
            ok = format_preset_file(file_path, check=check)
        except (OSError, ValueError) as exc:
            problems += 1
            print(f"[失败] {name}: {exc}")
            continue
        if not ok:
            problems += 1
            print(f"[未格式化] {name}")
    done = "检查" if check else "格式化"
    print(f"{done}完成：{len(json_files) - problems}/{len(json_files)} 个文件符合规范（{presets_dir}）")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("presets_dir", nargs="?", type=Path, help="预设目录，默认是内置预设")
    parser.add_argument("--check", action="store_true", help="只检查，不写文件")
    args = parser.parse_args()
    sys.exit(1 if format_all_presets(args.presets_dir, check=args.check) else 0)


if __name__ == "__main__":
    main()
