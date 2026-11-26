import json
import shutil
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from conftest import STATIC

pytest.importorskip("flask")

CHAT = {"base_url": "https://example.test/v1", "api_key": "test-key", "model": "reasoning-model"}


class DummyHttpClient:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def _chunk(content="", reasoning=None):
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content, reasoning_content=reasoning))]
    )


def _fake_openai(chunks):
    """生成一个替身 OpenAI 类；state 记录是否已经打过上游、请求体是什么。"""
    state = SimpleNamespace(create_called=False, requests=[], init_kwargs=None)

    def create(**kwargs):
        state.create_called = True
        state.requests.append(kwargs)
        return iter(chunks)

    class DummyOpenAI:
        def __init__(self, **kwargs):
            state.init_kwargs = kwargs
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))

    return DummyOpenAI, state


def _events(body: str) -> list:
    return [
        block.removeprefix("data: ") if block == "data: [DONE]" else json.loads(block.removeprefix("data: "))
        for block in body.split("\n\n")
        if block
    ]


@pytest.mark.parametrize(
    "endpoint, payload",
    [
        ("/api/generate", {"prompt": "a forest", "images": []}),
        ("/api/modify", {"document": {"风格模式": "插画"}, "modify_request": "add a forest", "images": []}),
        ("/api/modify", {"current_data": '{"风格模式": "插画"}', "modify_request": "add a forest"}),
    ],
)
def test_prompt_endpoints_start_before_upstream_and_report_thinking(
    web_client, fake_studio, endpoint, payload
):
    fake_studio.settings.update({"chat": CHAT})
    http_client = DummyHttpClient()
    openai_class, state = _fake_openai([_chunk(reasoning="thinking"), _chunk('{"风格模式":"写实"}')])

    with patch("openai.OpenAI", openai_class), patch("httpx.Client", return_value=http_client):
        response = web_client.post(endpoint, json=payload, buffered=False)

        assert response.status_code == 200
        assert response.mimetype == "text/event-stream"
        assert response.headers["Cache-Control"] == "no-cache"
        assert response.headers["X-Accel-Buffering"] == "no"
        assert not state.create_called

        chunks = iter(response.response)
        first_chunk = next(chunks).decode("utf-8")
        assert json.loads(first_chunk.removeprefix("data: ")) == {"status": "started"}
        assert not state.create_called  # 「已开始」先于上游请求送达浏览器

        remaining = b"".join(chunks).decode("utf-8")

    assert remaining.endswith("data: [DONE]\n\n")
    events = _events(remaining)
    assert events[0] == {"status": "thinking"}
    assert events[1] == {"content": '{"风格模式":"写实"}'}
    result = events[2]["result"]
    assert result["document"] == {"风格模式": "写实"}
    assert result["parse_error"] == ""
    assert events[3] == "[DONE]"
    assert http_client.closed
    assert state.init_kwargs["api_key"] == "test-key"
    assert state.init_kwargs["base_url"] == "https://example.test/v1"
    assert state.requests[0]["model"] == "reasoning-model"

    if endpoint == "/api/modify":
        # 差异由服务端算好，前端只负责展示和勾选
        assert result["changes"] == [
            {"path": ["风格模式"], "label": "风格模式", "kind": "changed", "old": "插画", "new": "写实"}
        ]
    else:
        assert result["changes"] == []


def test_abort_after_started_closes_http_client_without_calling_upstream(web_client, fake_studio):
    fake_studio.settings.update({"chat": CHAT})
    http_client = DummyHttpClient()
    openai_class, state = _fake_openai([_chunk("{}")])

    with patch("openai.OpenAI", openai_class), patch("httpx.Client", return_value=http_client):
        response = web_client.post(
            "/api/generate", json={"prompt": "a forest", "images": []}, buffered=False
        )
        chunks = iter(response.response)
        assert json.loads(next(chunks).decode("utf-8").removeprefix("data: ")) == {"status": "started"}
        response.close()

    assert not state.create_called
    assert http_client.closed


