from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd
from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import FileResponse, StreamingResponse

from config import UNITS, get_area_layout, settings
from config.codes import codes
from models.base import ItemImg
from util import is_city_code
from util.response_code import RET, error_map
from util.trace import TraceContext
from util.trace_logger import TraceLogger


if TYPE_CHECKING:
    from services.render_service import RenderService

_render_service: object = None


def set_service(service: RenderService) -> None:
    global _render_service
    _render_service = service


router = APIRouter(tags=["图片"])

_all_def_cache: pd.DataFrame | None = None


def _get_all_def() -> pd.DataFrame:
    global _all_def_cache
    if _all_def_cache is None:
        _all_def_cache = pd.DataFrame(codes)
    return _all_def_cache


def _parse_bounds_lines(bounds_lines: str | None, is_city: bool) -> list[float]:
    default = "2.0,1.0,0.7" if is_city else "2.0,2.0,0.7"
    src = bounds_lines if bounds_lines and len(bounds_lines.split(",")) > 2 else default
    return [float(i) for i in src.split(",")]


def _parse_bounds_colors(bounds_colors: str | None) -> list[str]:
    default = "#333,#333,#666"
    src = bounds_colors if bounds_colors and len(bounds_colors.split(",")) > 2 else default
    return src.split(",")


def _resolve_label_location(location: str) -> str:
    return "left" if location in ["bottom", "top"] else "top"


def _resolve_unit_title(unit: str | None, data_type: str) -> str | None:
    if unit is None:
        return UNITS.get(data_type)
    if unit == "0":
        return None
    return unit


def _fill_layout_defaults(config: dict, code: str, fix: bool = True) -> None:
    infoconfig = get_area_layout(code)
    if infoconfig:
        if config.get("top_location") is None:
            config["top_location"] = infoconfig.get("top_location")
        if config.get("face_location") is None:
            config["face_location"] = infoconfig.get("face_location")
        if config.get("width") is None:
            config["width"] = settings.width if fix else infoconfig.get("width")
        if config.get("height") is None:
            config["height"] = settings.height if fix else infoconfig.get("height")
    if config.get("width") is None:
        config["width"] = settings.width
    if config.get("height") is None:
        config["height"] = settings.height


def _generate_cache_id(config: dict, code: str) -> str:
    dict_str = json.dumps(config, default=str, sort_keys=True)
    digest = hashlib.md5(dict_str.encode()).hexdigest()[:16]
    return f"{digest}_{code}"


@router.get("/pic/img/{id}", response_class=StreamingResponse)
async def save_img(id: str):
    file_path = settings.img_data_path_resolved + f"/{id}.png"
    if not os.path.exists(file_path):
        file_path = settings.img_data_path_resolved + f"/{id}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Image {id} not found")
    return FileResponse(file_path)


