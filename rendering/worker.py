from __future__ import annotations

import logging
import uuid

import matplotlib


matplotlib.use("agg")
import cartopy.crs as ccrs
import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage
from shapely.geometry import shape as shp_shape

from config import SHOW_MINS, settings
from config.color_maps import get_color_map, rgb_to_hex
from rendering.image_io import close_figure, create_figure, save_figure_to_file, save_figure_to_stream
from rendering.layers.base_map import clip_path, draw_border, draw_mesh_lines, get_map_extent, set_margin
from rendering.layers.overlay import _draw_face_rainfall_table, _draw_rank_table, _draw_title, draw_area_names
from rendering.layers.stations import draw_stations
from rendering.layers.wind import draw_wind_barbs
from rendering.paths import LIGHT_IMG, RAIN_IMG, SNOW_IMG
from util.interpolate import Interpolator
from util.trace import TraceContext
from util.trace_logger import TraceLogger


project = ccrs.PlateCarree()
_interpolator = Interpolator()
_logo_cache: dict[str, np.ndarray] = {}
_LOGO_SCALE = 0.25


def deserialize_shapefile_data(data: dict) -> tuple:
    """将序列化的 shapefile 字典反序列化为 records/bounds/geometries.

    Args:
        data: 序列化字典 {"attrs": [...], "geoms": [...], "bounds": ...}

    Returns:
        (records, bounds, geometries) 元组, data 为 None 时返回 (None, None, None)
    """
    if data is None:
        return None, None, None

    class _FakeRecord:
        def __init__(self, attributes, geometry):
            self.attributes = attributes
            self.geometry = geometry

        @property
        def bounds(self):
            return self.geometry.bounds

    geometries = []
    records = []

    for i, geom_data in enumerate(data["geoms"]):
        try:
            geom = shp_shape(geom_data)
            geometries.append(geom)
            records.append(_FakeRecord(data["attrs"][i], geom))
        except Exception:
            logging.warning("deserialize shape geometry failed for index %s: %s", i, geom_data)

    return records, data["bounds"], geometries


