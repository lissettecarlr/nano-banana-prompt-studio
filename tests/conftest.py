"""公共夹具。所有测试都用临时数据目录，绝不碰开发机上的真实配置。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from nano_banana.core import (  # noqa: E402
    ProviderRegistry,
    ProviderSpec,
    Studio,
    StudioPaths,
)
from nano_banana.core.images.types import OptionSpec, aspect_ratio_option  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "nano_banana"
STATIC = PACKAGE / "web" / "static"
BUILTIN = PACKAGE / "builtin"


@dataclass
class FakeBackendLog:
    """记录假渠道收到的调用，供断言。"""

    credentials: list = field(default_factory=list)
    calls: list = field(default_factory=list)
    error: Exception | None = None
    image_size: tuple[int, int] = (2, 2)


def make_fake_spec(log: FakeBackendLog, provider_id: str = "fake", **overrides) -> ProviderSpec:
    class FakeBackend:
        def __init__(self, credentials):
            log.credentials.append(credentials)

        def generate(self, prompt, images, options):
            log.calls.append({"prompt": prompt, "images": tuple(images), "options": dict(options)})
            if log.error is not None:
                raise log.error
            return Image.new("RGB", log.image_size, "white")

    params = {
        "id": provider_id,
        "label": f"Fake {provider_id}",
        "factory": FakeBackend,
        "default_model": "fake-model",
        "default_base_url": "https://fake.example/v1",
        "url_placeholder": "https://fake.example/v1",
        "model_suggestions": ("fake-model", "fake-model-lite"),
        "options": (
            aspect_ratio_option(),
            OptionSpec("image_size", "尺寸", "2K", ("1K", "2K")),
        ),
        "model_overrides": {
            "fake-model-lite": {"options": {"image_size": None}},
        },
    }
    params.update(overrides)
    return ProviderSpec(**params)


@pytest.fixture
def paths(tmp_path) -> StudioPaths:
    """空的用户目录 + 空的内置目录：没有任何预设和默认选项。"""
    return StudioPaths(user=tmp_path / "data", builtin=tmp_path / "builtin")


@pytest.fixture
def studio(paths) -> Studio:
    """真实渠道注册表 + 临时数据目录。"""
    return Studio(paths)


@pytest.fixture
def backend_log() -> FakeBackendLog:
    return FakeBackendLog()


@pytest.fixture
def fake_studio(paths, backend_log) -> Studio:
    """两个假渠道（fake / other），不会发出任何网络请求。"""
    registry = ProviderRegistry(
        [make_fake_spec(backend_log, "fake"), make_fake_spec(backend_log, "other")]
    )
    return Studio(paths, registry=registry)


@pytest.fixture
def web_client(fake_studio):
    """挂在 fake_studio 上的 Flask 测试客户端。"""
    pytest.importorskip("flask")
    from nano_banana.web import create_app

    return create_app(fake_studio).test_client()


@pytest.fixture(scope="session")
def qapp(tmp_path_factory):
    QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
    from nano_banana.desktop.window_utils import use_settings_file

    # 窗口几何、上次目录等 UI 状态写到临时 ini，不污染开发机的注册表 / 配置
    use_settings_file(tmp_path_factory.mktemp("qsettings") / "ui_state.ini")
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
