"""Studio 门面：交互口能做的事都在这里，所以这里的测试就是「交互口契约」。"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from nano_banana.core import (
    ImageGenerationError,
    ImageRequest,
    NotConfiguredError,
    StudioError,
    UnknownProviderError,
)
from nano_banana.core.prompt import build_document


def _configure_chat(studio, **overrides):
    chat = {"base_url": "https://chat.example/v1", "api_key": "chat-key", "model": "chat-model"}
    chat.update(overrides)
    studio.settings.update({"chat": chat})


def _configure_image(studio, provider="fake", **overrides):
    creds = {"api_key": "image-key"}
    creds.update(overrides)
    studio.settings.update({"image": {"providers": {provider: creds}}})


class FakeHttpClient:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def _chunk(content="", reasoning=None):
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content, reasoning_content=reasoning))]
    )


class FakeChat:
    """替身 OpenAI 客户端：记录请求并回放预设的流。"""

    def __init__(self, chunks=(), error=None):
        self.chunks = list(chunks)
        self.error = error
        self.requests = []
        self.http_client = FakeHttpClient()
        self.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=self._create))
        )

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        if self.error is not None:
            raise self.error
        return iter(self.chunks)

    def patch(self):
        return patch(
            "nano_banana.core.studio.create_chat_client",
            return_value=(self.client, self.http_client),
        )


# ================= 提示词 =================


def test_render_migrates_legacy_documents_first(studio):
    rendered = studio.render({"反向提示词": {"禁止元素": ["水印"], "禁止风格": []}})
    assert rendered.payload == {"反向提示词": "水印"}


def test_generate_prompt_requires_configuration_and_input(studio):
    with pytest.raises(NotConfiguredError, match="API密钥"):
        studio.generate_prompt("a forest")

    _configure_chat(studio, base_url="")
    with pytest.raises(NotConfiguredError, match="Base URL"):
        studio.generate_prompt("a forest")

    _configure_chat(studio)
    with pytest.raises(StudioError, match="文字描述或参考图片"):
        studio.generate_prompt("   ")
    with pytest.raises(StudioError, match="修改要求不能为空"):
        studio.modify_prompt({}, "  ")


def test_generate_prompt_streams_events_and_parses_the_result(studio):
    _configure_chat(studio)
    chat = FakeChat(
        [_chunk(reasoning="hmm"), _chunk(reasoning="more"), _chunk('```json\n{"风格模式":'), _chunk(' "插画"}\n```')]
    )

    with chat.patch() as create_client:
        events = list(studio.generate_prompt("a forest"))

    create_client.assert_called_once_with(base_url="https://chat.example/v1", api_key="chat-key")
    assert [event.type for event in events] == ["started", "thinking", "content", "content", "result"]
    result = events[-1]
    assert result.text == '```json\n{"风格模式": "插画"}\n```'
    assert result.document == {"风格模式": "插画"}
    assert result.parse_error == "" and result.changes == ()
    assert chat.requests[0]["model"] == "chat-model"
    assert chat.requests[0]["stream"] is True
    assert "a forest" in chat.requests[0]["messages"][1]["content"]
    assert chat.http_client.closed


def test_started_is_emitted_before_the_upstream_request(studio):
    _configure_chat(studio, model="")
    chat = FakeChat([_chunk("{}")])

    with chat.patch():
        events = studio.generate_prompt("a forest")
        assert next(events).type == "started"
        assert chat.requests == []  # 还没打上游
        events.close()  # 调用方中途放弃

    assert chat.requests == []
    assert chat.http_client.closed


def test_default_chat_model_is_used_when_none_is_configured(studio):
    _configure_chat(studio, model="")
    chat = FakeChat([_chunk("{}")])
    with chat.patch():
        list(studio.generate_prompt("x"))
    assert chat.requests[0]["model"] == "gpt-4o-mini"


def test_unparseable_output_is_reported_not_raised(studio):
    _configure_chat(studio)
    with FakeChat([_chunk("抱歉，我做不到")]).patch():
        result = list(studio.generate_prompt("x"))[-1]

    assert result.type == "result"
    assert result.document is None
    assert result.text == "抱歉，我做不到"
    assert "JSON" in result.parse_error


def test_upstream_failure_becomes_a_friendly_error_event(studio):
    _configure_chat(studio)
    chat = FakeChat(error=RuntimeError("Error code: 401 Unauthorized"))
    with chat.patch():
        events = list(studio.generate_prompt("x"))

    assert [event.type for event in events] == ["started", "error"]
    assert events[-1].text == "API密钥无效或已过期，请检查配置"
    assert chat.http_client.closed


def test_bad_reference_image_is_an_error_event_before_any_network_call(studio, tmp_path):
    _configure_chat(studio)
    with patch("nano_banana.core.studio.create_chat_client") as create_client:
        events = list(studio.generate_prompt("x", [str(tmp_path / "missing.png")]))

    assert [event.type for event in events] == ["error"]
    assert "参考图文件不存在" in events[0].text
    create_client.assert_not_called()


def test_images_only_generation_is_allowed(studio):
    _configure_chat(studio)
    chat = FakeChat([_chunk("{}")])
    with chat.patch():
        list(studio.generate_prompt("", ["https://example.com/ref.png"]))

    parts = chat.requests[0]["messages"][1]["content"]
    assert parts[0] == {"type": "image_url", "image_url": {"url": "https://example.com/ref.png"}}
    assert parts[1] == {"type": "text", "text": "请根据参考图片生成提示词。"}


def test_cancellation_stops_the_stream(studio):
    _configure_chat(studio)
    cancelled = []
    chat = FakeChat([_chunk("a"), _chunk("b"), _chunk("c")])

    with chat.patch():
        events = []
        for event in studio.generate_prompt("x", cancelled=lambda: bool(cancelled)):
            events.append(event)
            if event.type == "content":
                cancelled.append(True)

    assert [event.type for event in events] == ["started", "content", "error"]
    assert events[-1].text == "已取消"


def test_modify_prompt_hides_ui_only_parts_from_the_model_and_diffs_the_rest(studio):
    _configure_chat(studio)
    current = build_document(
        {"styleMode": "插画", "location": "海边"},
        negative_prompt="水印",
        special_requirement="机密要求",
        line_art_prompt="机密线稿",
    )
    modified = dict(studio.render(current).payload, 风格模式="写实")
    import json

    chat = FakeChat([_chunk(json.dumps(modified, ensure_ascii=False))])
    with chat.patch():
        events = list(studio.modify_prompt(current, "改成写实"))

    sent = chat.requests[0]["messages"][1]["content"]
    assert "改成写实" in sent and "海边" in sent and "水印" in sent
    assert "机密要求" not in sent and "机密线稿" not in sent

    result = events[-1]
    assert [(change.label, change.kind, change.old, change.new) for change in result.changes] == [
        ("风格模式", "changed", "插画", "写实")
    ]

    # 应用差异后，模型没见过的 overlay 原样保留
    final = studio.apply_changes(current, result.changes)
    assert final["风格模式"] == "写实"
    assert final["特别要求"] == "机密要求"
    assert final["角色线稿生成"] == current["角色线稿生成"]
    assert studio.apply_changes(current, []) == current
    assert studio.diff(current, final) == list(result.changes)


# ================= 生图 =================


def test_provider_statuses_describe_every_channel_without_secrets(fake_studio):
    _configure_image(fake_studio, "fake", model="custom-model")

    statuses = {status.id: status for status in fake_studio.provider_statuses()}

    assert list(statuses) == ["fake", "other"]
    fake = statuses["fake"]
    assert (fake.has_api_key, fake.is_configured) == (True, True)
    assert fake.base_url == ""  # 用户没填，界面上显示占位符
    assert fake.configured_model == "custom-model"
    assert fake.models == ("fake-model", "fake-model-lite", "custom-model")
    assert set(fake.capabilities) == set(fake.models)
    assert "image_size" not in fake.capabilities["fake-model-lite"]["options"]
    assert (statuses["other"].has_api_key, statuses["other"].is_configured) == (False, False)

    data = fake.to_dict()
    assert "image-key" not in str(data)
    assert "api_key" not in data


def test_generate_image_passes_a_complete_stateless_request_to_the_backend(fake_studio, backend_log):
    _configure_image(fake_studio, "other", base_url="https://other.example/v1", model="stored-model")

    result = fake_studio.generate_image(
        ImageRequest(
            prompt="a cat",
            provider="other",
            model="requested-model",
            images=("https://example.com/ref.png",),
            options={"aspect_ratio": "16:9", "bogus": "x", "image_size": ""},
        )
    )

    assert (result.provider, result.model) == ("other", "requested-model")
    assert result.to_png_bytes()
    credentials = backend_log.credentials[0]
    assert (credentials.base_url, credentials.api_key, credentials.model) == (
        "https://other.example/v1",
        "image-key",
        "requested-model",
    )
    assert backend_log.calls == [
        {
            "prompt": "a cat",
            "images": ("https://example.com/ref.png",),
            "options": {"aspect_ratio": "16:9"},  # 渠道不认识的键和空值被丢掉
        }
    ]


def test_generate_image_remembers_selection_and_options_by_default(fake_studio):
    _configure_image(fake_studio, "other")

    fake_studio.generate_image(
        ImageRequest(prompt="p", provider="other", model="fake-model-lite", options={"aspect_ratio": "3:2"})
    )
    assert fake_studio.settings.active_provider() == "other"
    assert fake_studio.settings.credentials("other").model == "fake-model-lite"
    assert fake_studio.settings.generation_options("other", "fake-model-lite") == {"aspect_ratio": "3:2"}

    # 插件等一次性调用可以选择不留痕
    fake_studio.generate_image(
        ImageRequest(prompt="p", provider="other", model="one-off", options={"aspect_ratio": "1:1"}, remember=False)
    )
    assert fake_studio.settings.credentials("other").model == "fake-model-lite"
    assert fake_studio.settings.generation_options("other", "one-off") == {}


def test_generate_image_defaults_to_the_active_provider_and_stored_model(fake_studio, backend_log):
    _configure_image(fake_studio, "other")
    fake_studio.settings.set_active_selection("other", "fake-model-lite")

    result = fake_studio.generate_image(ImageRequest(prompt="p"))

    assert (result.provider, result.model) == ("other", "fake-model-lite")
    assert backend_log.credentials[0].base_url == "https://fake.example/v1"  # 渠道默认地址


def test_generate_image_validates_before_touching_the_backend(fake_studio, backend_log):
    with pytest.raises(UnknownProviderError):
        fake_studio.generate_image(ImageRequest(prompt="p", provider="nope"))
    with pytest.raises(NotConfiguredError, match="Fake fake"):
        fake_studio.generate_image(ImageRequest(prompt="p", provider="fake"))

    _configure_image(fake_studio, "fake")
    with pytest.raises(StudioError, match="提示词不能为空"):
        fake_studio.generate_image(ImageRequest(prompt="  ", provider="fake"))

    assert backend_log.credentials == [] and backend_log.calls == []
    assert fake_studio.settings.generation_options("fake", "fake-model") == {}


def test_generate_image_propagates_backend_errors_verbatim(fake_studio, backend_log):
    _configure_image(fake_studio, "fake")
    backend_log.error = RuntimeError("上游原始错误 request-123")

    with pytest.raises(RuntimeError, match="上游原始错误 request-123"):
        fake_studio.generate_image(ImageRequest(prompt="p", provider="fake"))


def test_generate_image_without_a_returned_image_is_an_error(fake_studio):
    from conftest import FakeBackendLog, make_fake_spec

    from nano_banana.core import ProviderRegistry, Studio

    class EmptyBackend:
        def __init__(self, _credentials):
            pass

        def generate(self, prompt, images, options):
            return None

    registry = ProviderRegistry([make_fake_spec(FakeBackendLog(), "empty", factory=EmptyBackend)])
    studio = Studio(fake_studio.paths, registry=registry)
    _configure_image(studio, "empty")

    with pytest.raises(ImageGenerationError):
        studio.generate_image(ImageRequest(prompt="p", provider="empty"))


def test_capabilities_follow_the_selected_model(fake_studio):
    assert "image_size" in fake_studio.capabilities("fake", "fake-model")["options"]
    assert "image_size" not in fake_studio.capabilities("fake", "fake-model-lite")["options"]
    with pytest.raises(UnknownProviderError):
        fake_studio.capabilities("nope")
