from __future__ import annotations

import logging
import threading

import cartopy.io.shapereader as shpreader

from util.trace_logger import TraceLogger


_SIMPLIFY_TOLERANCE = 0.01


class ShapeService:
    """Shapefile 读取与缓存服务, 提供区划边界/几何/属性的序列化数据."""

    def __init__(self, shape_dir: str, areas: dict):
        """初始化 shapefile 服务.

        Args:
            shape_dir: shapefile 目录路径
            areas: 区划代码-名称映射字典
        """
        self._shape_dir = shape_dir
        self._areas = areas
        self._cache: dict[str, object] = {}
        self._serialized_cache: dict[str, dict | None] = {}
        self._serialize_lock = threading.Lock()

    def _get_county_code(self, record) -> str:
        """从 shapefile 记录中提取区划代码 (adcode 或 ddgl_code)."""
        code = record.attributes.get("adcode") or record.attributes.get("ddgl_code")
        return str(code)[:6] if code else ""

    def get_shape(self, code: str, tail: str = "_county") -> tuple:
        """根据区划代码获取 shapefile 记录/边界/几何.

        Args:
            code: 区划代码 (6位)
            tail: shapefile 后缀, 可选 "_county"/"_town"/""

        Returns:
            (records, bounds, geometries) 元组, 失败返回 (None, None, None)
        """
        is_city = int(code[4:]) == 0
        city_code = code[:4] + "00"
        cache_key = city_code + "000" + tail

        gdf = self._cache.get(cache_key)
        if not gdf:
            gdf = self._read_shape("/" + cache_key)
            if gdf:
                self._cache[cache_key] = gdf

        if gdf is None:
            return None, None, None

        if is_city:
            records = list(gdf.records())
            return records, self.get_bounds(records), list(gdf.geometries())

        if tail.endswith("town"):
            records = [r for r in gdf.records() if self._get_county_code(r) == str(code)]
            if records:
                return records, [r.bounds for r in records], [r.geometry for r in records]
        else:
            for record in gdf.records():
                if self._get_county_code(record) == str(code):
                    return [record], record.bounds, [record.geometry]

        gdf = self._read_shape("/" + str(code).ljust(9, "0"))
        if gdf:
            records = list(gdf.records())
            return records, self.get_bounds(records), list(gdf.geometries())
        return None, None, None

    def get_serialized(self, code: str, tail: str) -> dict | None:
        """获取序列化的 shapefile 数据 (带双重检查锁定缓存).

        Args:
            code: 区划代码
            tail: shapefile 后缀

        Returns:
            序列化字典 {"attrs": [...], "geoms": [...], "bounds": ...}, 失败返回 None
        """
        TraceLogger.log("shape_load", f"code={code} tail={tail}")
        cache_key = f"{code}_{tail}"
        if cache_key in self._serialized_cache:
            return self._serialized_cache[cache_key]

        with self._serialize_lock:
            if cache_key in self._serialized_cache:
                return self._serialized_cache[cache_key]

            records, bounds, geometries = self.get_shape(code, tail)
            if records is None:
                self._serialized_cache[cache_key] = None
                return None

            result = self._serialize(records, geometries, bounds)
            self._serialized_cache[cache_key] = result
            return result

    def _read_shape(self, file_name: str):
        """读取 shapefile 文件.

        Args:
            file_name: 相对于 shape_dir 的文件路径

        Returns:
            cartopy Reader 对象, 读取失败返回 None
        """
        try:
            return shpreader.Reader(self._shape_dir + file_name)
        except Exception:
            logging.exception("read shape file failed [%s]", file_name)
            return None

    @staticmethod
    def get_bounds(records) -> tuple:
        """从 shapefile 记录中计算总边界范围.

        Args:
            records: shapefile 记录迭代器

        Returns:
            (min_lon, min_lat, max_lon, max_lat) 边界元组
        """
        min_lon = min_lat = float("inf")
        max_lon = max_lat = float("-inf")
        for r in records:
            b = r.bounds
            min_lon, max_lon = min(min_lon, b[0]), max(max_lon, b[2])
            min_lat, max_lat = min(min_lat, b[1]), max(max_lat, b[3])
        return min_lon, min_lat, max_lon, max_lat

    @staticmethod
    def _serialize(records, geometries, bounds) -> dict:
        """将 shapefile 数据序列化为可跨进程传递的字典.

        Args:
            records: shapefile 记录列表
            geometries: 几何图形列表
            bounds: 边界数据

        Returns:
            {"attrs": [属性字典...], "geoms": [GeoJSON几何...], "bounds": 边界}
        """
        attrs_list = []
        geoms = []
        for i, record in enumerate(records):
            try:
                attrs_list.append(dict(record.attributes))
            except Exception:
                logging.debug("serialize shape attrs failed for index %s", i)
                attrs_list.append({})
            try:
                geom = record.geometry if hasattr(record, "geometry") else geometries[i] if geometries else None
                if geom is not None:
                    simplified = geom.simplify(_SIMPLIFY_TOLERANCE, preserve_topology=True)
                    geoms.append({
                        "type": simplified.geom_type,
                        "coordinates": simplified.__geo_interface__["coordinates"],
                    })
                else:
                    geoms.append(None)
            except Exception:
                logging.debug("serialize shape geometry failed for index %s", i)
                geoms.append(None)
        return {"attrs": attrs_list, "geoms": geoms, "bounds": bounds}
