from __future__ import annotations


_TEMP = [
    {"value": 16, "stop": [3, 3, 67, 1]},
    {"value": 17, "stop": [12, 12, 84, 1]},
    {"value": 18, "stop": [24, 24, 102, 1]},
    {"value": 19, "stop": [36, 36, 121, 1]},
    {"value": 20, "stop": [52, 52, 142, 1]},
    {"value": 21, "stop": [72, 72, 165, 1]},
    {"value": 22, "stop": [28, 122, 218, 1]},
    {"value": 23, "stop": [6, 140, 222, 1]},
    {"value": 24, "stop": [49, 160, 228, 1]},
    {"value": 25, "stop": [14, 169, 232, 1]},
    {"value": 26, "stop": [51, 183, 232, 1]},
    {"value": 27, "stop": [92, 211, 255, 1]},
    {"value": 28, "stop": [128, 220, 254, 1]},
    {"value": 29, "stop": [157, 228, 255, 1]},
    {"value": 30, "stop": [200, 240, 254, 1]},
    {"value": 31, "stop": [240, 227, 80, 1]},
    {"value": 32, "stop": [237, 213, 125, 1]},
    {"value": 33, "stop": [249, 195, 99, 1]},
    {"value": 34, "stop": [237, 156, 74, 1]},
    {"value": 35, "stop": [241, 88, 47, 1]},
    {"value": 36, "stop": [237, 21, 96, 1]},
    {"value": 37, "stop": [175, 8, 62, 1]},
    {"value": 38, "stop": [149, 19, 19, 1]},
    {"value": 39, "stop": [155, 102, 172, 1]},
    {"value": 40, "stop": [134, 78, 143, 1]},
    {"value": 999999, "text": "缺测", "stop": [134, 78, 143, 1]},
]

_TEMP_WINTER = [
    {"value": 0, "stop": [6, 196, 253, 1]},
    {"value": 2, "stop": [6, 234, 251, 1]},
    {"value": 4, "stop": [8, 248, 252, 1]},
    {"value": 6, "stop": [2, 254, 182, 1]},
    {"value": 8, "stop": [15, 246, 113, 1]},
    {"value": 10, "stop": [0, 255, 42, 1]},
    {"value": 12, "stop": [118, 253, 0, 1]},
    {"value": 14, "stop": [150, 252, 29, 1]},
    {"value": 16, "stop": [180, 254, 8, 1]},
    {"value": 18, "stop": [216, 255, 1, 1]},
    {"value": 20, "stop": [255, 231, 0, 1]},
    {"value": 22, "stop": [249, 201, 5, 1]},
    {"value": 24, "stop": [255, 154, 4, 1]},
    {"value": 26, "stop": [255, 129, 14, 1]},
    {"value": 28, "stop": [243, 101, 13, 1]},
    {"value": 30, "stop": [246, 72, 4, 1]},
    {"value": 32, "stop": [249, 42, 1, 1]},
    {"value": 34, "stop": [205, 8, 0, 1]},
    {"value": 36, "stop": [140, 2, 8, 1]},
]

_WIND = [
    {"value": 0.2, "stop": [144, 208, 248, 1]},
    {"value": 2.6, "stop": [120, 184, 248, 1]},
    {"value": 3.4, "stop": [80, 160, 240, 1]},
    {"value": 5.5, "stop": [60, 120, 220, 1]},
    {"value": 8, "stop": [40, 100, 200, 1]},
    {"value": 10.8, "stop": [0, 176, 8, 1]},
    {"value": 13.9, "stop": [248, 248, 0, 1]},
    {"value": 17.2, "stop": [248, 168, 0, 1]},
    {"value": 20.8, "stop": [248, 80, 0, 1]},
    {"value": 24.5, "stop": [248, 0, 0, 1]},
    {"value": 28.5, "stop": [248, 24, 80, 1]},
    {"value": 32.7, "stop": [240, 48, 152, 1]},
    {"value": 37.0, "stop": [232, 80, 232, 1]},
    {"value": 46.2, "stop": [224, 72, 72, 1]},
    {"value": 51, "stop": [200, 56, 56, 1]},
    {"value": 56.1, "stop": [160, 24, 32, 1]},
    {"value": 76, "stop": [255, 210, 255, 1]},
]