def test_unparseable_model_output_still_finishes_the_stream(web_client, fake_studio):
    fake_studio.settings.update({"chat": CHAT})
    openai_class, _state = _fake_openai([_chunk("抱歉，我不能")])

    with patch("openai.OpenAI", openai_class), patch("httpx.Client", return_value=DummyHttpClient()):
        body = web_client.post("/api/generate", json={"prompt": "x"}).get_data(as_text=True)

    events = _events(body)
    assert events[-1] == "[DONE]"
    assert events[-2]["result"]["document"] is None
    assert events[-2]["result"]["parse_error"]


def test_upstream_failure_is_an_sse_error_without_done(web_client, fake_studio):
    fake_studio.settings.update({"chat": CHAT})

    class FailingOpenAI:
        def __init__(self, **_kwargs):
            def create(**_kwargs):
                raise RuntimeError("Error code: 429 rate limited")

            self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))

    http_client = DummyHttpClient()
    with patch("openai.OpenAI", FailingOpenAI), patch("httpx.Client", return_value=http_client):
        body = web_client.post("/api/generate", json={"prompt": "x"}).get_data(as_text=True)

    assert _events(body) == [{"status": "started"}, {"error": "请求过于频繁，请稍后再试"}]
    assert http_client.closed


@pytest.mark.parametrize(
    "endpoint, payload, chat, message",
    [
        ("/api/generate", {"prompt": "x"}, {}, "请先配置API密钥"),
        ("/api/generate", {"prompt": "x"}, {"api_key": "k"}, "请先配置Base URL"),
        ("/api/generate", {"prompt": "  ", "images": []}, CHAT, "请提供文字描述或参考图片"),
        ("/api/modify", {"modify_request": "x"}, CHAT, "当前数据和修改要求不能为空"),
        ("/api/modify", {"document": {}, "modify_request": " "}, CHAT, "修改要求不能为空"),
        ("/api/modify", {"current_data": "{bad", "modify_request": "x"}, CHAT, "current_data 不是有效的 JSON"),
    ],
)
def test_prompt_endpoints_reject_bad_requests_with_plain_json(
    web_client, fake_studio, endpoint, payload, chat, message
):
    if chat:
        fake_studio.settings.update({"chat": chat})
    response = web_client.post(endpoint, json=payload)
    assert response.status_code == 400
    assert response.mimetype == "application/json"
    assert response.get_json() == {"error": message}


# ---------------- 浏览器端 SSE 解析器 ----------------


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js is required for browser parser tests")
def test_parser_buffers_split_events_and_surfaces_server_errors():
    script = r"""
const assert = require('assert');
const { SseEventParser, parseSseJsonEvent } = require(process.argv[1]);

const parser = new SseEventParser();
assert.deepStrictEqual(parser.push('data: {"content":"hel'), []);
const second = parser.push('lo"}\r\n\r\n');
assert.strictEqual(second.length, 1);
assert.deepStrictEqual(parseSseJsonEvent(second[0]), { type: 'content', content: 'hello' });

assert.deepStrictEqual(parseSseJsonEvent('{"status":"thinking"}'), { type: 'status', status: 'thinking' });
assert.deepStrictEqual(parseSseJsonEvent('[DONE]'), { type: 'done' });
assert.deepStrictEqual(parseSseJsonEvent('{"content":""}'), { type: 'ignore' });

const result = { document: { a: 1 }, parse_error: '', changes: [{ path: ['a'], label: 'a', kind: 'added', old: null, new: 1 }] };
assert.deepStrictEqual(
    parseSseJsonEvent(JSON.stringify({ result })),
    { type: 'result', result },
);

assert.throws(() => parseSseJsonEvent('{"error":"upstream failed"}'), /^Error: upstream failed$/);
assert.throws(() => parseSseJsonEvent('not json'), /AI 流式响应格式错误/);

const multi = new SseEventParser();
assert.deepStrictEqual(multi.push('data: a\n\ndata: b\n\n: comment\n\n'), ['a', 'b']);
assert.deepStrictEqual(multi.finish(), []);
const truncated = new SseEventParser();
truncated.push('data: {"content":"x"');
assert.throws(() => truncated.finish(), /AI 流式响应不完整/);
"""
    result = subprocess.run(
        ["node", "-e", script, str(STATIC / "sse-parser.js")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
