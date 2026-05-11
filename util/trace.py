from __future__ import annotations

import contextvars


_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")


class TraceContext:
    """基于 contextvars 的协程安全 trace_id 传递."""

    @classmethod
    def set(cls, trace_id: str) -> None:
        """设置当前协程的 trace_id.

        Args:
            trace_id: 追踪标识, 通常由请求 ID 构成
        """
        _trace_id_var.set(trace_id)

    @classmethod
    def get(cls) -> str:
        """获取当前协程的 trace_id, 未设置时返回空字符串.

        Returns:
            当前协程的 trace_id
        """
        return _trace_id_var.get("")
