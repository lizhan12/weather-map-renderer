from __future__ import annotations

from datetime import datetime
from typing import Any

import aiohttp
import pandas as pd

from config import SHOW_MINS
from util.sm4 import sign_encode, sm4_decode


class DataService:
    """无状态数据获取服务, 复用 aiohttp ClientSession 连接池."""

    _DATE_PLACEHOLDER = "GETDATEB0YCODE"

    def __init__(self, prefix: str, key: str = "", sign_key: str = "", referer: str = "", user_agent: str = "", timeout: int = 30):
        self.prefix = prefix
        self.key = key
        self.sign_key = sign_key
        self._referer = referer
        self._user_agent = user_agent
        self._timeout = timeout
        self._session: aiohttp.ClientSession | None = None

    def _resolve_url(self) -> str:
        return self.prefix

    def _add_sign_params(self, params: dict) -> dict:
        """添加签名和时间戳参数, 签名算法: md5(key + secret + timestamp)."""
        if self.key:
            sign, timestamp = sign_encode(self.key, self.sign_key)
            params["sign"] = sign
            params["timestamp"] = timestamp
        return params

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers: dict[str, str] = {}
            if self._user_agent:
                headers["User-Agent"] = self._user_agent
            if self._referer:
                headers["Referer"] = self._referer
            timeout = aiohttp.ClientTimeout(total=self._timeout, connect=10, sock_read=max(self._timeout - 10, 10))
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers or None)
        return self._session

    async def close(self):
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None

    def _extract_data(self, json: dict) -> pd.DataFrame:
        ds = json.get("DS")
        if isinstance(ds, str) and ds:
            decrypted = sm4_decode(self.key, ds)
            if isinstance(decrypted, list):
                return pd.DataFrame(decrypted)
            if isinstance(decrypted, dict):
                inner = decrypted.get("data")
                if isinstance(inner, list):
                    return pd.DataFrame(inner)
        data = json.get("data")
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return pd.DataFrame(data["data"])
        if isinstance(data, list):
            return pd.DataFrame(data)
        return pd.DataFrame([])

    async def get_data(self, code: str, datestr: str, data_type: str, axis: str) -> pd.DataFrame:
        params = {"sort": "desc", "alias": axis, "code": code, "endTime": datestr}
        params = self._add_sign_params(params)
        session = await self._get_session()
        url = self._resolve_url()
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            json = await response.json()
        if json.get("returnCode") == "0":
            return self._extract_data(json)
        return pd.DataFrame([])

    async def get_stations(self, code: str, datestr: str, data_type: str, axis: str) -> pd.DataFrame:
        params = {"sort": "desc", "alias": axis, "code": code, "endTime": datestr}
        params = self._add_sign_params(params)
        session = await self._get_session()
        url = self._resolve_url()
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            json = await response.json()
        if json.get("returnCode") == "0":
            return self._extract_data(json)
        return pd.DataFrame([])

    async def get_els_data(self, code: str, datestr: str, axis: str) -> pd.DataFrame:
        params = {"sort": "desc", "alias": axis, "code": code, "endTime": datestr}
        params = self._add_sign_params(params)
        session = await self._get_session()
        url = self._resolve_url()
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            json = await response.json()
        if json.get("returnCode") == "0":
            return self._extract_data(json)
        return pd.DataFrame([])

    async def get_els_area_data(self, code: str, datestr: str, data_type: str, axis: str) -> pd.DataFrame:
        params = {"sort": "desc", "alias": axis, "code": code, "endTime": datestr}
        params = self._add_sign_params(params)
        session = await self._get_session()
        url = self._resolve_url()
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            json = await response.json()
        if json.get("returnCode") == "0":
            return self._extract_data(json)
        return pd.DataFrame([])

    async def get_rain_data(self, code: str, datestr: str) -> pd.DataFrame:
        params = {"sort": "desc", "alias": "RAIN_H_POINT", "code": code, "endTime": datestr}
        params = self._add_sign_params(params)
        session = await self._get_session()
        url = self._resolve_url()
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            json = await response.json()
        if json.get("returnCode") == "0":
            return self._extract_data(json)
        return pd.DataFrame([])

    async def handle_data(self, config: dict) -> list[dict[str, Any]]:
        """处理数据, 返回格式化后的站点列表."""
        df = pd.DataFrame([])
        data_type = config.get("type", "")
        if data_type == "rain":
            if not config.get("is_has_data"):
                if config.get("show_face"):
                    df = await self.get_els_area_data(config["code"], config["datestr"], config["type"], config["axis"])
                elif config.get("show_border"):
                    df = await self.get_rain_data(config["code"], config["datestr"])
                else:
                    df = await self.get_els_data(config["code"], config["datestr"], config["axis"])
            if config.get("show_name") is None:
                config["show_name"] = False
        elif data_type == "wind":
            if not config.get("is_has_data"):
                df = await self.get_els_data(config["code"], config["datestr"], config["axis"])
        elif data_type == "tem":
            if not config.get("is_has_data"):
                df = await self.get_data(config["code"], config["datestr"], config["type"], config["axis"])
        elif not config.get("is_has_data"):
            df = await self.get_els_data(config["code"], config["datestr"], config["axis"])

        if len(df) > 0 and not config.get("is_has_data"):
            df.rename(
                columns={
                    "V": "val", "v": "val", "VAL": "val", "Val": "val",
                    "LON": "lon", "Lon": "lon",
                    "LAT": "lat", "Lat": "lat",
                    "Town": "town",
                    "Station_Name": "name",
                    "D": "dir", "Dir": "dir",
                },
                inplace=True,
            )

        if (
            len(df) > 0
            and config.get("hide_rain_zero")
            and not config.get("show_face")
            and not config.get("show_border")
            and len(df[df["val"] != 0.0]) == 0
        ):
            config["show_name"] = False
            df = df.drop(df[df["val"] == 0.0].index)

        if config.get("is_has_data"):
            stations = config.get("data", [])
            stations = _normalize_stations(stations)
        else:
            stations = []
            for _, item in df.iterrows():
                item["Datetime"] = str(datetime.now()).replace(" ", "T")[0:19]
                stations.append(item.to_dict())

        result, _ = _filter_stations(config, stations)
        return result