_RAIN = [
    {"value": 0, "stop": [255, 255, 255, 1]},
    {"value": 0.1, "stop": [169, 255, 253, 1]},
    {"value": 2, "stop": [45, 212, 253, 1]},
    {"value": 5, "stop": [45, 167, 255, 1]},
    {"value": 10, "stop": [45, 126, 255, 1]},
    {"value": 15, "stop": [81, 168, 45, 1]},
    {"value": 25, "stop": [74, 255, 45, 1]},
    {"value": 35, "stop": [255, 253, 45, 1]},
    {"value": 50, "stop": [255, 209, 47, 1]},
    {"value": 70, "stop": [255, 168, 45, 1]},
    {"value": 100, "stop": [255, 45, 45, 1]},
    {"value": 120, "stop": [205, 47, 48, 1]},
    {"value": 150, "stop": [170, 45, 45, 1]},
    {"value": 170, "stop": [172, 45, 172, 1]},
    {"value": 200, "stop": [218, 45, 222, 1]},
    {"value": 230, "stop": [240, 45, 255, 1]},
    {"value": 250, "stop": [254, 209, 255, 1]},
    {"value": 999999, "text": "缺测", "stop": [254, 209, 255, 1]},
]

_SNOW = _RAIN

_VIS = [
    {"value": 50, "stop": [128, 64, 0, 1]},
    {"value": 200, "stop": [240, 45, 255, 1]},
    {"value": 500, "stop": [172, 45, 172, 1]},
    {"value": 1000, "stop": [255, 168, 45, 1]},
    {"value": 10000, "stop": [81, 168, 45, 1]},
    {"value": 30000, "stop": [169, 255, 253, 1]},
]

_CON_WIND = [
    {"value": 10.7, "stop": [0, 176, 8, 1]},
    {"value": 17.1, "stop": [0, 0, 255, 1]},
    {"value": 24.4, "stop": [218, 165, 32, 1]},
    {"value": 32.6, "stop": [255, 0, 255, 1]},
    {"value": 32.7, "stop": [255, 0, 0, 1]},
]


def get_color_map(axis: str, data_type: str, month: int | None = None, show_contourf: bool = True) -> list[dict]:
    """根据数据类型和月份获取色标配置列表.

    温度色标区分冬夏: 10-4月使用冬季色标, 其余使用夏季色标.
    风速色标区分填色/非填色模式.

    Args:
        axis: 数据别名 (如 TEM, SUM_PRE_12H_POINT)
        data_type: 数据类型, 可选 tem/wind/rain/vis/snow
        month: 月份 (1-12), 仅温度类型使用
        show_contourf: 是否显示填色图, 仅风速类型使用

    Returns:
        色标配置列表, 每项包含 value/stop/text 等键
    """
    if data_type == "tem":
        if month in [10, 11, 12, 1, 2, 3, 4]:
            return _TEMP_WINTER
        return _TEMP
    elif data_type == "wind":
        if not show_contourf:
            return _CON_WIND
        return _WIND
    elif data_type == "rain":
        return _RAIN
    elif data_type == "vis":
        return _VIS
    elif data_type == "snow":
        return _SNOW
    return _TEMP


def rgb_to_hex(rgb: tuple[int, ...]) -> str:
    """将 RGB 元组转换为十六进制颜色字符串.

    Args:
        rgb: RGB 颜色元组, 如 (255, 128, 0)

    Returns:
        十六进制颜色字符串, 如 "#ff8000"
    """
    r, g, b = rgb[:3]
    return f"#{r:02x}{g:02x}{b:02x}"