@router.get("/pic/{code}/{datestr}/{data_type}/{axis}", response_class=StreamingResponse)
async def get_img(
    code: str = Path(..., description="行政区号6位 eg:330700"),
    datestr: str = Path(..., description="观测时间(世界时) 格式yyyyMMddHHmmss eg:20230727110000"),
    data_type: str = Path(
        ..., description="数据类型: tem(温度)/rain(降水)/wind(风速)/vis(能见度)/light(闪电)/snow(降雪)"
    ),
    axis: str = Path(
        ..., description="数据别名: TEM_H_POINT(最高温)/SUM_PRE_1H_POINT(1h降水)/WIN_S_INST_H_POINT(极大风速) 等"
    ),
    show_wind: bool = Query(False, description="是否显示风向杆 默认:false"),
    show_face: bool = Query(False, description="是否显示面雨量 默认:false"),
    show_border: bool = Query(False, description="是否显示边框 默认:false"),
    hide_rain_zero: bool = Query(True, description="是否隐藏零值降水站点 默认:true"),
    show_value: bool = Query(True, description="是否显示站点数值 默认:true"),
    show_town: bool = Query(True, description="是否显示乡镇边界 默认:true"),
    show_real_station: bool = Query(False, description="是否显示站点实际位置(否则显示乡镇位置) 默认:false"),
    show_town_name: bool = Query(False, description="是否显示乡镇名称(需show_town=true) 默认:false"),
    show_contourf: bool = Query(True, description="是否显示填色图 默认:true"),
    show_point: bool = Query(True, description="是否显示站点圆点 默认:true"),
    show_unit: bool = Query(True, description="色标是否显示单位 默认:true"),
    arrow: bool = Query(False, description="是否显示箭头 默认:false"),
    is_clip: bool = Query(True, description="是否裁剪图片至行政区边界 默认:true"),
    fix: bool = Query(True, description="是否固定图片尺寸 默认:true"),
    show_mesh: bool = Query(False, description="是否显示经纬度网格 默认:false"),
    show_name: bool | None = Query(None, description="是否显示站点名称 默认:true"),
    color: str | None = Query(
        None,
        description="自定义色标 格式:#fff,1,#000,100(颜色,值交替) 传'1'自动色标 传-999999~999999只显示对应色标范围",
    ),
    title: str | None = Query(None, description="图片标题 默认:不显示"),
    location: str = Query("bottom", description="色标位置: bottom(下方)/right(右侧)/top(上方)/left(左侧)"),
    top_location: str | None = Query(None, description="排行榜位置 格式:左,下,宽,高(百分比0~1) eg:0,0,0.28,0.25"),
    wind_location: str = Query(
        "0,0,0.28,0.25", description="风向杆区域位置 格式:左,下,宽,高(百分比0~1) eg:0,0,0.28,0.25"
    ),
    face_location: str | None = Query(None, description="面雨量区域位置 格式:左,下,宽,高(百分比0~1) eg:0,0,0.28,0.25"),
    publisher_location: str | None = Query(
        "0.7,0.0,0.3,0.1", description="发布单位区域位置 格式:左,下,宽,高(百分比0~1) eg:0.7,0.0,0.3,0.1"
    ),
    mesh_padding: str = Query(
        "0.0,0.0,0.0,0.0", description="地图内边距(经纬度单位) 格式:上,右,下,左 eg:0.1,0.1,0.1,0.1"
    ),
    unit: str | None = Query(None, description="单位标题 '0'不显示 不传显示默认 其他显示传入值"),
    width: int | None = Query(None, description="图片宽度(像素) 默认:配置文件值"),
    height: int | None = Query(None, description="图片高度(像素) 默认:配置文件值"),
    top: int = Query(0, description="取排名前N个站点 0表示不限制"),
    start_time: str | None = Query(None, description="起始时间(世界时) 格式yyyyMMddHHmmss"),
    wind_fontsize: int | None = Query(20, description="风向杆字体大小(磅)"),
    wind_color: str | None = Query("blue", description="风向杆颜色 eg:blue/#00f"),
    point_color: str | None = Query("#666", description="站点圆点颜色 eg:#666"),
    txt_fontcolor: str | None = Query("#666", description="站点名称字体颜色 eg:#666"),
    val_fontcolor: str | None = Query("#666", description="站点数值字体颜色 eg:#666"),
    bar_aspect: int = Query(20, description="色标长宽比"),
    bar_width: float | None = Query(None, description="色标高度占比(0~1)"),
    bar_fontsize: int = Query(14, description="色标字体大小(磅)"),
    bar_txtcolor: str = Query("#666", description="色标字体颜色 eg:#666"),
    area_txtcolor: str = Query("#999", description="区域名称字体颜色 eg:#999"),
    bar_pad: float | None = Query(None, description="色标距离边框的距离(像素)"),
    txt_fontsize: int = Query(14, description="站点名称字体大小(磅)"),
    val_fontsize: int = Query(14, description="站点数值字体大小(磅)"),
    town_fontsize: int = Query(12, description="乡镇名称字体大小(磅)"),
    title_fontsize: int = Query(16, description="标题字体大小(磅)"),
    title_pad: int = Query(15, description="标题距离图片的间距(像素)"),
    bar_margin: int = Query(95, description="色标距离图片的间距(像素)"),
    offset_lat: float = Query(15.0, description="纬度偏移量(度)"),
    bounds_lines: str | None = Query(
        None, description="边界线宽度(磅) 格式:主边界,区县边界,乡镇边界 eg:2,1.5,0.7 必须3个数"
    ),
    bounds_colors: str | None = Query(
        None, description="边界线颜色 格式:主边界,区县边界,乡镇边界 eg:#333,#333,#666 必须3个数"
    ),
    publisher: str = Query("", description="发布单位文字"),
) -> StreamingResponse:
    is_city = is_city_code(code)
    month = int(datestr[4:6]) if datestr and len(datestr) >= 6 else datetime.now().month

    request_config = {
        "hide_rain_zero": hide_rain_zero,
        "month": month,
        "show_wind": show_wind,
        "show_name": show_name if show_name is not None else True,
        "show_real_station": show_real_station,
        "show_value": show_value,
        "show_border": show_border,
        "show_face": show_face,
        "show_point": show_point,
        "show_contourf": show_contourf,
        "show_mesh": show_mesh,
        "show_unit": show_unit,
        "color": color,
        "bar_txtcolor": bar_txtcolor,
        "wind_fontsize": wind_fontsize,
        "wind_color": wind_color,
        "txt_fontcolor": txt_fontcolor,
        "val_fontcolor": val_fontcolor,
        "area_txtcolor": area_txtcolor,
        "point_color": point_color,
        "title": title,
        "location": location,
        "is_clip": is_clip,
        "label_location": _resolve_label_location(location),
        "unit": _resolve_unit_title(unit, data_type),
        "width": width,
        "start_time": start_time,
        "height": height,
        "code": code,
        "show_town": show_town,
        "show_town_name": show_town_name,
        "axis": axis,
        "top": top,
        "publisher_location": publisher_location,
        "top_location": top_location,
        "wind_location": wind_location,
        "face_location": face_location,
        "arrow": arrow,
        "bar_aspect": bar_aspect,
        "bar_fontsize": bar_fontsize,
        "bar_width": bar_width,
        "bar_pad": bar_pad,
        "txt_fontsize": txt_fontsize,
        "val_fontsize": val_fontsize,
        "town_fontsize": town_fontsize,
        "title_pad": title_pad,
        "offset_lat": offset_lat,
        "bar_margin": bar_margin,
        "title_fontsize": title_fontsize,
        "bound_lines": _parse_bounds_lines(bounds_lines, is_city),
        "mesh_padding": mesh_padding,
        "bounds_colors": _parse_bounds_colors(bounds_colors),
        "datestr": datestr,
        "is_city": is_city,
        "publisher": publisher,
        "type": data_type,
    }

    _fill_layout_defaults(request_config, code, fix)
    request_config["id"] = _generate_cache_id(request_config, code)
    TraceContext.set(request_config["id"])
    TraceLogger.log("request_received", f"GET {code}/{datestr}/{data_type}/{axis}")

    try:
        image_stream = await _render_service.render(request_config)
        TraceLogger.log("response_sent", "success")
    except Exception as e:
        logging.error(f"Render error: {e}", exc_info=True)
        TraceLogger.log("response_sent", f"error: {e}", logging.ERROR)
        raise HTTPException(status_code=500, detail=str(e)) from None

    if isinstance(image_stream, str):
        file_path = settings.img_data_path_resolved + "/" + image_stream
        if os.path.exists(file_path):
            return FileResponse(file_path)
        logging.warning(f"Cache file missing: {file_path}, re-rendering")
        request_config["id"] = _generate_cache_id(request_config, code) + "_retry"
        try:
            image_stream = await _render_service.render(request_config)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from None
        if isinstance(image_stream, str):
            return FileResponse(settings.img_data_path_resolved + "/" + image_stream)
    image_stream.seek(0)
    return StreamingResponse(image_stream, media_type="image/png")


