from __future__ import annotations

import cartopy.crs as ccrs
import frykit.plot as fplt
import numpy as np
from cartopy.mpl.gridliner import LatitudeFormatter, LongitudeFormatter
from cartopy.mpl.patch import geos_to_path
from matplotlib.path import Path


def calc_extent(bounds: list, config: dict) -> list:
    """根据 bounds 和配置计算地图显示范围.

    处理流程:
    1. 将 bounds [min_lon, min_lat, max_lon, max_lat] 转为 extent [min_lon, max_lon, min_lat, max_lat]
    2. 根据 show_border 向外扩展边框留白
    3. 根据色标位置 (location) 和色标宽度 (bar_margin) 为色标预留空间
    4. 根据 mesh_padding 向四个方向扩展显示范围

    Args:
        bounds: 区划边界 [min_lon, min_lat, max_lon, max_lat]
        config: 渲染配置字典, 需包含 show_border/location/bar_margin/mesh_padding 等键

    Returns:
        调整后的 extent [min_lon, max_lon, min_lat, max_lat]
    """
    extent = [bounds[0], bounds[2], bounds[1], bounds[3]]
    x_range = extent[1] - extent[0]
    y_range = extent[3] - extent[2]

    w = config.get("width", 700)
    h = config.get("height", 700)
    base = min(w, h)
    show_border = config.get("show_border", False)
    location = config.get("location", "bottom")
    bar_margin = config.get("bar_margin", 95)
    data_len = len(config.get("data", []))
    is_has_data = config.get("is_has_data", True)
    has_no_stations = is_has_data and data_len == 0
    is_horizontal = location in ("right", "left")

    if show_border:
        extent[0] -= x_range / base * 10
        extent[1] += x_range / base * 10
        extent[2] -= y_range / base * 10
        extent[3] += y_range / base * 10
        if not has_no_stations:
            if is_horizontal:
                extent[1] += x_range / base * bar_margin
            else:
                extent[2] -= y_range / base * (bar_margin - 25.0)
    else:
        if not has_no_stations:
            if is_horizontal:
                extent[1] += x_range / base * (bar_margin - 35.0)
            else:
                extent[2] -= y_range / base * (bar_margin - 25.0)

    mesh_padding_str = config.get("mesh_padding", "0.0, 0.0, 0.0, 0.0")
    if mesh_padding_str:
        pad = [float(i) for i in mesh_padding_str.split(",")]
        extent[0] -= pad[3]
        extent[1] += pad[1]
        extent[2] -= pad[2]
        extent[3] += pad[0]

    return extent


def get_map_extent(ax, bounds: list, config: dict) -> list:
    """计算最终地图显示范围 (含 1:1 比例校正).

    在 calc_extent 基础上, 通过迭代调整使投影后的宽高比为 1:1,
    确保地图在画布上不变形.

    Args:
        ax: matplotlib Axes 对象 (需有 projection 属性)
        bounds: 区划边界 [min_lon, min_lat, max_lon, max_lat]
        config: 渲染配置字典

    Returns:
        校正后的 extent [min_lon, max_lon, min_lat, max_lat]
    """
    extent = calc_extent(bounds, config)
    return _adjust_extent_to_1_1(ax, extent)


def draw_mesh_lines(ax, config: dict) -> None:
    """绘制经纬网格线和标签.

    仅在 show_border=True 且 show_mesh=True 时绘制网格,
    否则隐藏坐标轴.

    Args:
        ax: matplotlib Axes 对象
        config: 渲染配置字典, 需包含 show_border/show_mesh/is_inner 等键
    """
    show = config.get("show_border", False) and config.get("show_mesh", False)
    if not show:
        ax.axis("off")
        return

    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color="#ddd", linestyle="--")
    gl.xlabel_style = {"size": 14, "color": "#333"}
    gl.ylabel_style = {"size": 14, "color": "#333"}

    is_inner = config.get("is_inner", True)
    gl.xformatter = LongitudeFormatter(number_format=".2f", degree_symbol="", direction_label=False)
    gl.yformatter = LatitudeFormatter(number_format=".2f", degree_symbol=" ", direction_label=False)
    gl.xlines = is_inner
    gl.ylines = is_inner
    gl.top_labels = is_inner
    gl.right_labels = is_inner


def draw_border(ax, show: bool, color: str = "black") -> None:
    """绘制地图边框.

    Args:
        ax: matplotlib Axes 对象
        show: 是否显示边框
        color: 边框颜色, 默认黑色
    """
    if not show:
        return
    for spine in ["top", "bottom", "left", "right"]:
        ax.spines[spine].set_color(color)
        ax.spines[spine].set_visible(True)
        ax.spines[spine].set_linewidth(1.5)
    ax.axis(True)


