"""阿里云百炼千问图像渠道。"""
from __future__ import annotations

import json
import ssl
import time
from collections.abc import Mapping, Sequence
from io import BytesIO
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from loguru import logger

from nano_banana.core.images.types import (
    OptionSpec,
    ProviderCredentials,
    ProviderSpec,
    aspect_ratio_option,
)
from nano_banana.core.media import encode_image_reference

DEFAULT_MODEL = "qwen-image-3.0-pro"
MAX_REFERENCE_IMAGES = 3

QWEN_IMAGE_SIZE_MAP = {
    "1K": {
        "1:1": "1024*1024",
        "2:3": "768*1152",
        "3:2": "1152*768",
        "3:4": "960*1280",
        "4:3": "1280*960",
        "4:5": "896*1120",
        "5:4": "1120*896",
        "9:16": "720*1280",
        "16:9": "1280*720",
        "21:9": "1344*576",
    },
    "2K": {
        "1:1": "2048*2048",
        "2:3": "1440*2160",
        "3:2": "2160*1440",
        "3:4": "1536*2048",
        "4:3": "2048*1536",
        "4:5": "1600*2000",
        "5:4": "2000*1600",
        "9:16": "1536*2688",
        "16:9": "2688*1536",
        "21:9": "2688*1152",
    },
}
QWEN_GENERATION_PATH = "/services/aigc/multimodal-generation/generation"


