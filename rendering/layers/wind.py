from __future__ import annotations

from config import WIND_SIGN, WS


def draw_wind_barbs(ax, stations: list, config: dict, state: dict) -> None:
    """在地图上绘制风向杆标记.

    根据站点风向和风速值绘制旋转的风向符号, 位置自动偏移避免与站点值重叠.

    Args:
        ax: matplotlib Axes 对象
        stations: 站点数据列表, 每项包含 lon/lat/val/dir 键
        config: 渲染配置, 包含 wind_fontsize/wind_color/show_contourf 等键
        state: 状态字典, 需包含 colors 和 extent
    """
    vals = state.get("colors", ([], []))[1]
    colors = state.get("colors", ([], []))[0]
    extent = state.get("extent", [])
    margin = state.get("margin", [10, 10, 10, 10])

    value_offset = 0
    if config.get("show_name") and config.get("show_value"):
        value_offset = 1

    h = config.get("height", 700) - margin[0] - margin[2]
    h = (extent[3] - extent[2] + 0.02) / h * 8 * value_offset if len(extent) >= 4 else 0

    for station in stations:
        direction = station.get("dir")
        if direction is None:
            continue
        val = station["val"]
        fontcolor = config.get("wind_color", "#fff")
        if not config.get("show_contourf", True):
            fontcolor = _get_wind_color(val, vals, colors)
        _draw_wind_marker(
            ax,
            float(station["lon"]),
            float(station["lat"]) + h,
            val,
            direction,
            config.get("wind_fontsize", 20),
            fontcolor,
            config,
        )


def _get_wind_font(v: float) -> str:
    """根据风速值获取对应的风向符号字符.

    Args:
        v: 风速值

    Returns:
        风向符号字符, 超出范围返回 "K"
    """
    for item in WIND_SIGN:
        if item[0] > float(v):
            return item[1]
    return "K"


def _get_wind_level(v: float) -> int:
    """根据风速值获取风力等级.

    Args:
        v: 风速值

    Returns:
        风力等级整数
    """
    for i in WS:
        if v <= i[0]:
            return i[1]
    return WS[-1][1]


def _get_wind_color(val: float, vals: list, colors: list) -> str:
    """根据风速值在色标中查找对应颜色.

    Args:
        val: 风速值
        vals: 色标值列表
        colors: 色标颜色列表

    Returns:
        十六进制颜色字符串
    """
    for i in range(len(vals)):
        if float(val) <= vals[i]:
            return colors[i]
    return colors[-1]


def _draw_wind_marker(ax, lon, lat, val, direction, fontsize, fontcolor, config) -> None:
    """在指定位置绘制旋转的风向标记.

    Args:
        ax: matplotlib Axes 对象
        lon: 经度
        lat: 纬度
        val: 风速值
        direction: 风向角度 (0-360)
        fontsize: 字体大小
        fontcolor: 字体颜色
        config: 渲染配置 (未使用, 保留接口兼容)
    """
    if float(direction) > 360.0:
        return
    import cartopy.crs as ccrs

    project = ccrs.PlateCarree()
    ax.text(
        lon,
        lat + 0.001,
        _get_wind_font(val),
        color=fontcolor,
        transform=project,
        va="baseline",
        ha="left",
        rotation_mode="anchor",
        fontproperties=_get_wind_font_properties(),
        rotation=360.0 - float(direction),
        fontsize=fontsize,
    )


def _get_wind_font_properties():
    """加载风向字体 (wind Bold.ttf) 的 FontProperties.

    Returns:
        matplotlib FontProperties 对象, size=50
    """
    import os

    import matplotlib.font_manager as fm

    font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "font", "wind Bold.ttf")
    return fm.FontProperties(fname=font_path, size=50)
