import base64
import json
from io import BytesIO

import pytest
from PIL import Image

pytest.importorskip("flask")

from nano_banana.core import Studio  # noqa: E402
from nano_banana.core.prompt import build_document  # noqa: E402
from nano_banana.web import create_app  # noqa: E402
from nano_banana.web import app as web_app_module  # noqa: E402


def _configure_image(studio, provider="fake", **overrides):
    creds = {"api_key": "image-key"}
    creds.update(overrides)
    studio.settings.update({"image": {"providers": {provider: creds}}})


# ---------------- 应用工厂 ----------------


def test_importing_the_web_package_has_no_side_effects():
    assert not hasattr(web_app_module, "app")  # 没有模块级全局应用


def test_each_app_is_bound_to_its_own_studio(tmp_path, fake_studio):
    from nano_banana.core import StudioPaths

    other = Studio(StudioPaths(user=tmp_path / "other", builtin=tmp_path / "builtin"))
    fake_studio.presets.save("只在第一个里", {"风格模式": "x"})

    first = create_app(fake_studio).test_client()
    second = create_app(other).test_client()

    assert [item["name"] for item in first.get("/api/presets").get_json()] == ["只在第一个里"]
    assert second.get("/api/presets").get_json() == []


def test_index_and_static_assets_are_served(web_client):
    response = web_client.get("/")
    assert response.status_code == 200
    assert "<title>" in response.get_data(as_text=True)
    response.close()

    asset = web_client.get("/static/sse-parser.js")
    assert asset.status_code == 200
    asset.close()


def test_api_errors_are_always_json(web_client):
    response = web_client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert "error" in response.get_json()

    response = web_client.put("/api/config")
    assert response.status_code == 405
    assert "error" in response.get_json()


