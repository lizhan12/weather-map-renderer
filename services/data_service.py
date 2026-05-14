from __future__ import annotations

import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse

import aiohttp
import numpy as np
import pandas as pd

from config import RAIN_PRE, SHOW_MINS
from config.towns import towns
from util.sm4 import sign_encode, sm4_decode
from util.trace_logger import TraceLogger


df_towns = pd.DataFrame(towns)

_EMPTY_VALS = np.array([])
_EMPTY_POS = np.array([]).reshape(0, 2)
_DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)


class DataService:
    """气象数据获取与处理服务, 负责从远程接口获取站点观测数据并进行 SM4 解密和处理."""

    def __init__(self, prefix: str, url_path: str | None = None, key: str | None = None, sign_key: str | None = None):
        """初始化数据服务.

        Args:
            prefix: 数据接口基础 URL
            url_path: URL 路径模板, 默认包含 alias/code/sign/timestamp 占位符
            key: SM4 解密密钥
            sign_key: 接口签名密钥
        """
        self.prefix = prefix
        self.url_path = url_path or "?sort=desc&alias={}&code={}&endTime={}&sign={}&timestamp={}"
        self.key = key
        self.sign_key = sign_key

        parsed = urlparse(self.prefix)
        self._referer = f"{parsed.scheme}://{parsed.netloc}/"
        self._origin = f"{parsed.scheme}://{parsed.netloc}"
        self._session = aiohttp.ClientSession(timeout=_DEFAULT_TIMEOUT)

    def _build_url(self, alias: str, code: str, date_str: str, start_time: str | None = None) -> str:
        """构建带签名的数据请求 URL."""
        sign, timestr = sign_encode(self.key, self.sign_key)
        url = self.prefix + self.url_path.format(alias, code, date_str, sign, timestr)
        if start_time is not None:
            url += "&startTime=" + start_time
        return url

    def _try_sm4_decode(self, res: dict) -> bool:
        """尝试对响应数据执行 SM4 解密, 成功返回 True."""
        if not self.key:
            logging.warning("SM4 key not configured, skipping decryption")
            return False
        try:
            res["DS"] = sm4_decode(self.key, res["DS"])
        except Exception:
            logging.exception("SM4 decode failed")
            return False
        return True

    @staticmethod
    def _is_success(res: dict | None) -> bool:
        """检查接口响应是否成功 (returnCode 为 0 或 200)."""
        if res is None:
            return False
        code = res.get("returnCode")
        try:
            return int(code) in (0, 200)
        except (TypeError, ValueError):
            return False

    async def _fetch_data(self, url: str) -> dict | None:
        """异步获取远程接口数据."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": self._referer,
            "Origin": self._origin,
        }
        try:
            async with self._session.get(url, headers=headers) as res:
                return await res.json()
        except Exception:
            logging.exception("request data failed")
            return None

    async def close(self) -> None:
        """关闭 aiohttp 会话, 释放连接池."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_face_data(
        self,
        axis: str = "SUM_PRE_12H_POINT",
        code: str = "330500",
        date_str: str = "20231105100000",
        start_time: str | None = None,
    ):
        """获取面雨量数据, 根据降雨类型自动计算开始时间."""
        step = RAIN_PRE.get(axis)
        if step is None or step < 0:
            return None
        if start_time is None:
            date = datetime.strptime(date_str, "%Y%m%d%H%M%S") - timedelta(minutes=step)
            start_time = date.strftime("%Y%m%d%H0000")

        url = self._build_url("SUM_FACE_PRE_FREE", code[:4] + "00", date_str, start_time)
        TraceLogger.log("data_fetch")
        res = await self._fetch_data(url)
        if not self._is_success(res):
            return None
        if not self._try_sm4_decode(res):
            return None
        TraceLogger.log("sm4_decode_done")

        arr = []
        for item in res["DS"]:
            if item.get("Admin_Code_CHN") == code[:4] + "00":
                arr.insert(0, {"name": item.get("City") + "平均雨量", "val": item["V"]})
            else:
                arr.append({"name": item.get("Cnty"), "val": item["V"]})
        return arr

    def handle_data(self, data: list, code: str, is_city: bool = False) -> tuple:
        """处理原始站点数据, 提取观测值/坐标/站点信息.

        Args:
            data: 原始站点数据列表
            code: 区划代码, 用于过滤站点
            is_city: 是否为市级请求 (不过滤区划代码)

        Returns:
            (vals, pos, stations) 元组
        """
        if not data:
            return _EMPTY_VALS, _EMPTY_POS.copy(), []

        code_prefix = str(code)[:4]
        vals = []
        pos = []
        stations = []

        for item in data:
            obj = {
                "id": item["Station_Id_C"],
                "name": item["Station_Name"],
                "cnty": item["Cnty"],
                "city": item["City"],
                "code": item["Admin_Code_CHN"],
                "town": item.get("Town"),
                "val": item["V"],
                "lon": item["Lon"],
                "lat": item["Lat"],
            }
            if item.get("D") is not None:
                obj["dir"] = item["D"]
            stations.append(obj)

            admin_code = str(item["Admin_Code_CHN"])
            if is_city or admin_code.startswith(code_prefix) or admin_code == str(code):
                vals.append(float(item["V"]))
                pos.append([float(item["Lon"]), float(item["Lat"])])

        return np.array(vals), np.array(pos), stations

    async def get_data(
        self,
        axis: str = "SUM_PRE_12H_POINT",
        code: str = "330500",
        date_str: str = "20230725100000",
        start_time: str | None = None,
        is_city: bool = False,
    ) -> tuple:
        """获取并处理站点观测数据 (异步): 请求 -> SM4 解密 -> handle_data."""
        url = self._build_url(axis, code, date_str, start_time)
        TraceLogger.log("data_fetch")
        res = await self._fetch_data(url)
        TraceLogger.log("data_fetch_done")

        if not self._is_success(res):
            return _EMPTY_VALS, _EMPTY_POS.copy(), []
        if not self._try_sm4_decode(res):
            return _EMPTY_VALS, _EMPTY_POS.copy(), []
        TraceLogger.log("sm4_decode_done")

        result = self.handle_data(res["DS"], code, is_city)
        TraceLogger.log("data_process", f"stations={len(result[2])}")
        return result

    def top_face(self, stations: list, is_rain: bool = True, config: dict | None = None) -> tuple:
        """计算站点排名和面雨量统计.

        Args:
            stations: 站点数据列表
            is_rain: 是否为降雨类型 (True 时不计算面雨量)
            config: 渲染配置, 包含 top/is_city/code/axis 等键

        Returns:
            (head, face_data) 元组
        """
        df = pd.DataFrame(stations)
        df["val"] = df["val"].astype(float)
        is_ascending = bool(config and config.get("axis") in SHOW_MINS)

        top_df = df
        if config and config.get("is_city") is False:
            top_df = df[df["code"] == config["code"]]
        top_df = top_df.sort_values(by="val", ascending=is_ascending)
        head = top_df.head(config.get("top", 5) if config else 5)

        group = "cnty"
        if int(config.get("code", "000000")[2:]) == 0:
            group = "city"

        if is_rain:
            return list(head.to_dict(orient="index").values()), None

        rain_mean = df.groupby(group)["val"].mean().reset_index().round(1)
        city_mean = df.groupby("city")["val"].mean().reset_index().round(1)
        rain_mean.sort_values("val", ascending=False, inplace=True)
        rain_mean["name"] = rain_mean[group]
        city_mean["name"] = city_mean["city"] + "平均雨量"

        return (
            list(head.to_dict(orient="index").values()),
            list(city_mean.to_dict(orient="index").values()) + list(rain_mean.to_dict(orient="index").values()),
        )

    def filter_stations(self, stations: list, config: dict | None = None) -> tuple:
        """根据配置过滤站点数据: 隐藏零值 -> 按区划过滤 -> 按乡镇聚合 -> 过滤国家站.

        Args:
            stations: 站点数据列表
            config: 渲染配置, 包含 type/hide_rain_zero/is_city/show_town 等键

        Returns:
            (filtered_stations, show_empty) 元组
        """
        show_empty = False
        if len(stations) == 0:
            return [], show_empty

        df = pd.DataFrame(stations)
        data_type = config.get("type", config.get("data_type", "")) if config else ""

        if data_type in ["rain", "snow"]:
            df["num"] = df["val"].astype(float)
            tmp = df[df["num"] > 0.0]
            if len(tmp) <= 0:
                show_empty = True
            if config and config.get("hide_rain_zero"):
                df = tmp

        if config and config.get("show_all"):
            return stations, show_empty

        filter_list = config.get("filter_list") if config else None
        if filter_list is not None and len(filter_list) > 0:
            arr = [s for s in stations if s["id"] in filter_list]
            if config and config.get("is_city"):
                return arr, show_empty
            return [s for s in arr if s["code"] == config.get("code")], show_empty

        if not config or not config.get("is_city"):
            df = df[df["code"].str.contains(config["code"])]

        if config and config.get("show_town") and not config.get("is_city"):
            df = df.groupby(by=["town"]).min() if config.get("axis") in SHOW_MINS else df.groupby(by=["town"]).max()
            df = pd.merge(df_towns, df, on="town", how="inner")
            if config.get("show_real_station"):
                df.rename(columns={"lon_y": "lon", "lat_y": "lat"}, inplace=True)
            else:
                df.rename(columns={"lon_x": "lon", "lat_x": "lat"}, inplace=True)
            return list(df.to_dict(orient="index").values()), show_empty

        df = df.query('id.str.startswith("5")')
        return list(df.to_dict(orient="index").values()), show_empty
