from __future__ import annotations


def is_city_code(code: str) -> bool:
    """判断行政区号是否为市级及以上 (第5-6位为00).

    Args:
        code: 6位行政区号 eg:330700

    Returns:
        True 表示市级及以上, False 表示区县级
    """
    return len(code) >= 5 and code[4:6] == "00"
