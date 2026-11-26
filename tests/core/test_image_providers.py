import base64
import json
from io import BytesIO
from types import SimpleNamespace

import httpx
import pytest
from conftest import FakeBackendLog, make_fake_spec
from openai import OpenAI
from PIL import Image

from nano_banana.core import ImageResult, ProviderRegistry, UnknownProviderError
from nano_banana.core.images.providers import doubao, openai_images, qwen
from nano_banana.core.images.registry import BUILTIN_PROVIDER_MODULES, default_registry
from nano_banana.core.images.types import ImageBackend, ProviderCredentials
from nano_banana.core.media import (
    encode_image_reference,
    image_reference_filename,
    read_image_reference,
)

DOUBAO_MODEL = "doubao-seedream-5-0-pro-260628"
DOUBAO_URL = "https://ark.cn-beijing.volces.com/api/v3"


def _png_bytes(size=(3, 2)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _doubao(base_url=DOUBAO_URL) -> doubao.DoubaoImageBackend:
    return doubao.DoubaoImageBackend(ProviderCredentials(base_url, "test-key", DOUBAO_MODEL))


# ---------------- 注册表 / 渠道声明 ----------------


def test_builtin_registry_lists_every_provider_module_in_order():
    registry = default_registry()
    assert registry.ids == ("gemini", "openai_images", "qwen_image", "doubao_image")
    assert len(registry) == len(BUILTIN_PROVIDER_MODULES)
    assert registry.default_id == "gemini"
    for spec in registry:
        assert spec.default_model in spec.models()
        assert "aspect_ratio" in spec.capabilities()["options"]


def test_registry_rejects_duplicates_and_unknown_ids():
    log = FakeBackendLog()
    registry = ProviderRegistry([make_fake_spec(log, "fake")])
    with pytest.raises(ValueError):
        registry.register(make_fake_spec(log, "fake"))
    with pytest.raises(UnknownProviderError) as caught:
        registry.get("nope")
    assert str(caught.value) == "未知图片生成渠道: nope"
    assert "fake" in registry and "nope" not in registry


def test_model_override_does_not_mutate_provider_defaults():
    spec = make_fake_spec(
        FakeBackendLog(),
        model_overrides={
            "small": {
                "label": "小模型",
                "options": {"image_size": {"values": ["1K"], "default": "1K"}, "aspect_ratio": None},
            }
        },
    )

    resolved = spec.capabilities("small")
    defaults = spec.capabilities()

    assert resolved["label"] == "小模型"
    assert resolved["options"]["image_size"]["values"] == ["1K"]
    assert resolved["options"]["image_size"]["label"] == "尺寸"  # 未覆盖的属性保留
    assert "aspect_ratio" not in resolved["options"]
    assert defaults["options"]["image_size"]["values"] == ["1K", "2K"]
    assert "aspect_ratio" in defaults["options"]


def test_resolve_options_drops_unknown_and_empty_values():
    spec = make_fake_spec(FakeBackendLog())
    assert spec.resolve_options(
        "fake-model", {"aspect_ratio": "16:9", "image_size": "", "bogus": "x"}
    ) == {"aspect_ratio": "16:9"}
    # fake-model-lite 把 image_size 整个移除了
    assert spec.resolve_options("fake-model-lite", {"image_size": "2K"}) == {}


def test_configured_model_is_appended_to_suggestions():
    spec = make_fake_spec(FakeBackendLog())
    assert spec.models("custom") == ["fake-model", "fake-model-lite", "custom"]
    assert spec.models("fake-model") == ["fake-model", "fake-model-lite"]


def test_qwen_exposes_only_supported_model_and_hides_watermark():
    spec = default_registry().get("qwen_image")
    assert spec.model_suggestions == ("qwen-image-3.0-pro",)
    assert "watermark" not in spec.capabilities()["options"]
    assert spec.max_reference_images == 3


def test_doubao_defaults_and_generation_options():
    spec = default_registry().get("doubao_image")
    assert spec.default_base_url == DOUBAO_URL
    assert spec.default_model == DOUBAO_MODEL
    options = spec.capabilities()["options"]
    assert options["image_size"]["values"] == ["1K", "1.5K", "2K"]
    assert options["output_format"]["values"] == ["png", "jpeg"]
    assert options["watermark"]["default"] == "false"


def test_registry_factory_creates_the_doubao_backend():
    spec = default_registry().get("doubao_image")
    backend = spec.factory(ProviderCredentials(spec.default_base_url, "test-key", "custom-model"))
    assert isinstance(backend, doubao.DoubaoImageBackend)
    assert backend.model == "custom-model"
    assert backend.base_url == DOUBAO_URL


def test_backends_satisfy_the_stateless_protocol():
    assert isinstance(_doubao(), ImageBackend)
    assert isinstance(
        qwen.QwenImageBackend(ProviderCredentials("https://q.example/api/v1", "k", "m")),
        ImageBackend,
    )
    assert isinstance(
        openai_images.OpenAIImagesBackend(ProviderCredentials("https://o.example/v1", "k", "m")),
        ImageBackend,
    )


def test_image_result_encodes_png():
    result = ImageResult(Image.new("RGB", (4, 3), "red"), "fake", "fake-model")
    assert Image.open(BytesIO(result.to_png_bytes())).size == (4, 3)
    assert result.to_data_url().startswith("data:image/png;base64,")


# ---------------- 参考图 ----------------


def test_image_reference_forms(tmp_path):
    image_path = tmp_path / "ref.jpg"
    image_path.write_bytes(b"jpeg-bytes")
    data_url = "data:image/webp;base64," + base64.b64encode(b"webp-bytes").decode()

    assert encode_image_reference(str(image_path)) == (
        "data:image/jpeg;base64," + base64.b64encode(b"jpeg-bytes").decode()
    )
    assert encode_image_reference(data_url) == data_url
    assert encode_image_reference("https://example.com/a.png") == "https://example.com/a.png"

    assert read_image_reference(str(image_path)) == (b"jpeg-bytes", "image/jpeg")
    assert read_image_reference(data_url) == (b"webp-bytes", "image/webp")
    assert image_reference_filename(0, "image/webp") == "reference_0.webp"
    assert image_reference_filename(1, "image/unknown") == "reference_1.png"


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_empty_image_reference_is_rejected(bad):
    with pytest.raises(ValueError):
        encode_image_reference(bad)
    with pytest.raises(ValueError):
        read_image_reference(bad)


def test_missing_file_and_remote_url_errors(tmp_path):
    with pytest.raises(ValueError, match="参考图文件不存在"):
        encode_image_reference(str(tmp_path / "missing.png"))
    with pytest.raises(ValueError, match="远程 URL"):
        read_image_reference("https://example.com/a.png")


# ---------------- 豆包 ----------------


def test_doubao_full_generation_endpoint_is_normalized_to_openai_base_url():
    backend = _doubao(f"{DOUBAO_URL}/images/generations")
    assert backend.base_url == DOUBAO_URL


def test_doubao_request_kwargs_include_seedream_options_and_local_reference(tmp_path):
    image_path = tmp_path / "reference.png"
    image_path.write_bytes(b"reference-bytes")

    kwargs = _doubao().build_request_kwargs(
        "test prompt",
        [str(image_path)],
        {
            "aspect_ratio": "16:9",
            "image_size": "2K",
            "output_format": "jpeg",
            "watermark": "true",
            "optimize_prompt_mode": "fast",
        },
    )

    assert kwargs["model"] == DOUBAO_MODEL
    assert kwargs["prompt"] == "test prompt"
    assert kwargs["size"] == "2816x1584"
    assert kwargs["output_format"] == "jpeg"
    assert kwargs["response_format"] == "b64_json"
    assert kwargs["extra_body"]["watermark"] is True
    assert kwargs["extra_body"]["optimize_prompt_options"] == {"mode": "fast"}
    assert kwargs["extra_body"]["image"].startswith("data:image/png;base64,")


def test_doubao_generate_parses_base64_response():
    backend = _doubao()
    response = SimpleNamespace(
        data=[SimpleNamespace(b64_json=base64.b64encode(_png_bytes()).decode("ascii"), url=None)]
    )
    backend.client = SimpleNamespace(images=SimpleNamespace(generate=lambda **_kwargs: response))

    generated = backend.generate("test prompt", (), {})

    assert generated is not None
    assert generated.size == (3, 2)


def test_doubao_api_error_preserves_server_response_details():
    backend = _doubao()
    request_id = "0217866875428522f7309b89ef4aa83d5a6323dac40bcdef47e0e"
    error_body = {
        "error": {
            "code": "OutputImageSensitiveContentDetected.PolicyViolation",
            "message": (
                "The request failed because the output image may be related "
                f"to copyright restrictions. Request id: {request_id}"
            ),
            "param": "",
            "type": "BadRequestError",
        }
    }
    http_client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(400, json=error_body))
    )
    backend.client = OpenAI(api_key="test-key", base_url=backend.base_url, http_client=http_client)
    try:
        with pytest.raises(RuntimeError) as caught:
            backend.generate("test prompt", (), {})
    finally:
        backend.client.close()

    error_text = str(caught.value)
    assert "Error code: 400" in error_text
    assert error_body["error"]["code"] in error_text
    assert error_body["error"]["message"] in error_text
    assert "'param': ''" in error_text
    assert "'type': 'BadRequestError'" in error_text
    assert request_id in error_text
    assert "请移除作品名" not in error_text