def render_in_subprocess(
    bounds, stations, records_data, pos, vals, color_types, is_rain, config, city_shape_data=None, town_shape_data=None
) -> bytes:
    """在子进程中执行完整的站点数据渲染流程.

    Args:
        bounds: 区划边界 [min_lon, min_lat, max_lon, max_lat]
        stations: 站点数据列表
        records_data: 序列化的 shapefile 数据
        pos: 站点坐标数组
        vals: 观测值数组
        color_types: [data_type, axis] 色标类型
        is_rain: 是否非降雨类型
        config: 渲染配置字典
        city_shape_data: 可选市级 shapefile 数据
        town_shape_data: 可选乡镇 shapefile 数据

    Returns:
        图片字节数据
    """
    import time as _time

    t0 = _time.time()

    trace_id = config.get("trace_id", "")
    if trace_id:
        TraceContext.set(trace_id)

    records, _, geometries = deserialize_shapefile_data(records_data)
    logging.info(f"[PERF-WORKER] deserialize main: {_time.time() - t0:.3f}s")

    t1 = _time.time()
    width = config.get("width", settings.width)
    height = config.get("height", settings.height)
    fig, ax = create_figure(width, height, config.get("show_border", False))
    logging.info(f"[PERF-WORKER] create_figure: {_time.time() - t1:.3f}s")

    t2 = _time.time()
    lines = config.get("bound_lines", [2.0, 2.0, 0.7])
    bounds_colors = config.get("bounds_colors", ["#333", "#333", "#666"])

    if config.get("is_city") and city_shape_data is not None:
        _city_records, _, city_geometries = deserialize_shapefile_data(city_shape_data)
        if city_geometries:
            ax.add_geometries(
                city_geometries, crs=project, facecolor="none", edgecolor=bounds_colors[0], linewidth=lines[0]
            )

    if config.get("show_town") and town_shape_data is not None:
        town_records, _, town_geometries = deserialize_shapefile_data(town_shape_data)
        if town_geometries:
            ax.add_geometries(
                town_geometries,
                crs=project,
                facecolor="none",
                edgecolor=bounds_colors[2],
                linewidth=lines[2],
                alpha=0.8,
            )
        if config.get("show_town_name") and town_records:
            draw_area_names(ax, town_records, config)

    if geometries is not None:
        ax.add_geometries(geometries, crs=project, facecolor="none", edgecolor=bounds_colors[1], linewidth=lines[1])

    extent = get_map_extent(ax, bounds, config)
    draw_mesh_lines(ax, config)
    draw_border(ax, show=config.get("show_border", False))

    state = {"extent": extent}
    set_margin(ax, fig, config, state)
    logging.info(f"[PERF-WORKER] draw_base_map: {_time.time() - t2:.3f}s")

    t3 = _time.time()
    colors = _resolve_colors(config, color_types)
    state["colors"] = colors

    if config.get("is_has_data") and len(config.get("data", [])) == 0:
        _set_logo(fig, config)

    lon, lat = _interpolator.get_mesh(*bounds)
    logging.info(f"[PERF-WORKER] colors+mesh: {_time.time() - t3:.3f}s, mesh_shape=({lon.shape}, {lat.shape})")

    cbar = None
    if len(vals) > 0:
        if config.get("show_contourf", True):
            t4 = _time.time()
            interplate_val = _interpolator.interpolate_grid(
                pos[:, 0], pos[:, 1], vals, [lon, lat], method=config.get("interpolation_method", "rbf")
            )
            logging.info(f"[PERF-WORKER] interpolate_grid: {_time.time() - t4:.3f}s, grid_shape={interplate_val.shape}")

            t5 = _time.time()
            if config.get("color") == "1" and color_types[0] == "rain":
                v_max = np.max(interplate_val)
                v_min = np.min(interplate_val)
                auto_colors = _get_auto_colors(v_min, v_max, config.get("axis", ""), color_types[0], config)
                state["colors"] = auto_colors

            pc = _draw_contourf(ax, lon, lat, interplate_val, config, state)
            logging.info(f"[PERF-WORKER] draw_contourf: {_time.time() - t5:.3f}s")

            t6 = _time.time()
            pc, cbar = _set_contourf_bar(ax, fig, pc, config, state)
            ax.set_extent(state["extent"], crs=project)
            clip_path(ax, records, pc, config.get("is_clip", True))
            logging.info(f"[PERF-WORKER] colorbar+clip: {_time.time() - t6:.3f}s")
        else:
            ax.set_extent(state["extent"], crs=project)
    else:
        ax.set_extent(state["extent"], crs=project)

    t7 = _time.time()
    if config.get("show_name") or config.get("show_value") or config.get("show_point"):
        draw_stations(ax, stations, config, state)

    if (config.get("show_face") or config.get("top", 0) != 0) and len(stations) > 0:
        head, face = _top_face(stations, is_rain=is_rain, config=config)
        if config.get("top", 0):
            _draw_rank_table(ax, head, config)
        if config.get("show_face") and is_rain:
            _draw_face_rainfall_table(ax, face, config)

    if config.get("show_wind"):
        draw_wind_barbs(ax, stations, config, state)

    _draw_title(ax, config)
    fig.tight_layout()
    _reset_margin(ax, cbar, config)
    logging.info(f"[PERF-WORKER] stations+tables+layout: {_time.time() - t7:.3f}s")

    t8 = _time.time()
    image_stream = save_figure_to_stream(fig)
    TraceLogger.log("image_encode", "start")
    close_figure(fig)
    logging.info(f"[PERF-WORKER] save_to_stream: {_time.time() - t8:.3f}s")
    logging.info(f"[PERF-WORKER] TOTAL: {_time.time() - t0:.3f}s")
    return image_stream.getvalue()


