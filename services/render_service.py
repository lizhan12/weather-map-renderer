from __future__ import annotations

import asyncio
import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

from config import settings
from services.data_service import DataService
from services.shape_service import ShapeService
from util.file_dir_io import get_file_name


MAX_QUEUE_SIZE = 32

_process_pool: ProcessPoolExecutor | None = None
_queue: asyncio.Queue | None = None


def _get_process_pool() -> ProcessPoolExecutor:
    global _process_pool
    if _process_pool is None:
        max_workers = settings.render_workers if settings.render_workers > 0 else settings.render_max_workers
        _process_pool = ProcessPoolExecutor(
            max_workers=max_workers,
            initializer=_init_worker,
        )
    return _process_pool


async def shutdown_render_service():
    global _process_pool
    if _process_pool is not None:
        _process_pool.shutdown(wait=True)
        _process_pool = None
    _queue = None


def _init_worker():
    import matplotlib

    matplotlib.use("agg")
    import matplotlib.font_manager as fm

    from rendering.paths import SIMHEI_FONT

    fm.fontManager.addfont(SIMHEI_FONT)
    matplotlib.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False


_sub_shape_service: ShapeService | None = None


def _sub_process_serialize_shape(code: str, tail: str):
    """子进程版本 shape 序列化, 使用进程级缓存的 ShapeService."""
    global _sub_shape_service
    from services.shape_service import ShapeService

    if _sub_shape_service is None:
        _sub_shape_service = ShapeService(shape_dir=settings.shape_path_resolved, areas={})
    return _sub_shape_service.get_serialized(code, tail)


def _cache_get(key):
    try:
        file_name = get_file_name(key)
        if os.path.exists(file_name) and time.time() - os.stat(file_name).st_mtime < settings.cache_ttl:
            with open(file_name, "rb") as f:
                return f.read()
    except Exception:
        pass
    return None


def _cache_set(key, content):
    try:
        file_name = get_file_name(key)
        _clean_old_files(settings.cache_max_files)
        with open(file_name, "wb") as f:
            f.write(content)
    except Exception:
        pass


def _clean_old_files(max_files: int):
    try:
        cache_dir = settings.img_data_path_resolved
        if not os.path.isdir(cache_dir):
            return
        files = [
            (os.path.join(cache_dir, f), os.path.getmtime(os.path.join(cache_dir, f)))
            for f in os.listdir(cache_dir)
            if f.endswith(".png")
        ]
        if len(files) > max_files:
            files.sort(key=lambda x: x[1])
            for path, _ in files[: len(files) - max_files]:
                os.remove(path)
    except Exception:
        pass


def _should_cache(config: dict, df: pd.DataFrame) -> bool:
    code = config.get("code", "")
    is_city = config.get("is_city", False) or (len(code) >= 5 and code[4:6] == "00")
    return not (is_city and len(df) < 20)


