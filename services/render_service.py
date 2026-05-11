from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from io import BytesIO

from config.settings import settings
from services.data_service import DataService
from services.shape_service import ShapeService
from util.trace import TraceContext
from util.trace_logger import TraceLogger


_process_pool: ProcessPoolExecutor | None = None
_cache_write_count = 0
_CLEANUP_INTERVAL = 20


def _cache_path(cache_key: str) -> str:
    """拼接缓存文件完整路径."""
    return os.path.join(settings.img_data_path_resolved, f"{cache_key}.png")


def _cache_exists(cache_key: str) -> bool:
    """检查缓存文件是否存在且未过期, 过期则删除."""
    path = _cache_path(cache_key)
    if not os.path.exists(path):
        return False
    if time.time() - os.path.getmtime(path) < settings.cache_ttl:
        return True
    os.remove(path)
    return False


def _cache_set(cache_key: str, data: bytes) -> None:
    """将图片数据写入 imgs 目录, 每隔 _CLEANUP_INTERVAL 次写入触发清理."""
    global _cache_write_count

    cache_dir = settings.img_data_path_resolved
    os.makedirs(cache_dir, exist_ok=True)
    with open(os.path.join(cache_dir, f"{cache_key}.png"), "wb") as f:
        f.write(data)

    _cache_write_count += 1
    if _cache_write_count % _CLEANUP_INTERVAL != 0:
        return

    files = sorted(
        (os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith(".png")),
        key=os.path.getmtime,
    )
    for old in files[: -settings.cache_max_files]:
        with contextlib.suppress(OSError):
            os.remove(old)


def _init_subprocess():
    """子进程初始化: 配置 matplotlib 后端/字体, 并预热 cartopy 渲染管线."""
    import matplotlib

    matplotlib.use("agg")
    import matplotlib.font_manager as fm

    from rendering.paths import SIMHEI_FONT

    fm.fontManager.addfont(SIMHEI_FONT)
    matplotlib.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False

    from io import BytesIO as _Buf

    import cartopy.crs as ccrs
    from matplotlib.figure import Figure
    from shapely.geometry import Polygon

    fig = Figure(figsize=[4, 4], dpi=80)
    ax = fig.add_subplot(projection=ccrs.Mercator())
    ax.set_extent([118.0, 123.0, 27.0, 31.5], crs=ccrs.PlateCarree())
    ax.set_title("预热")
    test_geom = Polygon([(119, 28), (120, 28), (120, 29), (119, 29)])
    ax.add_geometries([test_geom], crs=ccrs.PlateCarree(), facecolor="none", edgecolor="#333", linewidth=1.0)
    buf = _Buf()
    fig.savefig(buf, format="png")
    fig.clear()
    logging.info("subprocess warmup completed")


def _get_process_pool() -> ProcessPoolExecutor:
    """获取或创建渲染进程池, 崩溃时自动重建."""
    global _process_pool
    if _process_pool is None:
        max_workers = settings.render_workers or min(os.cpu_count() or 1, settings.render_max_workers)
        _process_pool = ProcessPoolExecutor(max_workers=max_workers, initializer=_init_subprocess)
    return _process_pool


def _should_save(config: dict, station_count: int) -> bool:
    """判断是否应返回文件名而非字节流: POST 请求或站点数 >= 10."""
    return config.get("is_has_data") or station_count >= 10


