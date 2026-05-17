import asyncio
import logging
from collections import deque


class TraceLogger:
    """异步日志记录器."""

    _queue: asyncio.Queue | None = None
    _task: asyncio.Task | None = None
    _max_logs = 1000
    _logs: deque | None = None

    @classmethod
    def init(cls, path: str):
        cls._path = path
        if cls._queue is None:
            cls._queue = asyncio.Queue()
        if cls._logs is None:
            cls._logs = deque(maxlen=cls._max_logs)

    @classmethod
    def start(cls):
        if cls._task is None:
            cls._task = asyncio.create_task(cls._consume())

    @classmethod
    async def _consume(cls):
        while True:
            try:
                msg = await cls._queue.get()
                logging.info(msg)
                cls._logs.append(msg)
                cls._queue.task_done()
            except Exception as e:
                logging.warning(f"TraceLogger consume error: {e}")
            finally:
                await asyncio.sleep(0)

    @classmethod
    def log(cls, trace_id: str, msg: str, level: int = logging.INFO):
        if cls._queue is not None:
            full_msg = f"[{trace_id}] {msg}"
            cls._queue.put_nowait(full_msg)

    @classmethod
    async def shutdown(cls):
        from contextlib import suppress

        if cls._queue is not None:
            await cls._queue.join()
        if cls._task is not None:
            cls._task.cancel()
            with suppress(asyncio.CancelledError):
                await cls._task
        cls._queue = None
        cls._task = None
        if cls._logs is not None:
            cls._logs.clear()
            cls._logs = None

    @classmethod
    def get_logs(cls) -> list:
        return list(cls._logs) if cls._logs else []

    @classmethod
    def clear_logs(cls):
        if cls._logs is not None:
            cls._logs.clear()
