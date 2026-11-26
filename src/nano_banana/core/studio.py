"""Studio：核心的组合根 + 用例门面。

所有交互口（桌面、Web、CLI、插件……）只通过这个类使用核心能力：
交互口负责收集输入、调用 Studio、展示结果，不直接碰渠道实现和存储细节。
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any

from nano_banana.core.images.registry import ProviderRegistry, default_registry
from nano_banana.core.images.types import (
    ImageGenerationError,
    ImageRequest,
    ImageResult,
    ProviderCredentials,
)
from nano_banana.core.llm.chat import (
    DEFAULT_CHAT_MODEL,
    build_generate_messages,
    build_modify_messages,
    create_chat_client,
    format_chat_error,
    iter_completion_events,
)
from nano_banana.core.prompt.diff import Change, apply_changes, diff_documents
from nano_banana.core.prompt.migrate import migrate_document
from nano_banana.core.prompt.parse import PromptParseError, parse_ai_document
from nano_banana.core.prompt.render import (
    RenderedPrompt,
    payload_json,
    prompt_payload,
    render_prompt,
)
from nano_banana.core.prompt.schema import PromptSchema, get_schema, overlay_by_id
from nano_banana.core.storage.legacy import import_legacy_user_data
from nano_banana.core.storage.options import OptionsStore
from nano_banana.core.storage.paths import StudioPaths
from nano_banana.core.storage.presets import PresetStore
from nano_banana.core.storage.settings import ChatSettings, SettingsStore

CancelledFn = Callable[[], bool]

EVENT_STARTED = "started"
EVENT_THINKING = "thinking"
EVENT_CONTENT = "content"
EVENT_RESULT = "result"
EVENT_ERROR = "error"


class StudioError(Exception):
    """可以直接展示给用户的业务错误（输入不合法、未配置等）。"""


class NotConfiguredError(StudioError):
    """缺少必要的连接配置。"""


@dataclass(frozen=True)
class PromptEvent:
    """AI 生成 / 修改提示词过程中的流式事件。

    - started：已受理，尚未请求上游；
    - thinking：模型进入推理阶段；
    - content：text 为新增的输出片段；
    - result：结束。text 为完整原始输出；document 为解析并升级后的文档
      （解析失败时为 None，原因在 parse_error）；修改场景下 changes 为相对原文档的差异；
    - error：text 为错误信息，流到此结束。
    """

    type: str
    text: str = ""
    document: dict[str, Any] | None = None
    changes: tuple[Change, ...] = ()
    parse_error: str = ""


@dataclass(frozen=True)
class ProviderStatus:
    """一个图片渠道的声明 + 当前配置状态，不含密钥。"""

    id: str
    label: str
    models: tuple[str, ...]
    default_model: str
    default_base_url: str
    url_placeholder: str
    model_suggestions: tuple[str, ...]
    base_url: str  # 用户填写的原值
    model: str  # 用户填写的原值
    configured_model: str  # 补齐默认值后实际会用的模型
    has_api_key: bool
    is_configured: bool
    capabilities: dict[str, dict[str, Any]]  # {model: capabilities}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "models": list(self.models),
            "default_model": self.default_model,
            "default_base_url": self.default_base_url,
            "url_placeholder": self.url_placeholder,
            "model_suggestions": list(self.model_suggestions),
            "base_url": self.base_url,
            "model": self.model,
            "configured_model": self.configured_model,
            "has_api_key": self.has_api_key,
            "is_configured": self.is_configured,
            "capabilities": self.capabilities,
        }


class Studio:
    def __init__(
        self,
        paths: StudioPaths | None = None,
        *,
        registry: ProviderRegistry | None = None,
        schema: PromptSchema | None = None,
    ):
        self.paths = paths or StudioPaths.default()
        self.schema = schema or get_schema()
        self.registry = registry or default_registry()

        self.settings = SettingsStore(self.paths.settings_file, self.registry)
        self.presets = PresetStore(self.paths.presets_dir, self.paths.builtin_presets_dir)
        negative = overlay_by_id("negativePrompt", self.schema)
        self.options = OptionsStore(
            self.paths.options_file,
            self.paths.builtin_options_file,
            fallback={negative.options_key: [negative.default]} if negative.options_key else None,
        )

    @classmethod
    def default(cls) -> "Studio":
        """用默认数据目录创建实例，供各交互口的启动入口使用。

        源码运行时顺带把重构前留在 src/config、src/presets 的数据导入一次。
        """
        paths = StudioPaths.default()
        import_legacy_user_data(paths)
        return cls(paths)

    # ================= 提示词文档 =================

    def migrate(self, document: dict[str, Any] | None) -> dict[str, Any]:
        """把任意来源（预设、草稿、旧版本）的文档升级到当前结构。"""
        return migrate_document(document, self.schema)

    def render(self, document: dict[str, Any] | None) -> RenderedPrompt:
        """文档 → 最终发给生图模型的文本。两端预览和实际请求都以它为准。"""
        return render_prompt(self.migrate(document), self.schema)

    def diff(self, old: dict[str, Any] | None, new: dict[str, Any] | None) -> list[Change]:
        """两份文档在模型可见部分上的差异。"""
        return diff_documents(
            prompt_payload(self.migrate(old), self.schema),
            prompt_payload(self.migrate(new), self.schema),
        )

    def apply_changes(
        self, document: dict[str, Any] | None, changes: Iterable[Change]
    ) -> dict[str, Any]:
        return apply_changes(self.migrate(document), changes)

    # ================= AI 生成 / 修改提示词 =================

    def chat_settings(self) -> ChatSettings:
        return self.settings.chat()

    def generate_prompt(
        self,
        text: str,
        images: Sequence[str] = (),
        *,
        cancelled: CancelledFn | None = None,
    ) -> Iterator[PromptEvent]:
        """根据描述 / 参考图生成一份新文档。配置或输入有问题时立即抛 StudioError。"""
        chat = self._require_chat()
        text = (text or "").strip()
        images = tuple(images or ())
        if not text and not images:
            raise StudioError("请提供文字描述或参考图片")

        def finalize(content: str) -> PromptEvent:
            return self._result_event(content)

        return self._stream_prompt(
            lambda: build_generate_messages(text, images), chat, cancelled, finalize
        )

    def modify_prompt(
        self,
        document: dict[str, Any] | None,
        request: str,
        images: Sequence[str] = (),
        *,
        cancelled: CancelledFn | None = None,
    ) -> Iterator[PromptEvent]:
        """按要求修改现有文档。ui_only 的部分（特别要求、线稿）不会发给模型。"""
        chat = self._require_chat()
        request = (request or "").strip()
        if not request:
            raise StudioError("修改要求不能为空")
        current = self.migrate(document)
        base_payload = prompt_payload(current, self.schema)
        images = tuple(images or ())

        def finalize(content: str) -> PromptEvent:
            event = self._result_event(content)
            if event.document is None:
                return event
            changes = diff_documents(base_payload, prompt_payload(event.document, self.schema))
            return PromptEvent(
                EVENT_RESULT, content, document=event.document, changes=tuple(changes)
            )

        return self._stream_prompt(
            lambda: build_modify_messages(payload_json(current, self.schema), request, images),
            chat,
            cancelled,
            finalize,
        )

    # ================= 生图 =================

    def provider_statuses(self) -> list[ProviderStatus]:
        stored = self.settings.read()["image"]["providers"]
        statuses = []
        for spec in self.registry:
            raw = stored.get(spec.id) or {}
            credentials = self.settings.credentials(spec.id)
            models = spec.models(credentials.model)
            statuses.append(
                ProviderStatus(
                    id=spec.id,
                    label=spec.label,
                    models=tuple(models),
                    default_model=spec.default_model,
                    default_base_url=spec.default_base_url,
                    url_placeholder=spec.url_placeholder,
                    model_suggestions=spec.model_suggestions,
                    base_url=raw.get("base_url") or "",
                    model=raw.get("model") or "",
                    configured_model=credentials.model,
                    has_api_key=bool(credentials.api_key),
                    is_configured=credentials.is_complete,
                    capabilities={model: spec.capabilities(model) for model in models},
                )
            )
        return statuses

    def capabilities(self, provider_id: str, model: str = "") -> dict[str, Any]:
        return self.registry.get(provider_id).capabilities(model)

    def generate_image(self, request: ImageRequest) -> ImageResult:
        """无状态生图：一次调用所需的全部输入都在 request 里。"""
        provider_id = request.provider or self.settings.active_provider()
        spec = self.registry.get(provider_id)
        stored = self.settings.credentials(provider_id)
        model = (request.model or "").strip() or stored.model
        if not model:
            raise StudioError("图片模型不能为空")
        if not (request.prompt or "").strip():
            raise StudioError("提示词不能为空")
        if not stored.base_url or not stored.api_key:
            raise NotConfiguredError(f"请先配置 {spec.label} Base URL 和 API Key")

        options = spec.resolve_options(model, request.options)
        if request.remember:
            self.settings.set_active_selection(provider_id, model)
            self.settings.save_generation_options(provider_id, model, dict(request.options))

        backend = spec.factory(
            ProviderCredentials(base_url=stored.base_url, api_key=stored.api_key, model=model)
        )
        image = backend.generate(request.prompt, tuple(request.images or ()), options)
        if image is None:
            raise ImageGenerationError("生成图片失败，未返回图片数据")
        return ImageResult(image=image, provider=provider_id, model=model)

    # ================= 内部 =================

    def _require_chat(self) -> ChatSettings:
        chat = self.settings.chat()
        if not chat.api_key:
            raise NotConfiguredError("请先配置API密钥")
        if not chat.base_url:
            raise NotConfiguredError("请先配置Base URL")
        return chat

    def _result_event(self, content: str) -> PromptEvent:
        try:
            document = parse_ai_document(content, self.schema)
        except PromptParseError as exc:
            return PromptEvent(EVENT_RESULT, content, parse_error=str(exc))
        return PromptEvent(EVENT_RESULT, content, document=document)

    @staticmethod
    def _stream_prompt(
        build_messages: Callable[[], list[dict[str, Any]]],
        chat: ChatSettings,
        cancelled: CancelledFn | None,
        finalize: Callable[[str], PromptEvent],
    ) -> Iterator[PromptEvent]:
        # 读参考图 + base64 可能很慢，放在生成器里，由调用方的工作线程承担
        try:
            messages = build_messages()
        except ValueError as exc:
            yield PromptEvent(EVENT_ERROR, str(exc))
            return
        try:
            client, http_client = create_chat_client(
                base_url=chat.base_url, api_key=chat.api_key
            )
        except ImportError as exc:
            yield PromptEvent(EVENT_ERROR, f"openai 导入失败: {exc}")
            return

        try:
            # 先让调用方知道已受理，再打上游（上游首包可能要等很久）
            yield PromptEvent(EVENT_STARTED)
            for event in iter_completion_events(
                client,
                messages,
                model=chat.model or DEFAULT_CHAT_MODEL,
                cancelled=cancelled,
            ):
                if event.type == "done":
                    yield finalize(event.text)
                    return
                if event.type == "error":
                    yield PromptEvent(EVENT_ERROR, event.text)
                    return
                yield PromptEvent(event.type, event.text)
        except Exception as exc:  # noqa: BLE001
            yield PromptEvent(EVENT_ERROR, format_chat_error(exc))
        finally:
            http_client.close()
