"""架构边界。这些规则是「以后加功能 / 加交互口不会把代码搅在一起」的保证。

    desktop ─┐
    web ─────┼─→ nano_banana.core（Studio 门面）＋ nano_banana.core.prompt（纯函数）
    插件… ───┘
              core 内部： studio → storage | llm → images → prompt | media

同样的规则也写在 pyproject.toml 的 [tool.importlinter] 里（CI 跑 lint-imports）；
这里用 AST 再查一遍，这样只装了 pytest 也能发现越界。
"""
from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import PACKAGE, ROOT

PORTS = ("desktop", "web")
# 交互口允许导入的核心模块（精确匹配，不含子模块）
PORT_CORE_API = {"nano_banana.core", "nano_banana.core.prompt"}
UI_FRAMEWORKS = {"PyQt6", "PyQt5", "PySide6", "PySide2", "flask", "flask_cors"}
# 核心内部分层：键可以导入值里列出的核心子包（以及自己）
CORE_LAYERS = {
    "prompt": set(),
    "media": set(),
    "images": {"media"},
    "llm": {"prompt", "media"},
    "storage": {"images"},
    "studio": {"prompt", "media", "images", "llm", "storage"},
}


def _module_name(path: Path) -> str:
    parts = path.relative_to(PACKAGE.parent).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _imports(path: Path) -> set[str]:
    """文件里所有（含函数内的惰性）import 的绝对模块名。"""
    module = _module_name(path)
    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                anchor = package.split(".")[: len(package.split(".")) - node.level + 1]
                base = ".".join(anchor + ([base] if base else []))
            found.add(base)
            # from pkg import submodule 也算导入了 pkg.submodule
            found.update(f"{base}.{alias.name}" for alias in node.names)
    return found


def _sources(*parts: str) -> list[Path]:
    return sorted(PACKAGE.joinpath(*parts).rglob("*.py"))


def _violations(files: list[Path], is_forbidden) -> list[str]:
    return [
        f"{path.relative_to(ROOT).as_posix()} -> {name}"
        for path in files
        for name in sorted(_imports(path))
        if is_forbidden(name)
    ]


def _top(name: str) -> str:
    return name.partition(".")[0]


def test_layout_is_what_the_rules_assume():
    assert {path.name for path in PACKAGE.iterdir() if path.is_dir() and path.name != "__pycache__"} == {
        "core",
        "builtin",
        "desktop",
        "web",
    }
    core_parts = {
        path.stem for path in (PACKAGE / "core").iterdir() if path.name not in ("__init__.py", "__pycache__")
    }
    assert core_parts == set(CORE_LAYERS)


@pytest.mark.parametrize("port", PORTS)
def test_ports_only_use_the_public_core_api(port):
    """交互口只能走 Studio 门面和 core.prompt，不能伸手进渠道实现 / 存储 / LLM 细节。"""

    def forbidden(name: str) -> bool:
        if not name.startswith("nano_banana.core"):
            return False
        if name in PORT_CORE_API:
            return False
        # from nano_banana.core import Studio / from nano_banana.core.prompt import nest
        parent, _, attr = name.rpartition(".")
        return not (parent in PORT_CORE_API and not _is_core_submodule(parent, attr))

    assert _violations(_sources(port), forbidden) == []


def _is_core_submodule(parent: str, attr: str) -> bool:
    # 用目录列表做大小写敏感的比较：Windows 上 Studio.py 和 studio.py 是同一个文件
    entries = set(os.listdir(PACKAGE.parent.joinpath(*parent.split("."))))
    return f"{attr}.py" in entries or attr in entries


@pytest.mark.parametrize("port, other", [("desktop", "web"), ("web", "desktop")])
def test_ports_do_not_depend_on_each_other(port, other):
    assert _violations(_sources(port), lambda name: name.startswith(f"nano_banana.{other}")) == []


def test_core_has_no_ui_or_port_dependencies():
    def forbidden(name: str) -> bool:
        return _top(name) in UI_FRAMEWORKS or any(
            name.startswith(f"nano_banana.{port}") for port in PORTS
        )

    assert _violations(_sources("core"), forbidden) == []


def test_web_does_not_import_qt_and_desktop_does_not_import_flask():
    qt = {"PyQt6", "PyQt5", "PySide6", "PySide2"}
    assert _violations(_sources("web"), lambda name: _top(name) in qt) == []
    assert _violations(_sources("desktop"), lambda name: _top(name) in {"flask", "flask_cors"}) == []


@pytest.mark.parametrize("layer", sorted(CORE_LAYERS))
def test_core_internal_layering(layer):
    allowed = CORE_LAYERS[layer] | {layer}
    target = PACKAGE / "core" / layer
    files = _sources("core", layer) if target.is_dir() else [target.with_suffix(".py")]

    def forbidden(name: str) -> bool:
        if not name.startswith("nano_banana.core."):
            return False
        return name.split(".")[2] not in allowed

    assert _violations(files, forbidden) == []


def test_provider_sdks_are_imported_lazily():
    """渠道 SDK（openai / google-genai / httpx / PIL）只能在函数里导入：

    没装某个渠道的 SDK、或者只用 schema 的调用方，不应该在 import 阶段就失败 / 变慢。
    """
    heavy = {"openai", "google", "httpx", "PIL"}
    offenders = []
    for path in _sources("core"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:  # 只看模块顶层
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level:
                names = [node.module or ""]
            offenders += [
                f"{path.relative_to(ROOT).as_posix()} -> {name}" for name in names if _top(name) in heavy
            ]
    assert offenders == []


def test_import_linter_contracts_hold():
    """pyproject.toml 里的 import-linter 契约（装了 import-linter 才跑）。"""
    if importlib.util.find_spec("importlinter") is None:
        pytest.skip("import-linter is not installed")
    env = dict(os.environ, PYTHONPATH=str(PACKAGE.parent), PYTHONIOENCODING="utf-8", NO_COLOR="1")
    result = subprocess.run(
        [sys.executable, "-c", "from importlinter.cli import lint_imports; raise SystemExit(lint_imports())"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
