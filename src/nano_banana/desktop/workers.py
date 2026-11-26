"""后台线程：把 Studio 的阻塞调用搬出 UI 线程。这里不含任何业务逻辑。"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from nano_banana.core import ImageRequest, PromptEvent, Studio, StudioError

_PROGRESS_TEXT = {
    "started": "正在连接AI服务...",
    "thinking": "模型思考中...",
}


class PromptStreamThread(QThread):
    """消费 Studio.generate_prompt / modify_prompt 的事件流。"""

    progress = pyqtSignal(str)
    chunk = pyqtSignal(str)
    result = pyqtSignal(object)  # PromptEvent(type="result")
    error = pyqtSignal(str)

    def __init__(self, open_stream: Callable[[Callable[[], bool]], Iterable[PromptEvent]]):
        super().__init__()
        self._open_stream = open_stream
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            self.progress.emit("正在处理输入...")
            events = self._open_stream(lambda: self._cancelled)
            try:
                for event in events:
                    if self._cancelled:
                        return
                    if event.type == "content":
                        self.chunk.emit(event.text)
                    elif event.type == "result":
                        self.result.emit(event)
                    elif event.type == "error":
                        self.error.emit(event.text)
                    elif event.type in _PROGRESS_TEXT:
                        self.progress.emit(_PROGRESS_TEXT[event.type])
            finally:
                close = getattr(events, "close", None)
                if close:
                    close()  # 取消时立刻释放上游连接
        except StudioError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            if not self._cancelled:
                self.error.emit(f"发生未知错误: {exc}")


class PromptService:
    """对话框用的小门面：同一时间只跑一个提示词任务，可取消。"""

    def __init__(self, studio: Studio):
        self.studio = studio
        self._current: PromptStreamThread | None = None
        # 已取消但可能还在跑的线程：保住引用防止 QThread 运行中被析构
        self._stale: list[PromptStreamThread] = []

    def is_configured(self) -> bool:
        return self.studio.chat_settings().is_configured

    def generate(self, text: str, images: Sequence[str] = (), **callbacks) -> None:
        images = tuple(images or ())
        self._start(
            lambda cancelled: self.studio.generate_prompt(text, images, cancelled=cancelled),
            **callbacks,
        )

    def modify(
        self, document: dict[str, Any], request: str, images: Sequence[str] = (), **callbacks
    ) -> None:
        images = tuple(images or ())
        self._start(
            lambda cancelled: self.studio.modify_prompt(
                document, request, images, cancelled=cancelled
            ),
            **callbacks,
        )

    def cancel(self) -> None:
        """取消当前任务：断开信号后打取消标记，不阻塞主线程等待。"""
        thread, self._current = self._current, None
        if thread is None or not thread.isRunning():
            return
        for signal in (thread.progress, thread.chunk, thread.result, thread.error):
            try:
                signal.disconnect()
            except TypeError:
                pass  # 没有连接
        thread.cancel()
        self._stale.append(thread)

    def _start(self, open_stream, *, on_result, on_error, on_progress=None, on_chunk=None) -> None:
        self.cancel()
        self._stale = [thread for thread in self._stale if thread.isRunning()]
        thread = PromptStreamThread(open_stream)
        thread.result.connect(on_result)
        thread.error.connect(on_error)
        if on_progress:
            thread.progress.connect(on_progress)
        if on_chunk:
            thread.chunk.connect(on_chunk)
        self._current = thread
        thread.start()


class ImageGenerationThread(QThread):
    """后台调用 Studio.generate_image。"""

    image_ready = pyqtSignal(bytes)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, studio: Studio, request: ImageRequest, provider_label: str = ""):
        super().__init__()
        self.studio = studio
        self.request = request
        self.provider_label = provider_label or request.provider
        self._cancelled = False

    def cancel(self):
        """标记取消：无法中断进行中的 HTTP 请求，但完成后不再发任何信号。"""
        self._cancelled = True

    def run(self):
        try:
            ref_count = len(self.request.images)
            hint = f"，含 {ref_count} 张参考图" if ref_count else ""
            self.progress.emit(f"正在生成图片（{self.provider_label}{hint}）...")
            result = self.studio.generate_image(self.request)
            if self._cancelled:
                return
            self.image_ready.emit(result.to_png_bytes())
        except Exception as exc:  # noqa: BLE001
            if not self._cancelled:
                self.error.emit(str(exc))