def render_nc_in_subprocess(bounds, records_data, lon, lat, vals, code, data_type, config, dirs) -> str:
    """在子进程中执行 NC 格点数据渲染.

    Args:
        bounds: 区划边界
        records_data: 序列化的 shapefile 数据
        lon: 经度网格
        lat: 纬度网格
        vals: 格点值二维数组
        code: 区划代码
        data_type: 数据类型
        config: 渲染配置字典
        dirs: 可选风向数据 (u, v, direction)

    Returns:
        生成的图片文件名
    """
    records, _, _geometries = deserialize_shapefile_data(records_data)
    is_zhejiang = int(code[2:]) == 0

    width = config.get("width", settings.width)
    height = config.get("height", settings.height)
    fig, ax = create_figure(width, height, config.get("show_border", False))

    _draw_title(ax, config)

    if is_zhejiang:
        city_data = config.get("city_shape_data")
        city_records, _, city_geometries = deserialize_shapefile_data(city_data)
        if city_geometries:
            bounds_colors = config.get("bounds_colors", ["#333", "#333", "#666"])
            bound_lines = config.get("bound_lines", [2.0, 2.0, 0.7])
            ax.add_geometries(
                city_geometries, crs=project, facecolor="none", edgecolor=bounds_colors[1], linewidth=bound_lines[1]
            )
            draw_area_names(ax, city_records, config, "NAME")

    if config.get("is_clip", True):
        ax.set_extent([bounds[0], bounds[2], bounds[1], bounds[3]], crs=project)

    pc, cbar = _set_contourf_bar(ax, fig, None, config, state=None, lon=lon, lat=lat, vals=vals)
    paths = clip_path(ax, records, pc, config.get("is_clip", True))

    min_lat, max_lat, min_lon, max_lon = _get_index(bounds, lat, lon)
    if not config.get("is_clip", True):
        min_lat = 0
        max_lat = len(lat) - 1
        min_lon = 0
        max_lon = len(lon) - 1

    y_step = config.get("y_step", 1)
    x_step = config.get("x_step", 1)

    sub_dirs = None
    if dirs is not None:
        sub_dirs = dirs[2][min_lat:max_lat:y_step, min_lon:max_lon:x_step]
        u = dirs[0][min_lat:max_lat:y_step, min_lon:max_lon:x_step]
        v = dirs[1][min_lat:max_lat:y_step, min_lon:max_lon:x_step]

    sub_vals = vals[min_lat:max_lat:y_step, min_lon:max_lon:x_step]
    sub_lat = lat[min_lat:max_lat:y_step]
    sub_lon = lon[min_lon:max_lon:x_step]

    n_lat = len(sub_lat)
    n_lon = len(sub_lon)

    if config.get("is_clip", True):
        grid_points = np.column_stack([np.tile(sub_lon, n_lat), np.repeat(sub_lat, n_lon)])
        inside = paths.contains_points(grid_points).reshape(n_lat, n_lon)
    else:
        inside = np.ones((n_lat, n_lon), dtype=bool)

    arr_vals = []
    lons_list = []
    lats_list = []
    us_list = []
    vs_list = []

    for i in range(n_lat):
        for j in range(n_lon):
            if not inside[i, j]:
                continue
            if config.get("show_value"):
                if data_type == "rain" and config.get("hide_rain_zero") and sub_vals[i][j] <= 0.0:
                    continue
                arr_vals.append([sub_lon[j], sub_lat[i], sub_vals[i][j]])
            if config.get("show_wind") and sub_dirs is not None:
                lons_list.append(sub_lon[j])
                lats_list.append(sub_lat[i])
                us_list.append(u[i][j])
                vs_list.append(v[i][j])

    if len(us_list) > 0:
        ax.barbs(
            np.array(lons_list),
            np.array(lats_list),
            np.array(us_list),
            np.array(vs_list),
            length=6,
            color="#333",
            pivot="middle",
            transform=project,
        )

    if len(arr_vals) > 0:
        for val in arr_vals:
            val[2] = str(int(val[2])) if data_type == "vis" else f"{val[2]:.1f}"
        for val in arr_vals:
            ax.text(
                val[0],
                val[1],
                val[2],
                transform=project,
                ha="center",
                va="center",
                fontsize=config.get("font_size", 14),
                color=config.get("font_color", "#666"),
            )

    fig.tight_layout()
    _reset_margin(ax, cbar, config)

    file_id = config.get("id") or str(uuid.uuid4())
    save_figure_to_file(fig, settings.img_data_path_resolved + f"/{file_id}.png")
    close_figure(fig)
    return f"{file_id}.png"


def _resolve_colors(config: dict, color_types: list) -> tuple:
    """从配置或色标映射解析颜色和值.

    Args:
        config: 渲染配置
        color_types: [data_type, axis]

    Returns:
        (colors, vals) 元组
    """
    custom_color = config.get("color")
    if custom_color and len(custom_color) > 2:
        tmp = custom_color.split(",")
        return tmp[::2], [float(str(item)) for item in tmp[1::2]]

    cmap = get_color_map(
        config.get("axis", ""),
        color_types[0],
        month=config.get("month", 7),
        show_contourf=config.get("show_contourf", True),
    )
    return list(
        zip(*[[rgb_to_hex(item["stop"][:3]), item["value"]] for item in cmap if item["value"] < 99999], strict=True)
    )