def test_openai_sdk_serializes_doubao_request_body():
    backend = _doubao()
    captured = {}

    def handle_request(request):
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"data": [{"b64_json": base64.b64encode(_png_bytes((1, 1))).decode("ascii")}]}
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handle_request))
    backend.client = OpenAI(api_key="test-key", base_url=backend.base_url, http_client=http_client)
    try:
        generated = backend.generate(
            "test prompt",
            ["https://example.com/reference.png"],
            {
                "aspect_ratio": "4:3",
                "image_size": "1.5K",
                "output_format": "png",
                "watermark": "false",
                "optimize_prompt_mode": "standard",
            },
        )
    finally:
        backend.client.close()

    assert generated is not None
    assert captured["path"] == "/api/v3/images/generations"
    assert captured["body"] == {
        "model": DOUBAO_MODEL,
        "prompt": "test prompt",
        "size": "1792x1344",
        "output_format": "png",
        "response_format": "b64_json",
        "watermark": False,
        "optimize_prompt_options": {"mode": "standard"},
        "image": "https://example.com/reference.png",
    }


def test_doubao_sends_at_most_ten_references_as_a_list():
    refs = [f"https://example.com/{index}.png" for index in range(12)]
    kwargs = _doubao().build_request_kwargs("p", refs, {})
    assert kwargs["extra_body"]["image"] == refs[:10]
    assert kwargs["size"] == "2048x2048"  # 默认 2K 1:1