def test_unexpected_api_exception_is_reported_as_json(fake_studio, monkeypatch):
    monkeypatch.setattr(
        type(fake_studio.presets), "list_all", lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    response = create_app(fake_studio).test_client().get("/api/presets")
    assert response.status_code == 500
    assert response.get_json() == {"error": "boom"}


def test_cors_is_off_by_default_and_opt_in(fake_studio, monkeypatch):
    pytest.importorskip("flask_cors")
    headers = {"Origin": "https://evil.example"}

    monkeypatch.delenv(web_app_module.CORS_ENV, raising=False)
    response = create_app(fake_studio).test_client().get("/api/config", headers=headers)
    assert "Access-Control-Allow-Origin" not in response.headers

    monkeypatch.setenv(web_app_module.CORS_ENV, "https://ok.example, https://also.example")
    client = create_app(fake_studio).test_client()
    assert "Access-Control-Allow-Origin" not in client.get("/api/config", headers=headers).headers
    allowed = client.get("/api/config", headers={"Origin": "https://ok.example"})
    assert allowed.headers["Access-Control-Allow-Origin"] == "https://ok.example"


def test_main_reads_host_port_debug_from_env(monkeypatch, fake_studio, capsys):
    calls = {}

    class FakeApp:
        extensions = {"nano_banana_studio": fake_studio}

        def run(self, **kwargs):
            calls.update(kwargs)

    monkeypatch.setattr(web_app_module, "create_app", lambda: FakeApp())
    for name in (web_app_module.HOST_ENV, web_app_module.PORT_ENV, web_app_module.DEBUG_ENV):
        monkeypatch.delenv(name, raising=False)

    opened = []
    monkeypatch.setattr(web_app_module, "_open_browser_later", opened.append)

    web_app_module.main([])
    assert calls == {"host": "127.0.0.1", "port": 5000, "debug": False}
    assert opened == []  # 默认不打开浏览器

    monkeypatch.setenv(web_app_module.HOST_ENV, "0.0.0.0")
    monkeypatch.setenv(web_app_module.PORT_ENV, "8123")
    monkeypatch.setenv(web_app_module.DEBUG_ENV, "true")
    web_app_module.main(["--open"])
    assert calls == {"host": "0.0.0.0", "port": 8123, "debug": True}
    assert opened == ["http://localhost:8123"]
    assert str(fake_studio.paths.user) in capsys.readouterr().out


# ---------------- 配置 ----------------


def test_config_api_never_returns_secrets(web_client, fake_studio):
    fake_studio.settings.update(
        {
            "chat": {"base_url": "https://chat.example/v1", "api_key": "chat-secret", "model": "m"},
            "image": {"providers": {"fake": {"api_key": "image-secret"}}},
        }
    )

    response = web_client.get("/api/config")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "secret" not in body
    data = response.get_json()
    assert data["chat"] == {"base_url": "https://chat.example/v1", "model": "m", "has_api_key": True}
    assert data["image"]["active"] == "fake"
    assert data["image"]["providers"]["fake"]["has_api_key"] is True
    assert data["image"]["providers"]["other"]["has_api_key"] is False


def test_config_api_accepts_nested_patches_and_keeps_omitted_keys(web_client, fake_studio):
    fake_studio.settings.update({"chat": {"api_key": "keep-me", "model": "old"}})

    response = web_client.post(
        "/api/config",
        json={
            "chat": {"model": "new"},
            "image": {"providers": {"other": {"base_url": "https://o.example", "api_key": "k"}}},
        },
    )

    assert response.get_json() == {"success": True}
    assert fake_studio.settings.chat().api_key == "keep-me"
    assert fake_studio.settings.chat().model == "new"
    assert fake_studio.settings.credentials("other").base_url == "https://o.example"


@pytest.mark.parametrize(
    "payload, message",
    [
        (["not", "an", "object"], "请求体必须是 JSON 对象"),
        ({"image": {"active": "nope"}}, "未知图片生成渠道: nope"),
    ],
)
def test_config_api_rejects_bad_patches(web_client, fake_studio, payload, message):
    response = web_client.post("/api/config", json=payload)
    assert response.status_code == 400
    assert response.get_json() == {"error": message}
    assert not fake_studio.paths.settings_file.exists()


# ---------------- 渠道 / 生图 ----------------


def test_image_provider_api_describes_channels_without_credentials(web_client, fake_studio):
    _configure_image(fake_studio, "fake", model="custom")

    response = web_client.get("/api/image-providers")
    payload = response.get_json()

    assert list(payload) == ["fake", "other"]
    fake = payload["fake"]
    assert fake["label"] == "Fake fake"
    assert fake["default_model"] == "fake-model"
    assert fake["configured_model"] == "custom"
    assert fake["models"] == ["fake-model", "fake-model-lite", "custom"]
    assert fake["has_api_key"] is True and fake["is_configured"] is True
    assert payload["other"]["has_api_key"] is False
    assert set(fake["capabilities"]["fake-model"]["options"]) == {"aspect_ratio", "image_size"}
    assert set(fake["capabilities"]["fake-model-lite"]["options"]) == {"aspect_ratio"}
    assert "image-key" not in response.get_data(as_text=True)
    assert "api_key" not in fake


def test_real_registry_is_exposed_by_default(studio):
    payload = create_app(studio).test_client().get("/api/image-providers").get_json()
    assert list(payload) == ["gemini", "openai_images", "qwen_image", "doubao_image"]
    assert payload["doubao_image"]["default_model"] == "doubao-seedream-5-0-pro-260628"
    assert payload["qwen_image"]["models"] == ["qwen-image-3.0-pro"]


def test_image_generation_settings_persist_selection_and_options(web_client, fake_studio):
    response = web_client.post(
        "/api/image-generation-settings",
        json={"provider": "other", "model": " fake-model-lite ", "options": {"aspect_ratio": "9:16"}},
    )

    assert response.get_json() == {"success": True}
    assert fake_studio.settings.active_provider() == "other"
    assert fake_studio.settings.credentials("other").model == "fake-model-lite"
    assert fake_studio.settings.generation_options("other", "fake-model-lite") == {"aspect_ratio": "9:16"}
    assert web_client.get("/api/config").get_json()["image"]["options"] == {
        "other": {"fake-model-lite": {"aspect_ratio": "9:16"}}
    }


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"provider": "nope", "model": "m"}, "未知图片生成渠道: nope"),
        ({"provider": "fake", "model": "  "}, "图片模型不能为空"),
        ({"provider": "fake", "model": "m", "options": []}, "生成参数必须是 JSON 对象"),
        ({"provider": ["fake"], "model": "m"}, "未知图片生成渠道: ['fake']"),
    ],
)
def test_image_generation_settings_validation(web_client, payload, message):
    response = web_client.post("/api/image-generation-settings", json=payload)
    assert response.status_code == 400
    assert response.get_json() == {"error": message}