class RenderService:
    """无状态渲染服务, 组合 DataService/ShapeService 并提供统一的 render 接口."""

    def __init__(self, shape_service: ShapeService, data_service: DataService):
        self.shape_service = shape_service
        self.data_service = data_service

    @property
    def cache_size(self) -> int:
        try:
            return len([f for f in os.listdir(settings.img_data_path_resolved) if f.endswith(".png")])
        except Exception:
            return 0

    async def render(self, config):
        if config.get("trace_id") is None:
            config["trace_id"] = config.get("id") or ""

        if config.get("id") is not None:
            cache = _cache_get(config.get("id"))
            if cache is not None:
                logging.info("Render cache hit: %s", config.get("id"))
                import io

                return io.BytesIO(cache)

        df = await self._get_data(config)
        df = self._filter_stations(config, df)
        if not config.get("is_has_data") and len(df) > 0:
            config["data"] = df.to_dict(orient="records")
        self.shape_service.get_serialized(config["code"], "_county")

        if config.get("is_city"):
            self.shape_service.get_serialized(config["code"], "")

        if config.get("show_town"):
            self.shape_service.get_serialized(config["code"], "_town")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(_get_process_pool(), self._subprocess_render, config)
        if not result or (isinstance(result, bytes) and len(result) == 0):
            logging.warning("Render returned empty result for id=%s code=%s", config.get("id"), config.get("code"))
            msg = f"Render produced empty result for code={config.get('code')}"
            raise RuntimeError(msg)
        if _should_cache(config, df):
            _cache_set(config.get("id"), result)
        import io

        return io.BytesIO(result)

    async def _get_data(self, config) -> pd.DataFrame:
        if config.get("is_has_data"):
            return pd.DataFrame(config.get("data"))
        try:
            return await self.data_service.get_data(config["code"], config["datestr"], config["type"], config["axis"])
        except Exception as e:
            logging.warning(
                "API data fetch failed [%s/%s/%s/%s], falling back to stations: %s",
                config["code"],
                config["datestr"],
                config["type"],
                config["axis"],
                e,
            )
            return await self.data_service.get_stations(
                config["code"], config["datestr"], config["type"], config["axis"]
            )

    @staticmethod
    def _filter_stations(config, df) -> pd.DataFrame:
        from config import SHOW_MINS

        if len(df) == 0:
            return df

        filter_list = config.get("filter_list")
        if filter_list and len(filter_list) > 0:
            filter_col = "Station_Id_C" if "Station_Id_C" in df.columns else "station_id"
            if filter_col in df.columns:
                df = df[df[filter_col].isin(filter_list)]

        top = config.get("top", 0)
        if top != 0:
            df["val"] = df["val"].astype(float)
            df = df.sort_values(by="val", ascending=config.get("axis") in SHOW_MINS)
            df = df.head(top)
        return df

    @staticmethod
    def _subprocess_render(config):
        from config import SHOW_MINS
        from config.towns import towns
        from rendering.worker import render_in_subprocess

        df = pd.DataFrame(config.get("data"))
        if len(df) == 0:
            records, _, _ = [], [], []
            pos = []
            vals = []
        else:
            rename_map = {}
            if "val" not in df.columns:
                for key in ("V", "v", "VAL", "Val"):
                    if key in df.columns:
                        rename_map[key] = "val"
                        break
            if "lon" not in df.columns:
                for key in ("LON", "Lon"):
                    if key in df.columns:
                        rename_map[key] = "lon"
                        break
            if "lat" not in df.columns:
                for key in ("LAT", "Lat"):
                    if key in df.columns:
                        rename_map[key] = "lat"
                        break
            if "town" not in df.columns:
                for key in ("Town",):
                    if key in df.columns:
                        rename_map[key] = "town"
                        break
            if "name" not in df.columns:
                for key in ("Station_Name",):
                    if key in df.columns:
                        rename_map[key] = "name"
                        break
            if "dir" not in df.columns:
                for key in ("D", "Dir"):
                    if key in df.columns:
                        rename_map[key] = "dir"
                        break
            if rename_map:
                df.rename(columns=rename_map, inplace=True)

            if "Admin_Code_CHN" in df.columns and not config.get("is_city"):
                df = df[df["Admin_Code_CHN"] == config["code"]]

            if len(df) == 0:
                records, _, _ = [], [], []
                pos = []
                vals = []
            else:
                df["val"] = pd.to_numeric(df["val"], errors="coerce")
                df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
                df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
                if "dir" in df.columns:
                    df["dir"] = pd.to_numeric(df["dir"], errors="coerce")
                df = df.dropna(subset=["val", "lon", "lat"])

                if config.get("is_city"):
                    df_all = df.copy()
                    if "Station_Id_C" in df.columns:
                        df = df[df["Station_Id_C"].astype(str).str.startswith("5")]
                    df["lon"] = df["lon"].astype(float)
                    df["lat"] = df["lat"].astype(float)
                    if "name" not in df.columns:
                        df["name"] = ""
                    records = df[["name", "val", "lon", "lat"]].to_dict("records")
                    df_all["lon"] = df_all["lon"].astype(float)
                    df_all["lat"] = df_all["lat"].astype(float)
                    pos = df_all[["lon", "lat"]].to_numpy()
                    vals = df_all["val"].to_numpy().astype("float")
                elif config.get("show_town"):
                    if "town" in df.columns:
                        df = df[df["town"].ne("-")]
                        df = df.dropna(subset=["town", "val", "lon", "lat"])
                    if len(df) == 0:
                        records, _, _ = [], [], []
                        pos = []
                        vals = []
                    else:
                        df_towns = pd.DataFrame(towns)
                        agg_cols = ["town", "val", "lon", "lat"]
                        if "dir" in df.columns and "dir" not in df_towns.columns:
                            agg_cols.append("dir")
                        df_agg = (
                            df[agg_cols].groupby(by=["town"]).min()
                            if config.get("axis") in SHOW_MINS
                            else df[agg_cols].groupby(by=["town"]).max()
                        )
                        df = pd.merge(df_towns, df_agg, on="town", how="right", suffixes=("_town", ""))
                        if config.get("show_real_station"):
                            df["lon"] = df["lon"].fillna(df["lon_town"])
                            df["lat"] = df["lat"].fillna(df["lat_town"])
                        else:
                            df["lon"] = df["lon_town"].fillna(df["lon"])
                            df["lat"] = df["lat_town"].fillna(df["lat"])
                        df = df.drop(columns=["lon_town", "lat_town"], errors="ignore")
                        df["lon"] = df["lon"].astype(float)
                        df["lat"] = df["lat"].astype(float)
                        if "name" in df.columns:
                            records = df[["name", "val", "lon", "lat"]].to_dict("records")
                        else:
                            records = [
                                {"name": row.get("town", ""), "val": row["val"], "lon": row["lon"], "lat": row["lat"]}
                                for _, row in df.iterrows()
                            ]
                        pos = df[["lon", "lat"]].to_numpy()
                        vals = df["val"].to_numpy().astype("float")
                else:
                    df["lon"] = df["lon"].astype(float)
                    df["lat"] = df["lat"].astype(float)
                    if "name" not in df.columns:
                        df["name"] = ""
                    records = df[["name", "val", "lon", "lat"]].to_dict("records")
                    pos = df[["lon", "lat"]].to_numpy()
                    vals = df["val"].to_numpy().astype("float")

        main_shape_data = None
        city_shape_data = None
        town_shape_data = None

        from services.render_service import _sub_process_serialize_shape

        main_shape_data = _sub_process_serialize_shape(config["code"], "_county")
        if main_shape_data is None:
            logging.warning("Shape data missing for code=%s, skipping render", config["code"])
            return b""
        if config.get("is_city"):
            city_shape_data = _sub_process_serialize_shape(config["code"], "")
        if config.get("show_town"):
            town_shape_data = _sub_process_serialize_shape(config["code"], "_town")

        if not main_shape_data.get("bounds"):
            logging.warning("Bounds data missing for code=%s, skipping render", config["code"])
            return b""

        image_stream = render_in_subprocess(
            bounds=main_shape_data.get("bounds") if main_shape_data else [],
            stations=records,
            records_data=main_shape_data,
            pos=pos,
            vals=vals,
            color_types=[config.get("type", ""), config.get("axis", "")],
            is_rain=config.get("type", "") == "rain",
            config=config,
            city_shape_data=city_shape_data,
            town_shape_data=town_shape_data,
        )
        if isinstance(image_stream, str):
            file_path = settings.img_data_path_resolved + "/" + image_stream
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    return f.read()
            return b""
        return image_stream