class QwenHTTPError(RuntimeError):
    """千问 HTTP 错误，保留状态码供重试策略判断。"""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class QwenImageBackend:
    """阿里云百炼千问图像 3.0（文生图 / 图生图）。"""

    def __init__(self, credentials: ProviderCredentials):
        self.api_key = credentials.api_key
        self.model = credentials.model or DEFAULT_MODEL
        self.endpoint = self._normalize_endpoint(credentials.base_url)
        logger.info(f"[Qwen] 初始化完成，模型: {self.model}，地址: {self.endpoint}")

    @staticmethod
    def _normalize_endpoint(base_url: str) -> str:
        url = (base_url or "").strip().rstrip("/")
        if not url:
            raise ValueError("请先配置千问图像 Base URL")
        if url.endswith(QWEN_GENERATION_PATH):
            return url
        return f"{url}{QWEN_GENERATION_PATH}"

    def generate(self, prompt: str, images: Sequence[str], options: Mapping[str, Any]):
        content = self.build_content(prompt, images)
        has_refs = any("image" in item for item in content)
        parameters = self.build_parameters(options, has_refs=has_refs)
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": content,
                    }
                ]
            },
            "parameters": parameters,
        }
        logger.info(
            f"[Qwen] 发起请求，模型={self.model}，参考图={sum(1 for i in content if 'image' in i)}，"
            f"parameters={parameters}"
        )
        response = self._post_json(payload)
        return self._extract_image(response)

    @staticmethod
    def build_content(text: str, images: Sequence[str]) -> list[dict[str, str]]:
        content: list[dict[str, str]] = []
        if images:
            if len(images) > MAX_REFERENCE_IMAGES:
                logger.warning(
                    f"[Qwen] 参考图超过 {MAX_REFERENCE_IMAGES} 张，"
                    f"仅使用前 {MAX_REFERENCE_IMAGES} 张（共 {len(images)}）"
                )
            for image_ref in images[:MAX_REFERENCE_IMAGES]:
                content.append({"image": encode_image_reference(image_ref)})
        content.append({"text": text})
        return content

    @staticmethod
    def build_parameters(options: Mapping[str, Any], has_refs: bool) -> dict[str, Any]:
        parameters: dict[str, Any] = {"n": 1}

        prompt_extend = options.get("prompt_extend", "true")
        parameters["prompt_extend"] = str(prompt_extend).lower() != "false"

        mode = options.get("prompt_extend_mode") or "direct"
        if has_refs and mode == "agent":
            logger.warning("[Qwen] I2I 不支持 agent 增强，已降为 direct")
            mode = "direct"
        parameters["prompt_extend_mode"] = mode

        parameters["watermark"] = False

        size = resolve_size(options)
        if size:
            parameters["size"] = size
        return parameters

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload)
        last_error: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                raw = self._http_request(
                    "POST",
                    self.endpoint,
                    content=body.encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    timeout=180.0,
                )
                break
            except QwenHTTPError as exc:
                last_error = exc
                if not self._is_transient_http_error(exc.status_code) or attempt >= 3:
                    raise
                logger.warning(f"[Qwen] POST 重试 {attempt}/3: {exc}")
                time.sleep(1.5 * attempt)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if not self._is_transient_network_error(exc) or attempt >= 3:
                    raise RuntimeError(f"千问图像网络错误: {exc}") from exc
                logger.warning(f"[Qwen] POST 重试 {attempt}/3: {exc}")
                time.sleep(1.5 * attempt)
        else:
            raise RuntimeError(f"千问图像网络错误: {last_error}")

        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"千问图像返回非 JSON: {raw[:200]!r}") from exc

        if isinstance(data, dict) and data.get("code"):
            raise RuntimeError(
                f"千问图像请求失败: code={data.get('code')}, message={data.get('message')}"
                + (f", request_id={data.get('request_id')}" if data.get("request_id") else "")
            )
        if isinstance(data, dict) and data.get("status_code") not in (None, 200):
            raise RuntimeError(
                f"千问图像请求失败: status_code={data.get('status_code')}, "
                f"code={data.get('code')}, message={data.get('message')}"
            )
        return data

    @staticmethod
    def _is_transient_network_error(exc: Exception) -> bool:
        text = str(exc).lower()
        needles = (
            "not_enough_data",
            "ssl",
            "eof",
            "timed out",
            "timeout",
            "connection refused",
            "all connection attempts failed",
            "connection reset",
            "connection aborted",
            "temporarily unavailable",
            "remote disconnected",
            "server disconnected",
        )
        if any(n in text for n in needles):
            return True
        if type(exc).__module__.startswith("httpx"):
            return type(exc).__name__ in {
                "CloseError",
                "ConnectError",
                "ConnectTimeout",
                "NetworkError",
                "PoolTimeout",
                "ReadError",
                "ReadTimeout",
                "RemoteProtocolError",
                "TransportError",
                "WriteError",
                "WriteTimeout",
            }
        return isinstance(exc, (ssl.SSLError, TimeoutError, ConnectionError, OSError))

    @staticmethod
    def _is_transient_http_error(status_code: int) -> bool:
        return status_code == 429 or status_code in {500, 502, 503, 504}

    @staticmethod
    def _http_request(
        method: str,
        url: str,
        *,
        content: Optional[bytes] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: float = 120.0,
    ) -> bytes:
        """优先 httpx（与项目其它 AI 调用一致），失败再回退 urllib。"""
        try:
            import httpx

            with httpx.Client(http2=False, timeout=timeout, follow_redirects=True) as client:
                response = client.request(method, url, content=content, headers=headers or {})
                if response.status_code >= 400:
                    detail = response.text
                    try:
                        parsed = response.json()
                        code = parsed.get("code") or response.status_code
                        message = parsed.get("message") or detail
                        request_id = parsed.get("request_id") or ""
                        raise QwenHTTPError(
                            f"千问图像请求失败: code={code}, message={message}"
                            + (f", request_id={request_id}" if request_id else ""),
                            response.status_code,
                        )
                    except QwenHTTPError:
                        raise
                    except Exception:  # noqa: BLE001
                        raise QwenHTTPError(
                            f"千问图像请求失败: HTTP {response.status_code}, {detail[:300]}",
                            response.status_code,
                        )
                return response.content
        except ImportError:
            pass

        request = Request(url, data=content, headers=headers or {}, method=method)
        try:
            with urlopen(request, timeout=timeout) as resp:
                return resp.read()
        except HTTPError as exc:
            error_body = ""
            try:
                error_body = exc.read().decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass
            detail = error_body or str(exc)
            try:
                parsed = json.loads(error_body) if error_body else {}
                code = parsed.get("code") or exc.code
                message = parsed.get("message") or detail
                request_id = parsed.get("request_id") or ""
                raise QwenHTTPError(
                    f"千问图像请求失败: code={code}, message={message}"
                    + (f", request_id={request_id}" if request_id else ""),
                    exc.code,
                ) from exc
            except QwenHTTPError:
                raise
            except Exception:  # noqa: BLE001
                raise QwenHTTPError(
                    f"千问图像请求失败: HTTP {exc.code}, {detail}",
                    exc.code,
                ) from exc
        except URLError:
            raise

    def _extract_image(self, response: dict[str, Any]):
        from PIL import Image

        choices = ((response.get("output") or {}).get("choices")) or []
        if not choices:
            logger.warning("[Qwen] 响应无 choices")
            return None

        content = ((choices[0].get("message") or {}).get("content")) or []
        image_url = None
        for item in content:
            if isinstance(item, dict) and item.get("image"):
                image_url = item["image"]
                break
        if not image_url:
            logger.warning("[Qwen] 响应未包含 image URL")
            return None

        logger.info("[Qwen] 正在下载生成图片")
        last_error: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                image_bytes = self._http_request("GET", image_url, timeout=120.0)
                return Image.open(BytesIO(image_bytes))
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                is_transient = self._is_transient_network_error(exc)
                if isinstance(exc, QwenHTTPError):
                    is_transient = self._is_transient_http_error(exc.status_code)
                if not is_transient or attempt >= 3:
                    raise RuntimeError(f"千问图像下载失败: {exc}") from exc
                logger.warning(f"[Qwen] 下载重试 {attempt}/3: {exc}")
                time.sleep(1.5 * attempt)
        raise RuntimeError(f"千问图像下载失败: {last_error}")


def resolve_size(options: Mapping[str, Any]) -> Optional[str]:
    image_size = options.get("image_size") or "auto"
    if image_size == "auto":
        return None
    aspect_ratio = options.get("aspect_ratio") or "1:1"
    size_bucket = QWEN_IMAGE_SIZE_MAP.get(image_size) or QWEN_IMAGE_SIZE_MAP["2K"]
    return size_bucket.get(aspect_ratio) or size_bucket.get("1:1")


SPEC = ProviderSpec(
    id="qwen_image",
    label="千问图像",
    factory=QwenImageBackend,
    default_model=DEFAULT_MODEL,
    default_base_url="",
    url_placeholder="https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1",
    model_suggestions=(DEFAULT_MODEL,),
    options=(
        aspect_ratio_option(),
        OptionSpec("image_size", "尺寸", "auto", ("auto", "1K", "2K")),
        OptionSpec("prompt_extend", "提示词增强", "true", ("true", "false")),
        OptionSpec("prompt_extend_mode", "增强方式", "direct", ("direct", "agent")),
    ),
    max_reference_images=MAX_REFERENCE_IMAGES,
)