def test_generate_image_uses_the_requested_provider_and_model_snapshot(
    web_client, fake_studio, backend_log
):
    _configure_image(fake_studio, "fake")
    _configure_image(fake_studio, "other", base_url="https://images.example/v1", model="old-model")

    response = web_client.post(
        "/api/generate-image",
        json={
            "prompt": "test prompt",
            "images": [],
            "provider": "other",
            "model": "requested-model",
            "options": {"aspect_ratio": "16:9", "image_size": "1K"},
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert (payload["provider"], payload["model"]) == ("other", "requested-model")
    header, _, encoded = payload["image"].partition(",")
    assert header == "data:image/png;base64"
    assert Image.open(BytesIO(base64.b64decode(encoded))).size == (2, 2)

    credentials = backend_log.credentials[0]
    assert (credentials.base_url, credentials.api_key, credentials.model) == (
        "https://images.example/v1",
        "image-key",
        "requested-model",
    )
    assert backend_log.calls == [
        {"prompt": "test prompt", "images": (), "options": {"aspect_ratio": "16:9", "image_size": "1K"}}
    ]
    assert fake_studio.settings.active_provider() == "other"
    assert fake_studio.settings.credentials("other").model == "requested-model"


def test_generate_image_renders_the_document_on_the_server(web_client, fake_studio, backend_log):
    """前端只交文档，最终文本以服务端为准 —— 和 /api/prompt/render 的预览逐字一致。"""
    _configure_image(fake_studio, "fake")
    document = build_document({"styleMode": "插画"}, negative_prompt="水印", special_requirement="横图")

    preview = web_client.post("/api/prompt/render", json={"document": document}).get_json()
    response = web_client.post(
        "/api/generate-image",
        json={"document": document, "prompt": "被忽略", "provider": "fake", "images": ["data:image/png;base64,AA=="]},
    )

    assert response.status_code == 200
    assert backend_log.calls[0]["prompt"] == preview["text"]
    assert preview["text"].endswith("\n\n特别要求：横图")
    payload = json.loads(preview["text"].split("\n\n特别要求：")[0])
    assert payload == preview["payload"]
    assert (payload["风格模式"], payload["反向提示词"]) == ("插画", "水印")
    assert "特别要求" not in payload
    assert list(payload)[0] == "风格模式" and list(payload)[-1] == "反向提示词"  # schema 顺序
    assert backend_log.calls[0]["images"] == ("data:image/png;base64,AA==",)


def test_generate_image_accepts_legacy_top_level_options(web_client, fake_studio, backend_log):
    _configure_image(fake_studio, "fake")
    response = web_client.post(
        "/api/generate-image",
        json={"prompt": "p", "provider": "fake", "aspect_ratio": "3:2", "image_size": "1K"},
    )
    assert response.status_code == 200
    assert backend_log.calls[0]["options"] == {"aspect_ratio": "3:2", "image_size": "1K"}


def test_generate_image_returns_provider_error_verbatim(web_client, fake_studio, backend_log):
    _configure_image(fake_studio, "fake")
    provider_error = (
        "Error code: 400 - {'error': {'code': 'PolicyViolation', "
        "'message': 'blocked. Request id: 021786687542', 'param': '', 'type': 'BadRequestError'}}"
    )
    backend_log.error = RuntimeError(provider_error)

    response = web_client.post("/api/generate-image", json={"prompt": "test prompt", "provider": "fake"})

    assert response.status_code == 500
    assert response.get_json() == {"error": provider_error}


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"prompt": "p", "provider": "nope"}, "未知图片生成渠道: nope"),
        ({"prompt": "p", "provider": "other"}, "请先配置 Fake other Base URL 和 API Key"),
        ({"prompt": "", "provider": "fake"}, "提示词不能为空"),
        ({"document": {}, "provider": "fake"}, "提示词不能为空"),
        ({"prompt": "p", "provider": "fake", "images": "x"}, "images 必须是数组"),
    ],
)
def test_generate_image_user_errors_are_400(web_client, fake_studio, backend_log, payload, message):
    _configure_image(fake_studio, "fake")
    response = web_client.post("/api/generate-image", json=payload)
    assert response.status_code == 400
    assert response.get_json() == {"error": message}
    assert backend_log.calls == []


# ---------------- schema / 渲染 / 选项 ----------------


def test_schema_api_exposes_fields_and_overlays(web_client):
    schema = web_client.get("/api/schema").get_json()
    assert [category["id"] for category in schema["categories"]] == [
        "basic",
        "scene",
        "subject",
        "camera",
        "aesthetic",
    ]
    overlays = {overlay["id"]: overlay for overlay in schema["overlays"]}
    assert overlays["negativePrompt"]["default"] == "水印、签名、文字"
    assert overlays["specialRequirement"]["ui_only"] is True


def test_render_api(web_client):
    line_art = build_document({"styleMode": "插画"}, special_requirement="白底", line_art_prompt="画线稿")
    rendered = web_client.post("/api/prompt/render", json={"document": line_art}).get_json()
    assert rendered["mode"] == "line_art"
    assert rendered["text"] == "画线稿\n\n额外要求：白底"

    empty = web_client.post("/api/prompt/render", json={"document": {}}).get_json()
    assert empty == {"text": "", "mode": "json", "payload": {}, "is_empty": True}

    bad = web_client.post("/api/prompt/render", json={"document": "x"})
    assert bad.status_code == 400