# ---------------- OpenAI Images ----------------


def _openai_backend() -> openai_images.OpenAIImagesBackend:
    return openai_images.OpenAIImagesBackend(
        ProviderCredentials("https://o.example/v1/", "test-key", "gpt-image-2")
    )


def test_openai_images_request_kwargs_skip_auto_values():
    backend = _openai_backend()
    assert backend.build_request_kwargs(
        "p", {"aspect_ratio": "16:9", "image_size": "1K", "quality": "auto", "output_format": "webp"}
    ) == {"model": "gpt-image-2", "prompt": "p", "size": "1536x864", "output_format": "webp"}
    assert openai_images.resolve_size({}) == "2048x2048"
    assert openai_images.resolve_size({"image_size": "bogus", "aspect_ratio": "bogus"}) == "2048x2048"


def test_openai_images_edit_accepts_paths_and_data_urls(tmp_path):
    """Web 端传来的参考图是 data URL，不能再假设一定是本地文件。"""
    image_path = tmp_path / "ref.png"
    image_path.write_bytes(b"png-bytes")
    data_url = "data:image/jpeg;base64," + base64.b64encode(b"jpeg-bytes").decode()
    calls = {}
    response = SimpleNamespace(
        data=[SimpleNamespace(b64_json=base64.b64encode(_png_bytes()).decode(), url=None)]
    )
    backend = _openai_backend()
    backend.client = SimpleNamespace(
        images=SimpleNamespace(
            edit=lambda **kwargs: calls.update(edit=kwargs) or response,
            generate=lambda **kwargs: calls.update(generate=kwargs) or response,
        )
    )

    assert backend.generate("p", [str(image_path), data_url], {}).size == (3, 2)
    assert "generate" not in calls
    assert calls["edit"]["image"] == [
        ("reference_0.png", b"png-bytes", "image/png"),
        ("reference_1.jpg", b"jpeg-bytes", "image/jpeg"),
    ]

    backend.generate("p", [data_url], {})
    assert calls["edit"]["image"] == ("reference_0.jpg", b"jpeg-bytes", "image/jpeg")

    backend.generate("p", (), {})
    assert calls["generate"]["prompt"] == "p"