def clip_path(ax, records, pc, is_clip: bool) -> Path:
    """裁剪绘图对象到区划边界, 并返回复合路径.

    当 is_clip=True 时, 将绘图对象 (pc) 裁剪到区划多边形范围内,
    使色斑图不超出行政边界. 无论是否裁剪, 都返回区划边界的 Path 对象.

    Args:
        ax: matplotlib Axes 对象 (未使用, 保留接口兼容)
        records: shapefile 记录列表, 每条记录需有 geometry 属性
        pc: matplotlib 集合对象 (如 contourf 返回值), 用于裁剪
        is_clip: 是否执行裁剪

    Returns:
        区划边界的复合 Path 对象
    """
    paths = [record.geometry for record in records]
    if is_clip:
        fplt.clip_by_polygon(pc, paths)
    return Path.make_compound_path(*geos_to_path(paths))


def set_margin(ax, fig, config: dict, state: dict) -> None:
    """设置图形边距并调整子图布局.

    根据 show_border/show_mesh/show_title 等配置计算四边边距,
    然后调用 fig.subplots_adjust 应用到图形布局.

    边距规则:
    - 默认四边均为 10 像素
    - show_border + show_mesh: 左侧 55px (经度标签), 右侧 52px (is_inner) 或 30px
    - 无 border 有 title: 顶部额外增加 15px

    Args:
        ax: matplotlib Axes 对象 (未使用, 保留接口兼容)
        fig: matplotlib Figure 对象
        config: 渲染配置字典
        state: 状态字典, 写入 margin 和 margin_per
    """
    show_border = config.get("show_border", False)
    show_mesh = config.get("show_mesh", False)
    show_title = config.get("title") is not None
    is_inner = config.get("is_inner", True)

    margin_top = 10
    margin_right = 10
    margin_bottom = 10
    margin_left = 10

    if show_border and show_mesh:
        margin_left = 55
        margin_right = 52 if is_inner else 30

    if not show_border and show_title:
        margin_top += 15

    state["margin"] = [margin_top, margin_right, margin_bottom, margin_left]

    height = config.get("height", 700)
    width = config.get("width", 700)

    top = margin_top / height
    right = margin_right / width
    bottom = margin_bottom / height
    left = margin_left / width

    state["margin_per"] = [left, bottom, 1.0 - right * 2, 1.0 - top * 2.0]
    fig.subplots_adjust(left=left, right=1.0 - right * 2, bottom=bottom, top=1.0 - top * 2.0)


def _adjust_extent_to_1_1(ax, extent: list, tolerance: float = 1e-3, max_iters: int = 30) -> list:
    """迭代调整 extent 使投影后的宽高比为 1:1.

    地图投影会导致经纬度范围与实际像素范围不一致,
    此函数通过迭代扩展较窄的维度, 使投影后的显示区域为正方形.

    Args:
        ax: matplotlib Axes 对象 (需有 projection 属性)
        extent: 待调整的 extent [min_lon, max_lon, min_lat, max_lat]
        tolerance: 宽高比与 1 的容差, 默认 0.001
        max_iters: 最大迭代次数, 默认 30

    Returns:
        调整后的 extent [min_lon, max_lon, min_lat, max_lat]
    """
    proj = ax.projection
    for _ in range(max_iters):
        corners = np.array(
            [
                [extent[0], extent[2]],
                [extent[1], extent[2]],
                [extent[1], extent[3]],
                [extent[0], extent[3]],
            ]
        )
        transformed_corners = proj.transform_points(ccrs.PlateCarree(), corners[:, 0], corners[:, 1])
        x_coords = transformed_corners[:, 0]
        y_coords = transformed_corners[:, 1]

        proj_width = x_coords.max() - x_coords.min()
        proj_height = y_coords.max() - y_coords.min()
        ratio = proj_width / proj_height

        if abs(ratio - 1) < tolerance:
            break

        if ratio > 1:
            center_lat = (extent[2] + extent[3]) / 2
            lat_range = (extent[3] - extent[2]) * ratio
            extent[2] = center_lat - lat_range / 2
            extent[3] = center_lat + lat_range / 2
        else:
            center_lon = (extent[0] + extent[1]) / 2
            lon_range = (extent[1] - extent[0]) / ratio
            extent[0] = center_lon - lon_range / 2
            extent[1] = center_lon + lon_range / 2

    return extent