def test_options_api_roundtrip(web_client):
    assert web_client.get("/api/options/风格模式").get_json() == []
    assert web_client.get("/api/options/反向提示词标签").get_json() == ["水印、签名、文字"]

    assert web_client.post("/api/options/风格模式", json={"value": "厚涂"}).get_json() == {"success": True}
    assert web_client.get("/api/options/风格模式").get_json() == ["厚涂"]
    assert web_client.get("/api/options").get_json()["风格模式"] == ["厚涂"]

    assert web_client.delete("/api/options/风格模式", json={"value": "厚涂"}).get_json() == {"success": True}
    assert web_client.get("/api/options/风格模式").get_json() == []
    assert web_client.post("/api/options/风格模式", json={"value": ""}).status_code == 400
    assert web_client.delete("/api/options/风格模式", json={}).status_code == 400


def test_line_art_prompt_api(web_client):
    assert web_client.get("/api/line-art-prompt").get_json() == {"prompt": ""}
    assert web_client.post("/api/line-art-prompt", json={"prompt": "线稿"}).get_json() == {"success": True}
    assert web_client.get("/api/line-art-prompt").get_json() == {"prompt": "线稿"}
    assert web_client.post("/api/line-art-prompt", json={"prompt": None}).status_code == 400


# ---------------- 预设 ----------------


def test_preset_api_roundtrip_and_migration(web_client, fake_studio):
    saved = web_client.post(
        "/api/presets",
        json={"name": "我的/预设", "data": {"反向提示词": {"禁止元素": ["水印"], "禁止风格": ["模糊"]}}},
    )
    assert saved.get_json() == {"success": True, "name": "我的预设"}

    listing = web_client.get("/api/presets").get_json()
    assert [item["name"] for item in listing] == ["我的预设"]
    assert "T" in listing[0]["modified_time"]

    # 读出来的永远是当前结构
    assert web_client.get("/api/presets/我的预设").get_json() == {"反向提示词": "水印, 模糊"}
    assert web_client.get("/api/presets/details").get_json() == [{"反向提示词": "水印, 模糊"}]

    assert web_client.delete("/api/presets/我的预设").get_json() == {"success": True}
    assert web_client.get("/api/presets/我的预设").status_code == 404
    assert web_client.delete("/api/presets/我的预设").status_code == 404


def test_preset_api_validation_and_traversal(web_client, fake_studio, tmp_path):
    assert web_client.post("/api/presets", json={"name": "", "data": {"a": 1}}).status_code == 400
    assert web_client.post("/api/presets", json={"name": "x", "data": {}}).status_code == 400
    assert web_client.post("/api/presets", json={"name": "x", "data": []}).status_code == 400

    secret = fake_studio.paths.user / "secret.json"
    secret.parent.mkdir(parents=True, exist_ok=True)
    secret.write_text('{"leak": true}', encoding="utf-8")
    for name in ("..%2Fsecret", "..%5Csecret", "%2E%2E%2Fsecret"):
        assert web_client.get(f"/api/presets/{name}").status_code == 404
        assert web_client.delete(f"/api/presets/{name}").status_code == 404
    assert secret.exists()


def test_category_preset_api(web_client):
    saved = web_client.post(
        "/api/category-presets/basic", json={"name": "常用", "data": {"风格模式": "插画"}}
    )
    assert saved.get_json() == {"success": True, "name": "常用"}
    assert [item["name"] for item in web_client.get("/api/category-presets/basic").get_json()] == ["常用"]
    assert web_client.get("/api/category-presets/scene").get_json() == []
    assert web_client.get("/api/category-presets/basic/常用").get_json() == {"风格模式": "插画"}
    assert web_client.get("/api/presets").get_json() == []  # 不混进整套预设

    assert web_client.delete("/api/category-presets/basic/常用").get_json() == {"success": True}
    assert web_client.get("/api/category-presets/basic/常用").status_code == 404

    for method, url in (
        ("get", "/api/category-presets/unknown"),
        ("get", "/api/category-presets/unknown/x"),
        ("post", "/api/category-presets/unknown"),
        ("delete", "/api/category-presets/unknown/x"),
    ):
        response = getattr(web_client, method)(url, json={"name": "x", "data": {}})
        assert response.status_code == 404
        assert response.get_json() == {"error": "未知的预设分类"}
