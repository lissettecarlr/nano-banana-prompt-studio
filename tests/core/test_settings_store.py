import threading

import pytest
import yaml

from nano_banana.core import UnknownProviderError
from nano_banana.core.images.registry import default_registry
from nano_banana.core.storage.settings import SettingsStore


@pytest.fixture
def store(tmp_path) -> SettingsStore:
    return SettingsStore(tmp_path / "config" / "ai_config.yaml", default_registry())


def _write(store: SettingsStore, data) -> None:
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _on_disk(store: SettingsStore) -> dict:
    return yaml.safe_load(store.path.read_text(encoding="utf-8"))


def test_missing_file_reads_as_empty_config_with_default_provider(store):
    assert store.chat().api_key == ""
    assert store.active_provider() == "gemini"
    assert store.providers_with_api_key() == []
    assert not store.path.exists()  # 读操作不落盘


def test_legacy_flat_yaml_is_understood_and_rewritten_nested(store):
    _write(
        store,
        {
            "base_url": "https://chat.example/v1",
            "api_key": "chat-key",
            "model": "chat-model",
            "image_provider": "openai_images",
            "openai_image_base_url": "https://images.example/v1",
            "openai_image_api_key": "image-key",
            "openai_image_model": "image-model",
            "image_generation_options": {"openai_images": {"image-model": {"quality": "high"}}},
        },
    )

    assert store.chat().api_key == "chat-key"
    assert store.active_provider() == "openai_images"
    assert store.credentials("openai_images").api_key == "image-key"
    assert store.generation_options("openai_images", "image-model") == {"quality": "high"}

    store.update({"model": "new-chat-model"})  # 旧版扁平补丁
    written = _on_disk(store)
    assert set(written) == {"chat", "image"}
    assert written["chat"] == {
        "base_url": "https://chat.example/v1",
        "api_key": "chat-key",
        "model": "new-chat-model",
    }
    assert written["image"]["providers"]["openai_images"]["api_key"] == "image-key"


def test_chat_and_image_credentials_are_isolated(store):
    store.update(
        {
            "chat": {"base_url": "https://chat.example/v1", "api_key": "chat-key", "model": "chat-model"},
            "image": {"providers": {"openai_images": {"api_key": "image-key", "model": "image-model"}}},
        }
    )

    store.set_active_selection("openai_images", "new-image-model")

    assert store.chat().model == "chat-model"
    assert store.credentials("openai_images").model == "new-image-model"
    assert store.credentials("openai_images").api_key == "image-key"
    assert store.active_provider() == "openai_images"


def test_partial_patch_never_clears_other_keys(store):
    store.update({"image": {"providers": {"gemini": {"base_url": "https://g", "api_key": "k"}}}})
    store.update({"image": {"providers": {"gemini": {"model": "m"}}}})

    credentials = store.credentials("gemini")
    assert (credentials.base_url, credentials.api_key, credentials.model) == ("https://g", "k", "m")


def test_credentials_fall_back_to_provider_defaults(store):
    credentials = store.credentials("doubao_image")
    assert credentials.base_url == "https://ark.cn-beijing.volces.com/api/v3"
    assert credentials.model == "doubao-seedream-5-0-pro-260628"
    assert credentials.api_key == ""


def test_image_provider_requires_complete_connection(store):
    _write(store, {"gemini_api_key": "image-key", "gemini_model": "gemini-model", "gemini_base_url": ""})
    assert not store.is_provider_configured("gemini")  # gemini 没有默认 base_url

    store.update({"gemini_base_url": "https://gemini.example"})
    assert store.is_provider_configured("gemini")


def test_provider_choices_include_only_non_empty_api_keys(store):
    _write(
        store,
        {
            "gemini_api_key": " gemini-key ",
            "openai_image_api_key": "   ",
            "qwen_image_api_key": "qwen-key",
            "doubao_image_api_key": "doubao-key",
        },
    )
    assert store.providers_with_api_key() == ["gemini", "qwen_image", "doubao_image"]


def test_generation_options_are_scoped_by_provider_and_model(store):
    store.save_generation_options("gemini", "model-a", {"aspect_ratio": "16:9", "image_size": "4K"})
    store.save_generation_options("gemini", "model-b", {"aspect_ratio": "1:1", "image_size": "1K"})

    assert store.generation_options("gemini", "model-a")["image_size"] == "4K"
    assert store.generation_options("gemini", "model-b")["image_size"] == "1K"
    assert store.generation_options("openai_images", "model-a") == {}

    store.save_generation_options("gemini", "", {"aspect_ratio": "3:2"})
    assert store.generation_options("gemini") == {"aspect_ratio": "3:2"}


def test_unknown_provider_is_rejected_everywhere(store):
    with pytest.raises(UnknownProviderError):
        store.update({"image": {"active": "nope"}})
    with pytest.raises(UnknownProviderError):
        store.set_active_selection("nope", "m")
    with pytest.raises(UnknownProviderError):
        store.credentials("nope")
    with pytest.raises(ValueError):
        store.update(["not", "a", "dict"])
    assert not store.path.exists()


def test_public_view_never_contains_secrets(store):
    store.update(
        {
            "chat": {"api_key": "chat-secret", "base_url": "https://chat"},
            "image": {"providers": {"gemini": {"api_key": "image-secret"}}},
        }
    )
    view = store.public_view()

    assert "secret" not in yaml.safe_dump(view)
    assert view["chat"] == {"base_url": "https://chat", "model": "", "has_api_key": True}
    assert view["image"]["providers"]["gemini"]["has_api_key"] is True
    assert view["image"]["providers"]["qwen_image"]["has_api_key"] is False
    assert set(view["image"]["providers"]) == set(default_registry().ids)


def test_unknown_providers_on_disk_survive_a_rewrite(store):
    """降级/升级版本时，不认识的渠道配置不能被悄悄丢掉。"""
    _write(
        store,
        {"image": {"active": "future", "providers": {"future": {"api_key": "k", "model": "m"}}}},
    )
    assert store.active_provider() == "gemini"  # 不认识的渠道不会被当成当前渠道

    store.update({"chat": {"model": "x"}})
    assert _on_disk(store)["image"]["providers"]["future"]["api_key"] == "k"


def test_corrupt_file_is_backed_up_before_being_overwritten(store):
    store.path.parent.mkdir(parents=True)
    store.path.write_text("chat: [unclosed", encoding="utf-8")

    assert store.chat().api_key == ""
    store.update({"chat": {"api_key": "new"}})

    backups = list(store.path.parent.glob("ai_config.yaml.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "chat: [unclosed"
    assert store.chat().api_key == "new"


def test_concurrent_updates_do_not_lose_writes(store):
    def save(index: int):
        store.save_generation_options("gemini", f"model-{index}", {"n": index})

    threads = [threading.Thread(target=save, args=(index,)) for index in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    for index in range(12):
        assert store.generation_options("gemini", f"model-{index}") == {"n": index}
    assert not list(store.path.parent.glob("*.tmp*"))
