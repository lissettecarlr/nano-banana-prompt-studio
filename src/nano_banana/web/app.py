"""Flask 应用工厂与启动入口。

    python -m nano_banana.web [--open]     # --open：启动后自动打开浏览器

运行参数全部走环境变量：

    NANO_BANANA_HOME          可写数据目录（配置、预设）
    NANO_BANANA_HOST          监听地址，默认 127.0.0.1；容器/局域网访问设为 0.0.0.0
    NANO_BANANA_PORT          监听端口，默认 5000
    NANO_BANANA_DEBUG         1 开启 Flask debug（切勿在对外监听时开启）
    NANO_BANANA_CORS_ORIGINS  允许跨域访问 /api 的来源，逗号分隔；默认不开放跨域
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from loguru import logger
from werkzeug.exceptions import HTTPException

from nano_banana.core import Studio
from nano_banana.web.blueprints import chat, config, images, presets, prompt
from nano_banana.web.context import STUDIO_EXTENSION

STATIC_DIR = Path(__file__).resolve().parent / "static"

HOST_ENV = "NANO_BANANA_HOST"
PORT_ENV = "NANO_BANANA_PORT"
DEBUG_ENV = "NANO_BANANA_DEBUG"
CORS_ENV = "NANO_BANANA_CORS_ORIGINS"

_TRUTHY = {"1", "true", "yes", "on"}


def create_app(studio: Studio | None = None) -> Flask:
    app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
    app.extensions[STUDIO_EXTENSION] = studio or Studio.default()
    # 键顺序有意义：渠道按注册顺序展示，文档按 schema 顺序展示
    app.json.sort_keys = False
    _configure_cors(app)

    for module in (config, prompt, presets, chat, images):
        app.register_blueprint(module.bp)

    @app.route("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.route("/.well-known/appspecific/com.chrome.devtools.json")
    def chrome_devtools():
        return jsonify({})

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        if isinstance(exc, HTTPException):
            if request.path.startswith("/api/"):
                return jsonify({"error": exc.description}), exc.code
            return exc
        logger.exception(f"未处理的异常: {request.method} {request.path}")
        if request.path.startswith("/api/"):
            return jsonify({"error": str(exc)}), 500
        raise exc

    return app


def _configure_cors(app: Flask) -> None:
    origins = [item.strip() for item in os.environ.get(CORS_ENV, "").split(",") if item.strip()]
    if not origins:
        return  # 页面与 API 同源，默认不需要跨域
    from flask_cors import CORS

    CORS(app, resources={r"/api/*": {"origins": "*" if origins == ["*"] else origins}})


def _open_browser_later(url: str, delay: float = 1.5) -> None:
    import threading
    import webbrowser

    timer = threading.Timer(delay, webbrowser.open, args=(url,))
    timer.daemon = True
    timer.start()


def main(argv: list[str] | None = None) -> None:
    """启动 Web 端。唯一的命令行参数是 --open：启动后自动打开浏览器。"""
    args = sys.argv[1:] if argv is None else argv
    host = os.environ.get(HOST_ENV, "").strip() or "127.0.0.1"
    port = int(os.environ.get(PORT_ENV, "").strip() or 5000)
    debug = os.environ.get(DEBUG_ENV, "").strip().lower() in _TRUTHY

    app = create_app()
    studio: Studio = app.extensions[STUDIO_EXTENSION]
    shown_host = "localhost" if host in ("127.0.0.1", "0.0.0.0", "::") else host
    print("=" * 60)
    print("Nano Banana Studio - Web")
    print("=" * 60)
    print(f"访问地址: http://{shown_host}:{port}")
    print(f"监听地址: {host}:{port}（局域网/容器访问请设置 {HOST_ENV}=0.0.0.0）")
    print(f"数据目录: {studio.paths.user}")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    if "--open" in args:
        _open_browser_later(f"http://{shown_host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