def _adjust_rain_levels(color_vals, data_type):
    """对降雨色标值进行调整: 在 0.1 前插入 0.05 级别."""
    if data_type == "rain" and color_vals and len(color_vals) > 1 and color_vals[1] == 0.1:
        return [color_vals[0], 0.05, *color_vals[2:]]
    return color_vals


def _draw_contourf(ax, lon, lat, grid_vals, config, state):
    """绘制填色等值线图."""
    colors = state.get("colors")
    color_vals = colors[1] if colors else None
    data_type = config.get("type", config.get("data_type", ""))

    if config.get("color") == "1" and data_type == "rain":
        return ax.contourf(lon, lat, grid_vals, extend="both", transform=ccrs.PlateCarree())

    if color_vals:
        color_vals = _adjust_rain_levels(color_vals, data_type)
        return ax.contourf(
            lon, lat, grid_vals, color_vals, extend="both", colors=colors[0], transform=ccrs.PlateCarree()
        )

    return ax.contourf(lon, lat, grid_vals, extend="both", transform=ccrs.PlateCarree())


def _set_contourf_bar(ax, fig, pc, config, state=None, lon=None, lat=None, vals=None):
    """绘制色标条, 若 pc 为 None 则先绘制 contourf (NC 渲染场景).

    Args:
        ax: matplotlib Axes 对象
        fig: matplotlib Figure 对象
        pc: 可选已有的 ContourSet 对象
        config: 渲染配置
        state: 状态字典
        lon: 经度网格 (pc=None 时需要)
        lat: 纬度网格 (pc=None 时需要)
        vals: 网格值数组 (pc=None 时需要)

    Returns:
        (pc, cbar) 元组
    """
    if pc is None:
        colors = state.get("colors") if state else None
        color_vals = colors[1] if colors else None
        data_type = config.get("type", config.get("data_type", ""))

        if config.get("color") == "1" and data_type == "rain":
            pc = ax.contourf(lon, lat, vals, extend="both", transform=ccrs.PlateCarree())
        elif color_vals:
            color_vals = _adjust_rain_levels(color_vals, data_type)
            pc = ax.contourf(lon, lat, vals, color_vals, extend="both", colors=colors[0], transform=ccrs.PlateCarree())
        else:
            pc = ax.contourf(lon, lat, vals, extend="both", transform=ccrs.PlateCarree())

    ticks = None if config.get("color") == "1" else (state.get("colors", ([], []))[1] if state else None)
    width = config.get("width", settings.width)
    bar_aspect = config.get("bar_aspect", 20)
    colors = state.get("colors", ([], []))[0] if state else []

    bar_width = config.get("bar_width")
    if bar_width is None:
        if len(colors) > 11:
            bar_width = 0.45
        elif len(colors) > 8:
            bar_width = 0.35
        else:
            bar_width = 0.3

    location = config.get("location", "bottom")
    if location in ["right", "left"]:
        ax2 = fig.add_axes([0, 0.1, bar_aspect / width, bar_width])
    else:
        bar_width += 0.15
        ax2 = fig.add_axes([0, 0.1, bar_width, bar_aspect / width])

    cbar = fig.colorbar(
        pc, cax=ax2, ticks=ticks, location=location, extendfrac=0.1 if config.get("arrow", False) else 0
    )

    _style_cbar(cbar, config, ticks)

    if config.get("unit") and config.get("show_unit"):
        loc = config.get("location", "bottom")
        label_loc = config.get("label_location", "left")
        if loc in ["right", "left"]:
            cbar.set_label(config["unit"], loc=label_loc, labelpad=5.0)
            cbar.ax.yaxis.set_label_position("left")
        else:
            cbar.set_label(config["unit"], loc=label_loc, labelpad=5)
            cbar.ax.xaxis.set_label_position("top")

    return pc, cbar


def _style_cbar(cbar, config, ticks):
    """设置色标条的刻度标签样式."""
    tick_labels = []
    source_ticks = ticks if ticks else cbar.get_ticks()
    for v in source_ticks:
        if int(v) in [-999999, 999999]:
            tick_labels.append("")
        elif float(round(v, 1)).is_integer():
            tick_labels.append(int(v))
        else:
            tick_labels.append(float(v) if ticks else round(v, 1))
    cbar.set_ticklabels(
        tick_labels, fontdict={"fontsize": config.get("bar_fontsize", 14), "color": config.get("bar_txtcolor", "#666")}
    )