def _normalize_stations(stations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """标准化站点数据字段名称, 统一不同大小写变体为小写.

    Args:
        stations: 原始站点数据列表

    Returns:
        标准化后的数据列表
    """
    for station in stations:
        if "val" not in station:
            for key in ("V", "v", "VAL", "Val"):
                if key in station:
                    station["val"] = station.pop(key)
                    break
        if "lon" not in station:
            for key in ("LON", "Lon"):
                if key in station:
                    station["lon"] = station.pop(key)
                    break
        if "lat" not in station:
            for key in ("LAT", "Lat"):
                if key in station:
                    station["lat"] = station.pop(key)
                    break
        if "dir" not in station:
            for key in ("D", "Dir"):
                if key in station:
                    station["dir"] = station.pop(key)
                    break
        if "town" not in station:
            for key in ("Town",):
                if key in station:
                    station["town"] = station.pop(key)
                    break
        if "name" not in station:
            for key in ("Station_Name",):
                if key in station:
                    station["name"] = station.pop(key)
                    break
        if "Station_Id_C" not in station:
            for key in ("station_id", "Station_Id_C"):
                if key in station:
                    station["Station_Id_C"] = station.pop(key)
                    break
    return stations


def _filter_stations(config: dict, stations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    from config.towns import towns

    if len(stations) == 0:
        return stations, False

    filter_list = config.get("filter_list")
    if filter_list is not None and len(filter_list) > 0:
        stations = [x for x in stations if x.get("Station_Id_C") in filter_list]

    if config.get("top", 0) != 0:
        try:
            df = pd.DataFrame(stations)
            df["val"] = df["val"].astype(float)
            df = df.sort_values(by="val", ascending=config.get("axis") in SHOW_MINS)
            return df.head(config.get("top")).to_dict(orient="records"), False
        except (ValueError, KeyError):
            pass

    if config.get("is_city"):
        stations = [s for s in stations if str(s.get("Station_Id_C", "")).startswith("5")]
        return stations, False

    if config.get("show_town"):
        df = pd.DataFrame(stations)
        df["val"] = pd.to_numeric(df["val"], errors="coerce")
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        if "dir" in df.columns:
            df["dir"] = pd.to_numeric(df["dir"], errors="coerce")
        df = df.dropna(subset=["town"])
        if len(df) == 0:
            return [], False
        agg_cols = ["town", "val", "lon", "lat"]
        if "dir" in df.columns:
            agg_cols.append("dir")
        df_towns = pd.DataFrame(towns)
        if config.get("axis") in SHOW_MINS:
            df_agg = df[agg_cols].groupby(by=["town"]).min()
        else:
            df_agg = df[agg_cols].groupby(by=["town"]).max()
        df = pd.merge(df_towns, df_agg, on="town", how="right", suffixes=("_town", ""))
        if config.get("show_real_station"):
            df["lon"] = df["lon"].fillna(df["lon_town"])
            df["lat"] = df["lat"].fillna(df["lat_town"])
        else:
            df["lon"] = df["lon_town"].fillna(df["lon"])
            df["lat"] = df["lat_town"].fillna(df["lat"])
        df = df.drop(columns=["lon_town", "lat_town"], errors="ignore")
        return df.to_dict(orient="records"), False

    return stations, False
