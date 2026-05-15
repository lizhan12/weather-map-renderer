from __future__ import annotations

import logging

import cartopy.crs as ccrs


def draw_overlay(
    fig, ax, stations: list, config: dict, state: dict, face_data: list | None = None, top_data: list | None = None
) -> None:
    """绘制叠加层: 标题/排名表/面雨量表/发布单位.

    Args:
        fig: matplotlib Figure 对象 (未使用, 保留接口兼容)
        ax: matplotlib Axes 对象
        stations: 站点数据列表 (未使用, 保留接口兼容)
        config: 渲染配置字典
        state: 状态字典 (未使用, 保留接口兼容)
        face_data: 面雨量统计数据
        top_data: 排名数据
    """
    _draw_title(ax, config)
    _draw_rank_table(ax, top_data, config)
    _draw_face_rainfall_table(ax, face_data, config)
    _draw_publisher(ax, config)


def _draw_title(ax, config: dict) -> None:
    """绘制地图标题.

    Args:
        ax: matplotlib Axes 对象
        config: 渲染配置, 包含 title/title_fontsize/title_pad 等键
    """
    title = config.get("title")
    if title:
        ax.set_title(
            title,
            fontsize=config.get("title_fontsize", 16),
            fontweight="bold",
            pad=config.get("title_pad", 15) / 80.0 * 72.0,
        )


def _draw_rank_table(ax, head: list | None, config: dict) -> None:
    """绘制站点排名表格.

    Args:
        ax: matplotlib Axes 对象
        head: 排名数据列表, 每项包含 name/val 键
        config: 渲染配置, 包含 top/top_location/unit 等键
    """
    if not head or config.get("top", 0) == 0:
        return
    loc = config.get("top_location", "0,0,0.28,0.25")
    loc = [float(i) for i in loc.split(",")]

    arr = [["Top" + str(config.get("top")) + " " + config.get("unit", "")]]
    for item in head:
        arr.append([item.get("name", "") + ":" + str(item["val"])])

    height = config.get("height", 700)
    loc[3] = ((config.get("top", 1)) * 16.0 + 25) / (height * 0.5)

    tb = ax.table(
        cellText=arr,
        colWidths=[0.2],
        cellLoc="left",
        rowLoc="left",
        bbox=loc,
    )
    tb.auto_set_font_size(False)
    tb.set_fontsize(14)
    for key, cell in tb.get_celld().items():
        cell.set_edgecolor((0, 0, 0, 0))
        if key[0] == 0:
            cell.set_height(25.0 / height)
            cell.set_text_props(weight="bold", fontsize=16)


def _draw_face_rainfall_table(ax, face: list | None, config: dict) -> None:
    """绘制面雨量统计表格.

    Args:
        ax: matplotlib Axes 对象
        face: 面雨量数据列表, 每项包含 name/val 键
        config: 渲染配置, 包含 show_face/face_location/code 等键
    """
    if not face or not config.get("show_face"):
        return
    loc = config.get("face_location", "0.7,0,0.3,0.25")
    loc = [float(i) for i in loc.split(",")]
    height = config.get("height", 700)

    arr = []
    name = "区县"
    if int(config.get("code", "000000")[2:]) == 0:
        name = "市级"
    arr.append(["各" + name + "面雨量(毫米)"])
    for item in face:
        arr.append([item.get("name", "") + ":" + str(item["val"])])

    loc[3] = (len(arr) * 25.0) / height

    tb = ax.table(
        cellText=arr,
        colWidths=[loc[2]],
        cellLoc="left",
        rowLoc="center",
        bbox=loc,
    )
    tb.auto_set_font_size(False)
    tb.set_fontsize(14)
    for key, cell in tb.get_celld().items():
        cell.set_edgecolor((0, 0, 0, 0))
        if key[0] == 0:
            cell.set_height(25.0 / height)
            cell.set_text_props(weight="bold", fontsize=16)


def _draw_publisher(ax, config: dict) -> None:
    """绘制发布单位信息表格.

    Args:
        ax: matplotlib Axes 对象
        config: 渲染配置, 包含 publisher/publisher_location 等键
    """
    publisher = config.get("publisher", "")
    if not publisher:
        return
    loc = config.get("publisher_location", "0.7,0.0,0.3,0.15")
    loc = [float(i) for i in loc.split(",")]
    height = config.get("height", 700)

    txt = publisher.split(",")
    loc[3] = 40.0 / height * len(txt)
    arr = [[t] for t in txt]

    tb = ax.table(
        cellText=arr,
        colWidths=[loc[2]],
        cellLoc="right",
        rowLoc="bottom",
        bbox=loc,
    )
    tb.auto_set_font_size(False)
    tb.set_fontsize(14)
    for key, cell in tb.get_celld().items():
        cell.set_edgecolor((0, 0, 0, 0))
        if key[0] == 0:
            cell.set_height(30.0 / height)
            cell.set_text_props(weight="bold", fontsize=16)


def draw_area_names(ax, records, config: dict, name_field: str = "TOWN") -> None:
    """在地图上绘制区划名称标注.

    Args:
        ax: matplotlib Axes 对象
        records: shapefile 记录列表, 需有 geometry.centroid 和 attributes
        config: 渲染配置, 包含 area_txtcolor/town_fontsize 等键
        name_field: 属性字段名, 默认 "TOWN"
    """
    fontcolor = config.get("area_txtcolor", "#999")
    project = ccrs.PlateCarree()
    for record in records:
        try:
            ax.text(
                record.geometry.centroid.x,
                record.geometry.centroid.y,
                record.attributes.get(name_field),
                verticalalignment="top",
                horizontalalignment="center",
                transform=project,
                fontsize=config.get("town_fontsize", 12),
                color=fontcolor,
            )
        except Exception:
            logging.debug("draw area name failed for %s: %s", name_field, record.attributes.get(name_field))
