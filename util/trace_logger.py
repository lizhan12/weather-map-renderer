from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time

import aiofiles

from util.trace import TraceContext


_log_queue: asyncio.Queue[str | None] | None = None
_writer_task: asyncio.Task | None = None
_log_path: str = ""
_last_ts: dict[str, float] = {}
_start_ts: dict[str, float] = {}


class TraceLogger:
    """异步追踪日志器, 记录请求各步骤的耗时."""

    @classmethod
    def init(cls, log_dir: str) -> None:
        """初始化日志文件路径.

        Args:
            log_dir: 日志目录, trace.log 将写入此目录
        """
        global _log_path
        _log_path = os.path.join(log_dir, "trace.log")

    @classmethod
    def _ensure_writer(cls) -> None:
        """确保异步写入协程已启动, 若事件循环不可用则静默跳过."""
        global _log_queue, _writer_task
        if _log_queue is not None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        _log_queue = asyncio.Queue()
        _writer_task = loop.create_task(cls._writer())

    @classmethod
    async def _writer(cls) -> None:
        """异步写入协程, 从队列消费日志行并追加写入文件."""
        os.makedirs(os.path.dirname(_log_path), exist_ok=True)
        while True:
            line = await _log_queue.get()
            if line is None:
                break
            try:
                async with aiofiles.open(_log_path, "a", encoding="utf-8") as f:
                    await f.write(line + "\n")
            except Exception:
                logging.warning("trace write failed")

    @classmethod
    async def shutdown(cls) -> None:
        """关闭日志器, 发送终止信号并等待写入协程结束."""
        global _log_queue, _writer_task
        if _log_queue is not None:
            await _log_queue.put(None)
        if _writer_task is not None:
            await _writer_task
            _writer_task = None
        _log_queue = None

    @classmethod
    def log(cls, step: str, message: str = "", level: int = logging.INFO) -> None:
        """记录一条追踪日志.

        格式: [trace_id] step | +elapsed_ms total=total_ms | message
        当 step="request_received" 时重置计时起点.

        Args:
            step: 步骤名称, 如 request_received/data_fetch_done/response_sent
            message: 附加信息
            level: 日志级别, 默认 INFO
        """
        cls._ensure_writer()
        trace_id = TraceContext.get()
        now = time.time()

        elapsed_ms = 0
        if trace_id:
            prev = _last_ts.get(trace_id)
            if prev is not None:
                elapsed_ms = int((now - prev) * 1000)
            if step == "request_received" or prev is None:
                _start_ts[trace_id] = now
                elapsed_ms = 0
        _last_ts[trace_id] = now

        total_ms = int((now - _start_ts.get(trace_id, now)) * 1000)

        text = f"[{trace_id or '-'}] {step} | +{elapsed_ms}ms total={total_ms}ms | {message}"

        if _log_queue is not None:
            with contextlib.suppress(asyncio.QueueFull):
                _log_queue.put_nowait(text)

        logger = logging.getLogger("trace")
        logger.log(level, text)
