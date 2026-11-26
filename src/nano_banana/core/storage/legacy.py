"""一次性导入重构前的数据位置（仅源码运行）。

以前源码运行时配置和预设直接写在 src/config、src/presets 里；
现在统一到 StudioPaths.user。目标已存在的文件一律不覆盖。
"""
from __future__ import annotations

import shutil
from pathlib import Path

from loguru import logger

from nano_banana.core.storage.paths import StudioPaths


def import_legacy_user_data(paths: StudioPaths) -> list[Path]:
    legacy = paths.legacy_user_dir
    if legacy is None:
        return []

    pairs: list[tuple[Path, Path]] = [
        (legacy / "config" / "ai_config.yaml", paths.settings_file),
        (legacy / "config" / "options.yaml", paths.options_file),
    ]
    legacy_presets = legacy / "presets"
    if legacy_presets.is_dir():
        pairs.extend(
            (source, paths.presets_dir / source.relative_to(legacy_presets))
            for source in legacy_presets.rglob("*.json")
        )

    copied: list[Path] = []
    for source, target in pairs:
        if not source.is_file() or target.exists():
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(target)
        except OSError as exc:
            logger.warning(f"导入旧数据失败 {source}: {exc}")
    if copied:
        logger.info(f"已从 {legacy} 导入 {len(copied)} 个旧数据文件到 {paths.user}")
    return copied