def test_openai_images_retries_with_core_fields_on_incompatible_gateway():
    seen = []

    def generate(**kwargs):
        seen.append(kwargs)
        if "quality" in kwargs:
            raise TypeError("unexpected keyword argument 'quality'")
        return SimpleNamespace(data=[])

    backend = _openai_backend()
    backend.client = SimpleNamespace(images=SimpleNamespace(generate=generate))

    assert backend.generate("p", (), {"quality": "high"}) is None
    assert [sorted(kwargs) for kwargs in seen] == [
        ["model", "prompt", "quality", "size"],
        ["model", "prompt", "size"],
    ]


# ---------------- 千问 ----------------


def test_qwen_endpoint_normalization():
    make = lambda url: qwen.QwenImageBackend(ProviderCredentials(url, "k", "m")).endpoint  # noqa: E731
    full = "https://ws.cn-beijing.maas.aliyuncs.com/api/v1" + qwen.QWEN_GENERATION_PATH
    assert make("https://ws.cn-beijing.maas.aliyuncs.com/api/v1/") == full
    assert make(full) == full
    with pytest.raises(ValueError):
        make("  ")


def test_qwen_content_and_parameters():
    content = qwen.QwenImageBackend.build_content(
        "画", [f"https://example.com/{index}.png" for index in range(5)]
    )
    assert [list(item) for item in content] == [["image"], ["image"], ["image"], ["text"]]
    assert content[-1] == {"text": "画"}

    parameters = qwen.QwenImageBackend.build_parameters(
        {"aspect_ratio": "16:9", "image_size": "2K", "prompt_extend": "false", "prompt_extend_mode": "agent"},
        has_refs=True,
    )
    assert parameters == {
        "n": 1,
        "prompt_extend": False,
        "prompt_extend_mode": "direct",  # 图生图不支持 agent
        "watermark": False,
        "size": "2688*1536",
    }
    assert "size" not in qwen.QwenImageBackend.build_parameters({}, has_refs=False)
    assert qwen.QwenImageBackend.build_parameters({"prompt_extend_mode": "agent"}, has_refs=False)[
        "prompt_extend_mode"
    ] == "agent"


def test_qwen_generate_posts_payload_and_downloads_result(monkeypatch):
    backend = qwen.QwenImageBackend(ProviderCredentials("https://q.example/api/v1", "secret", "qwen-m"))
    requests = []

    def fake_request(method, url, *, content=None, headers=None, timeout=120.0):
        requests.append((method, url, content, headers))
        if method == "POST":
            body = {"output": {"choices": [{"message": {"content": [{"image": "https://cdn/x.png"}]}}]}}
            return json.dumps(body).encode()
        return _png_bytes((5, 4))

    monkeypatch.setattr(backend, "_http_request", fake_request)

    image = backend.generate("画一只猫", (), {"image_size": "1K"})

    assert image.size == (5, 4)
    method, url, content, headers = requests[0]
    assert (method, url) == ("POST", "https://q.example/api/v1" + qwen.QWEN_GENERATION_PATH)
    assert headers["Authorization"] == "Bearer secret"
    payload = json.loads(content)
    assert payload["model"] == "qwen-m"
    assert payload["input"]["messages"][0]["content"] == [{"text": "画一只猫"}]
    assert payload["parameters"]["size"] == "1024*1024"
    assert requests[1][:2] == ("GET", "https://cdn/x.png")


def test_qwen_business_error_is_surfaced(monkeypatch):
    backend = qwen.QwenImageBackend(ProviderCredentials("https://q.example/api/v1", "k", "m"))
    monkeypatch.setattr(
        backend,
        "_http_request",
        lambda *_args, **_kwargs: json.dumps(
            {"code": "DataInspectionFailed", "message": "内容违规", "request_id": "req-1"}
        ).encode(),
    )
    with pytest.raises(RuntimeError) as caught:
        backend.generate("p", (), {})
    assert str(caught.value) == (
        "千问图像请求失败: code=DataInspectionFailed, message=内容违规, request_id=req-1"
    )