class RenderService:
    """渲染服务: 协调数据获取/shapefile 加载/子进程渲染/缓存管理."""

    def __init__(self, shape_service: ShapeService, data_service: DataService):
        """初始化渲染服务.

        Args:
            shape_service: shapefile 服务实例
            data_service: 数据服务实例
        """
        self._shape_service = shape_service
        self._data_service = data_service

    async def render(self, config: dict) -> BytesIO | str:
        """执行完整的渲染流程: 缓存检查 -> 数据获取 -> shapefile 加载 -> 子进程渲染 -> 缓存写入.

        Args:
            config: 渲染配置字典, 需包含 id/code/type/axis/datestr 等键

        Returns:
            BytesIO (直接返回图片) 或 str (返回文件名, should_save 模式)

        Raises:
            Exception: 数据获取失败或边界数据缺失
        """
        t_start = time.time()
        code = str(config.get("code", ""))
        cache_key = config["id"]

        if _cache_exists(cache_key):
            logging.info(f"[PERF] cache hit: {time.time() - t_start:.3f}s")
            TraceLogger.log("response_sent", "cache_hit")
            return f"{cache_key}.png"

        loop = asyncio.get_running_loop()

        shape_tasks: dict[str, asyncio.Task] = {}
        shape_tasks["main_shape_data"] = loop.run_in_executor(None, self._shape_service.get_serialized, code, "_county")
        if config.get("is_city"):
            shape_tasks["city_shape_data"] = loop.run_in_executor(None, self._shape_service.get_serialized, code, "")
        if config.get("show_town") and len(code) < 8:
            shape_tasks["town_shape_data"] = loop.run_in_executor(
                None, self._shape_service.get_serialized, code, "_town"
            )

        if config.get("is_has_data"):
            vals, pos, stations = self._data_service.handle_data(
                config.get("data", []), code, config.get("is_city", False)
            )
            TraceLogger.log("data_process", f"stations={len(stations)}")
            t_parallel = time.time()
            TraceLogger.log("shape_serialize")
            shape_results = await asyncio.gather(*shape_tasks.values())
            logging.info(f"[PERF] get_shape: {time.time() - t_parallel:.3f}s, vals={len(vals)}")
        else:
            data_task = self._data_service.get_data(
                config.get("axis", ""), code, config.get("datestr"), config.get("start_time"), config.get("is_city", False)
            )
            t_parallel = time.time()
            TraceLogger.log("shape_serialize")
            data_result, shape_results = await asyncio.gather(
                data_task,
                asyncio.gather(*shape_tasks.values()),
            )
            vals, pos, stations = data_result
            logging.info(f"[PERF] get_data+get_shape parallel: {time.time() - t_parallel:.3f}s, vals={len(vals)}")

        shape_map = dict(zip(shape_tasks.keys(), shape_results, strict=True))
        main_shape_data = shape_map.get("main_shape_data")
        city_shape_data = shape_map.get("city_shape_data")
        town_shape_data = shape_map.get("town_shape_data")

        if len(vals) == 0 and not config.get("is_has_data"):
            msg = "无法获取站点数据, 请检查 data_service_url 和密钥配置"
            raise Exception(msg)

        if main_shape_data is None or main_shape_data.get("bounds") is None:
            msg = "无法获取边界数据"
            raise Exception(msg)

        bounds = main_shape_data["bounds"]
        stations, _ = self._data_service.filter_stations(stations, config)
        logging.info(f"[PERF] filter_stations: stations={len(stations)}")

        t7 = time.time()
        logging.info(f"[PERF] total pre-render: {t7 - t_start:.3f}s, starting subprocess...")

        config["trace_id"] = TraceContext.get()
        config["_bounds"] = bounds
        config["_stations"] = stations
        config["_main_shape_data"] = main_shape_data
        config["_pos"] = pos
        config["_vals"] = vals
        config["_city_shape_data"] = city_shape_data
        config["_town_shape_data"] = town_shape_data

        TraceLogger.log("subprocess_render")
        try:
            result = await loop.run_in_executor(_get_process_pool(), _subprocess_render, config)
        except BrokenProcessPool:
            global _process_pool
            _process_pool = None
            result = await loop.run_in_executor(_get_process_pool(), _subprocess_render, config)

        del config["_bounds"]
        del config["_stations"]
        del config["_main_shape_data"]
        del config["_pos"]
        del config["_vals"]
        del config["_city_shape_data"]
        del config["_town_shape_data"]

        logging.info(f"[PERF] subprocess_render: {time.time() - t7:.3f}s")
        logging.info(f"[PERF] TOTAL: {time.time() - t_start:.3f}s")

        _cache_set(cache_key, result)

        if _should_save(config, len(stations)):
            return f"{cache_key}.png"
        return BytesIO(result)

    async def render_nc(self, lon, lat, vals, code, data_type, config, dirs=None) -> str:
        """渲染 NC 格点数据为图片文件.

        Args:
            lon: 经度网格
            lat: 纬度网格
            vals: 格点值数组
            code: 区划代码
            data_type: 数据类型
            config: 渲染配置字典
            dirs: 可选风向数据

        Returns:
            生成的图片文件名, 失败返回空字符串
        """
        is_zhejiang = int(code[2:]) == 0
        tail = "_city" if is_zhejiang else "_county"

        loop = asyncio.get_running_loop()
        records_data = await loop.run_in_executor(None, self._shape_service.get_serialized, code, tail)

        if is_zhejiang:
            config["city_shape_data"] = await loop.run_in_executor(
                None, self._shape_service.get_serialized, code, ""
            )

        if records_data is None or records_data.get("bounds") is None:
            return ""

        return await loop.run_in_executor(
            _get_process_pool(),
            _subprocess_render_nc,
            records_data["bounds"],
            records_data,
            lon,
            lat,
            vals,
            code,
            data_type,
            config,
            dirs,
        )


def _subprocess_render(config: dict) -> bytes:
    """子进程入口: 从 config 字典提取参数并调用 worker 渲染.

    Args:
        config: 渲染配置字典, 需包含 _bounds/_stations/_main_shape_data 等内部键

    Returns:
        图片字节数据
    """
    import logging as _logging
    import time as _time

    _logging.basicConfig(level=_logging.INFO)
    t0 = _time.time()
    from rendering.worker import render_in_subprocess

    _logging.info(f"[PERF-SUB] import worker: {_time.time() - t0:.3f}s")
    t1 = _time.time()
    result = render_in_subprocess(
        config["_bounds"],
        config["_stations"],
        config["_main_shape_data"],
        config["_pos"],
        config["_vals"],
        [config.get("type", config.get("data_type", "")), config.get("axis", "")],
        config.get("type", "") != "rain",
        config,
        config.get("_city_shape_data"),
        config.get("_town_shape_data"),
    )
    _logging.info(f"[PERF-SUB] render_in_subprocess: {_time.time() - t1:.3f}s")
    return result


def _subprocess_render_nc(bounds, records_data, lon, lat, vals, code, data_type, config, dirs):
    """子进程入口: 执行 NC 格点数据渲染.

    Args:
        bounds: 区划边界
        records_data: 序列化的 shapefile 数据
        lon: 经度网格
        lat: 纬度网格
        vals: 格点值数组
        code: 区划代码
        data_type: 数据类型
        config: 渲染配置字典
        dirs: 风向数据

    Returns:
        生成的图片文件名
    """
    from rendering.worker import render_nc_in_subprocess

    return render_nc_in_subprocess(bounds, records_data, lon, lat, vals, code, data_type, config, dirs)