@router.post("/pic/{code}/{data_type}")
async def create_img(
    code: str = Path(..., description="行政区号6位 eg:330500"),
    data_type: str = Path(..., description="类型 eg:wind,rain,tem,vis,light,snow"),
    item: ItemImg = ItemImg(),
):
    request_config = item.model_dump()
    is_city = is_city_code(code)

    request_config["bound_lines"] = _parse_bounds_lines(request_config.get("bounds_lines"), is_city)
    request_config["bounds_colors"] = _parse_bounds_colors(request_config.get("bounds_colors"))
    request_config["label_location"] = _resolve_label_location(request_config.get("location", "bottom"))

    unit = request_config.get("unit")
    if unit == "0":
        request_config["unit"] = None
    elif unit is None:
        request_config["unit"] = UNITS.get(data_type)

    request_config["is_has_data"] = True

    if request_config.get("filter_list") is not None:
        request_config["filter_list"] = [x for x in request_config.get("filter_list").split(",") if len(x) > 0]

    if request_config.get("show_name") is None:
        request_config["show_name"] = bool(is_city)

    request_config["code"] = code
    request_config["is_city"] = is_city
    request_config["month"] = datetime.now().month
    request_config["type"] = data_type

    _fill_layout_defaults(request_config, code, request_config.get("fix", True))
    request_config["id"] = _generate_cache_id(request_config, code)
    TraceContext.set(request_config["id"])
    TraceLogger.log("request_received", f"POST {code}/{data_type}")

    datas = request_config.get("data")
    gen_all = request_config.get("gen_all")

    all_tasks = []
    all_keys = []

    if gen_all:
        all_tasks = []
        all_keys = []
        all_cache_ids = []

        request_config["id"] = _generate_cache_id(request_config, code)
        all_tasks.append(_render_service.render(request_config))
        all_keys.append(code)
        all_cache_ids.append(request_config["id"])

        df = pd.DataFrame(request_config["data"])
        if "lon" in df.columns and "lat" in df.columns and "val" in df.columns:
            df = df.dropna(subset=["lon", "lat", "val"])
        parentconfig = request_config.copy()
        del parentconfig["data"]
        del parentconfig["code"]

        if "Admin_Code_CHN" in df.columns:
            df["Admin_Code_CHN"] = pd.to_numeric(df["Admin_Code_CHN"], errors="coerce").astype("Int64")
            df["Admin_Code_CHN"] = df["Admin_Code_CHN"].astype("str")
            df["code"] = df["Admin_Code_CHN"].str.slice(0, 6)

        if is_city:
            codedf = _get_all_def()[_get_all_def()["code"].str.startswith(code[0:4])].copy()
            codedf["code1"] = codedf["code"].apply(lambda x: str(x)[0:6])
            grouped = codedf.groupby(by="code1")
            if request_config.get("show_name") is None:
                request_config["show_name"] = False

            for name, _group in grouped:
                sub_config = request_config.copy()
                dat = []
                if len(sub_config.get("data", [])) > 0:
                    dat = df[df["code"] == name].to_dict(orient="records")
                infoconfig = item.subconfig.get(str(name))
                if infoconfig is None:
                    infoconfig = get_area_layout(name)
                sub_config["code"] = name
                sub_config["is_city"] = False
                sub_config["data"] = dat
                if infoconfig:
                    sub_config = {**sub_config, **infoconfig}
                sub_config.pop("id", None)
                sub_config["id"] = _generate_cache_id(sub_config, name)
                all_tasks.append(_render_service.render(sub_config))
                all_keys.append(name)
                all_cache_ids.append(sub_config["id"])

        request_config["gen"] = True
        codedf = _get_all_def()[_get_all_def()["code"].str.startswith(code[0:6])].copy()
        grouped = codedf.groupby(by="code")
        parentconfig["is_city"] = False

        for name, _group in grouped:
            if len(name) <= 6:
                continue
            sub_config = request_config.copy()
            infoconfig = item.subconfig.get(str(name))
            arr = []
            if infoconfig is None:
                infoconfig = get_area_layout(name)
            if len(datas) > 0:
                arr = df[df["Admin_Code_CHN"] == name].to_dict(orient="records")
            sub_config["code"] = name
            sub_config["is_city"] = False
            sub_config["data"] = arr
            sub_config = {**sub_config, **infoconfig} if infoconfig else {**sub_config, **parentconfig}
            sub_config.pop("id", None)
            sub_config["id"] = _generate_cache_id(sub_config, name)
            all_tasks.append(_render_service.render(sub_config))
            all_keys.append(name)
            all_cache_ids.append(sub_config["id"])

        all_results = await asyncio.gather(*all_tasks, return_exceptions=True)
        ids = []
        for key, cache_id, result in zip(all_keys, all_cache_ids, all_results, strict=False):
            if isinstance(result, Exception):
                logging.error("Render error for %s: %s", key, result, exc_info=True)
                ids.append({key: None, "error": f"{type(result).__name__}: {result}"})
            else:
                ids.append({key: cache_id})
    else:
        try:
            id = await _render_service.render(request_config)
            TraceLogger.log("response_sent", "success")
        except Exception as e:
            logging.error(f"Render error: {e}", exc_info=True)
            TraceLogger.log("response_sent", f"error: {e}", logging.ERROR)
            raise HTTPException(status_code=500, detail=str(e)) from None
        ids = [id]

    return {"DS": ids, "returnCode": RET.OK, "returnMessage": error_map[RET.OK]}
