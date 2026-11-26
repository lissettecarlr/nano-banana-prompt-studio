"""文件读写基础设施：原子写入 + 跨线程/跨进程互斥。"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml

_LOCK_TIMEOUT = 10.0
_STALE_LOCK_SECONDS = 30.0
_POLL_INTERVAL = 0.02

class _PathLock:
    def __init__(self) -> None:
        self.thread_lock = threading.RLock()
        self.depth = 0  # 只在持有 thread_lock 时读写


_path_locks: dict[str, _PathLock] = {}
_path_locks_guard = threading.Lock()


def _path_lock_for(path: Path) -> _PathLock:
    key = os.path.normcase(os.path.abspath(path))
    with _path_locks_guard:
        lock = _path_locks.get(key)
        if lock is None:
            lock = _path_locks[key] = _PathLock()
        return lock


@contextmanager
def locked(path: Path) -> Iterator[None]:
    """对 path 的「读-改-写」加锁，可重入。

    进程内用 RLock；进程间用 `<path>.lock` 独占创建。持锁进程崩溃留下的
    过期锁文件会在 _STALE_LOCK_SECONDS 后被接管。
    """
    path = Path(path)
    state = _path_lock_for(path)
    with state.thread_lock:
        if state.depth == 0:
            lock_path = path.with_name(path.name + ".lock")
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            _acquire_lock_file(lock_path)
        state.depth += 1
        try:
            yield
        finally:
            state.depth -= 1
            if state.depth == 0:
                try:
                    path.with_name(path.name + ".lock").unlink()
                except OSError:
                    pass


def _acquire_lock_file(lock_path: Path) -> None:
    deadline = time.monotonic() + _LOCK_TIMEOUT
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > _STALE_LOCK_SECONDS:
                    lock_path.unlink()
                    continue
            except OSError:
                continue  # 锁刚好被释放
            if time.monotonic() > deadline:
                raise TimeoutError(f"等待文件锁超时: {lock_path}") from None
            time.sleep(_POLL_INTERVAL)
        except PermissionError:
            # Windows 上另一进程正在删除锁文件时会短暂拒绝访问
            if time.monotonic() > deadline:
                raise
            time.sleep(_POLL_INTERVAL)
        else:
            os.write(fd, str(os.getpid()).encode("ascii"))
            os.close(fd)
            return


def atomic_write_text(path: Path, text: str) -> None:
    """先写同目录临时文件再 rename，读者永远看不到半截文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        _replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _replace(src: str, dst: Path) -> None:
    # Windows 上目标文件正被别的进程读取时 replace 会短暂失败
    for attempt in range(20):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(_POLL_INTERVAL)


def read_yaml(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_yaml(path: Path, data: Any) -> None:
    atomic_write_text(
        path,
        yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
    )


def read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2))
