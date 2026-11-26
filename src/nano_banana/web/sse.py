"""PromptEvent → SSE。事件格式是 Web 前端（以及任何 HTTP 调用方）的协议：

    data: {"status": "started" | "thinking"}
    data: {"content": "<增量文本>"}
    data: {"result": {"document": {...} | null, "parse_error": "", "changes": [...]}}
    data: {"error": "<错误信息>"}
    data: [DONE]
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Iterator

from flask import Response

from nano_banana.core import PromptEvent

DONE = "data: [DONE]\n\n"


def _data(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def iter_sse(events: Iterable[PromptEvent]) -> Iterator[str]:
    for event in events:
        if event.type in ("started", "thinking"):
            yield _data({"status": event.type})
        elif event.type == "content":
            yield _data({"content": event.text})
        elif event.type == "error":
            yield _data({"error": event.text})
            return
        elif event.type == "result":
            yield _data(
                {
                    "result": {
                        "document": event.document,
                        "parse_error": event.parse_error,
                        "changes": [change.to_dict() for change in event.changes],
                    }
                }
            )
            yield DONE
            return
    yield DONE


def sse_response(events: Iterable[PromptEvent]) -> Response:
    response = Response(iter_sse(events), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response
