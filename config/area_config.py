from __future__ import annotations

from functools import lru_cache

from config.codes import codes


_DEFAULT_LAYOUT = {
    "top_location": "0,0,0.28,0.25",
    "face_location": "0.7,0,0.3,0.25",
    "width": 900,
    "height": 700,
}

_CUSTOM_LAYOUTS: dict[str, dict] = {
    "330100": {"top_location": "0.7,0,0.3,0.25", "face_location": "0.0,0.7,0.3,0.3"},
    "330500": {"top_location": "0,0.55,0.28,0.25", "face_location": "0.8,0.08,0.2,0.25"},
    "330523": {"top_location": "0.78,0.08,0.1,0.1", "face_location": "0,0.80,0.28,0.25"},
    "330800": {"top_location": "0,0.01,0.28,0.3", "face_location": "0.75,0.08,0.25,0.25", "width": 800},
    "330802": {"face_location": "0.75,0.1,0.25,0.1"},
}

_SHOW_MINS = ["TEM_MIN_1H", "TEM_MIN_24H"]

RAIN_PRE = {
    "SUM_PRE_5MI": 5,
    "SUM_PRE_10MI": 10,
    "SUM_PRE_30MI": 30,
    "SUM_PRE_1H": 60,
    "SUM_PRE_3H": 3 * 60,
    "SUM_PRE_6H": 6 * 60,
    "SUM_PRE_12H": 12 * 60,
    "SUM_PRE_24H": 24 * 60,
    "SUM_PRE_36H": 36 * 60,
    "SUM_PRE_48H": 48 * 60,
    "SUM_PRE_72H": 72 * 60,
    "SUM_PRE_SINCE_MI": 60,
    "SUM_PRE_1H_POINT": 1 * 60,
    "SUM_PRE_3H_POINT": 3 * 60,
    "SUM_PRE_6H_POINT": 6 * 60,
    "SUM_PRE_12H_POINT": 12 * 60,
    "SUM_PRE_24H_POINT": 24 * 60,
    "SUM_PRE_36H_POINT": 36 * 60,
    "SUM_PRE_48H_POINT": 48 * 60,
    "SUM_PRE_72H_POINT": 72 * 60,
    "SUM_PRE_0808": 24 * 60,
    "SUM_PRE_2020": 24 * 60,
    "SUM_PRE_0505": 24 * 60,
    "SUM_PRE_FREE": -1,
    "PRE_MI_BY_MI": -1,
    "PRE_H_BY_H": -1,
    "PRE_D_BY_D": -1,
    "PRE_MAX_1H_HISTORY": -1,
    "PRE_MAX_3H_HISTORY": -1,
    "PRE_MAX_6H_HISTORY": -1,
    "PRE_MAX_12H_HISTORY": -1,
    "PRE_MAX_24H_HISTORY": -1,
    "SUM_PRE_1H_POINT_WATER": 60,
    "SUM_PRE_3H_POINT_WATER": 3 * 60,
    "SUM_PRE_6H_POINT_WATER": 6 * 60,
    "SUM_PRE_12H_POINT_WATER": 12 * 60,
    "SUM_PRE_24H_POINT_WATER": 24 * 60,
    "SUM_PRE_36H_POINT_WATER": 36 * 60,
    "SUM_PRE_48H_POINT_WATER": 48 * 60,
    "SUM_PRE_72H_POINT_WATER": 72 * 60,
    "SUM_PRE_0808_WATER": 24 * 60,
    "SUM_PRE_2020_WATER": 24 * 60,
}

AREAS = [item["code"] for item in codes]


@lru_cache(maxsize=256)
def get_area_layout(code: str) -> dict:
    """获取区划布局配置, 带 LRU 缓存避免重复字典合并."""
    code = str(code)
    custom = _CUSTOM_LAYOUTS.get(code, {})
    return {**_DEFAULT_LAYOUT, **custom}
