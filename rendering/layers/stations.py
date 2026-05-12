from __future__ import annotations

import cartopy.crs as ccrs
from matplotlib.transforms import ScaledTranslation


def draw_stations(ax, stations: list, config: dict, state: dict) -> None:
    """在地图上绘制站点名称/观测值/标记点.

    站点位置通过 Mercator 投影转换, 文本和标记使用 ScaledTranslation
    实现像素级偏移, 避免与风向杆重叠.

    Args:
        ax: matplotlib Axes 对象
        stations: 站点数据列表, 每项包含 lon/lat/name/val 键
        config: 渲染配置, 包含 show_name/show_value/show_point/字体颜色等键
        state: 状态字典 (未使用, 保留接口兼容)
    """
    show_name = config.get("show_name", False)
    show_value = config.get("show_value", True)
    show_point = config.get("show_point", False)
    offset_y = config.get("offset_lat", 15.0) if config.get("show_real_station", True) else 0.0
    offset_x = 0

    trans_name = ax.transData + ScaledTranslation(
        offset_x / ax.figure.dpi,
        (offset_y + 2) / ax.figure.dpi,
        ax.figure.dpi_scale_trans,
    )
    trans_value = ax.transData + ScaledTranslation(
        offset_x / ax.figure.dpi,
        (offset_y - 1) / ax.figure.dpi,
        ax.figure.dpi_scale_trans,
    )
    trans_point = ax.transData + ScaledTranslation(
        offset_x / ax.figure.dpi,
        offset_y / ax.figure.dpi,
        ax.figure.dpi_scale_trans,
    )

    projection = ccrs.Mercator()
    arr = []
    for station in stations:
        lon, lat = float(station["lon"]), float(station["lat"])
        x, y = projection.transform_point(lon, lat, ccrs.PlateCarree())
        arr.append([x, y, station["name"], station["val"]])

    if show_name:
        for item in arr:
            ax.text(
                item[0],
                item[1],
                item[2],
                color=config.get("txt_fontcolor", "#666"),
                verticalalignment="bottom",
                horizontalalignment="center",
                fontsize=config.get("txt_fontsize", 14),
                transform=trans_name,
            )

    if show_value:
        for item in arr:
            ax.text(
                item[0],
                item[1],
                item[3],
                color=config.get("val_fontcolor", "#666"),
                verticalalignment="top",
                horizontalalignment="center",
                fontsize=config.get("val_fontsize", 14),
                transform=trans_value,
            )

    if show_point:
        for item in arr:
            ax.scatter(
                item[0],
                item[1],
                s=8,
                transform=trans_point,
                color=config.get("point_color", "#666"),
                marker="o",
            )