def _reset_margin(ax, cbar, config):
    """重置色标条位置, 使其与主图对齐."""
    if cbar is None:
        return
    if config.get("location") == "right":
        box = ax.get_position()
        barbox = cbar.ax.get_position()
        pad = 30
        if config.get("type") == "vis":
            pad = 50
        if config.get("show_border"):
            pad = 50
            if config.get("type") == "vis":
                pad = 70
        if not config.get("title"):
            pad += 10
        if config.get("bar_pad") is not None:
            pad = config["bar_pad"]
        cbar.ax.set_position(
            [
                box.xmax - pad / config.get("width", 700),
                box.ymin + 10.0 / config.get("height", 700),
                0.02,
                barbox.height,
            ]
        )
    else:
        box = ax.get_position()
        barbox = cbar.ax.get_position()
        pad = 20
        if config.get("show_border"):
            pad = 25
        if config.get("bar_pad") is not None:
            pad = config["bar_pad"]
        cbar.ax.set_position(
            [
                box.xmin + (box.width - barbox.width) / 2,
                box.ymin + pad / config.get("height", 700),
                barbox.width,
                barbox.height,
            ]
        )


def _get_auto_colors(v_min, v_max, axis, data_type, config):
    """根据数据范围自动计算色标颜色和值."""
    cmap = get_color_map(axis, data_type, month=config.get("month", 7), show_contourf=True)
    data = list(
        zip(*[[rgb_to_hex(item["stop"][:3]), item["value"]] for item in cmap if item["value"] < 99999], strict=False)
    )
    colors = data[0]
    vals = data[1]

    if data_type == "rain":
        if int(v_min) == 0 and int(v_max) < 10:
            return colors[:5], np.linspace(0, 10, 5).round(1)
        elif int(v_min) == 0:
            return colors[:5], np.linspace(0, int(v_max) + 1, 5).round(1)
        else:
            return colors[0:5], np.linspace(0, int(v_max) + 1, 5).round(1)
    return colors, vals


def _get_index(bounds, lat, lon):
    """计算边界范围在网格中的索引范围."""
    lat_step = lat[1] - lat[0]
    lon_step = lon[1] - lon[0]
    min_lat = max(0, int((bounds[1] - lat[0]) / lat_step) - 1)
    max_lat = min(len(lat), int((bounds[3] - lat[0]) / lat_step) + 1)
    min_lon = max(0, int((bounds[0] - lon[0]) / lon_step) - 1)
    max_lon = min(len(lon), int((bounds[2] - lon[0]) / lon_step) + 1)
    return min_lat, max_lat, min_lon, max_lon


def _set_logo(fig, config):
    """在无数据时设置居中的天气类型 Logo (降雨/雷电/降雪)."""
    type_ = config.get("type", config.get("data_type", ""))
    img_key = None
    if type_ == "light":
        img_key = "light"
    elif type_ == "snow":
        img_key = "snow"
    elif type_ == "rain" and config.get("show_no_rain_logo"):
        img_key = "rain"
    else:
        return

    if img_key not in _logo_cache:
        path_map = {"light": LIGHT_IMG, "rain": RAIN_IMG, "snow": SNOW_IMG}
        img = Image.open(path_map[img_key])
        _logo_cache[img_key] = ndimage.zoom(np.array(img), (_LOGO_SCALE, _LOGO_SCALE, 1))

    snow = _logo_cache[img_key]
    img_height, img_width = snow.shape[:2]
    fig_width, fig_height = fig.get_size_inches() * fig.dpi
    center_x = fig_width / 2 - img_width / 2
    center_y = fig_height / 2 - img_height / 2
    fig.figimage(snow, xo=center_x, yo=center_y, resize=False)


def _top_face(stations, is_rain, config):
    """计算站点排名 (子进程版本, 简化版不计算面雨量)."""
    df = pd.DataFrame(stations)
    df["val"] = df["val"].astype(float)
    is_ascending = config and config.get("axis") in SHOW_MINS
    top_df = df
    if config and config.get("is_city") is False and "code" in df.columns:
        top_df = df[df["code"] == config["code"]]
    top_df = top_df.sort_values(by="val", ascending=is_ascending)
    head = top_df.head(config.get("top", 5) if config else 5)
    return list(head.to_dict(orient="index").values()), None
