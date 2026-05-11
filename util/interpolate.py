from __future__ import annotations

import numpy as np
from scipy.interpolate import Rbf


class Interpolator:
    """气象站点数据网格化插值器, 支持多种插值方法."""

    def get_mesh(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> tuple[np.ndarray, np.ndarray]:
        """根据经纬度范围生成等间距网格坐标.

        小范围 (跨度 < 0.1) 使用 0.0005 步长, 大范围使用 0.02 步长.

        Args:
            min_lon: 最小经度
            min_lat: 最小纬度
            max_lon: 最大经度
            max_lat: 最大纬度

        Returns:
            (lon_grid, lat_grid) 网格坐标数组
        """
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon
        latstep = 0.0005 if lat_range < 0.1 else 0.02
        lonstep = 0.0005 if lon_range < 0.1 else 0.02
        lonstep = round((max_lon - min_lon) / lonstep)
        latstep = round((max_lat - min_lat) / latstep)
        return np.meshgrid(
            np.linspace(min_lon, max_lon, lonstep),
            np.linspace(min_lat, max_lat, latstep),
        )

    def interpolate_grid(
        self, lons: np.ndarray, lats: np.ndarray, vals: np.ndarray, mesh: tuple[np.ndarray, np.ndarray], method: str = "rbf",
    ) -> np.ndarray:
        """将站点观测值插值到网格上.

        站点数 < 3 时返回均值填充的网格.

        Args:
            lons: 站点经度数组
            lats: 站点纬度数组
            vals: 站点观测值数组
            mesh: 目标网格 (lon_grid, lat_grid)
            method: 插值方法, 可选 "rbf"(默认)/"idw"/"cressman"

        Returns:
            网格化后的二维数组
        """
        if len(vals) < 3:
            return np.full(mesh[0].shape, np.mean(vals) if len(vals) > 0 else 0.0)

        if method == "idw":
            return self._interpolate_idw(lons, lats, vals, mesh)
        elif method == "cressman":
            return self._interpolate_cressman(lons, lats, vals, mesh)
        else:
            return self._interpolate_rbf(lons, lats, vals, mesh)

    @staticmethod
    def _interpolate_rbf(lons: np.ndarray, lats: np.ndarray, vals: np.ndarray, mesh: tuple[np.ndarray, np.ndarray]) -> np.ndarray:
        """RBF (径向基函数) 插值, 使用 linear 核函数.

        Args:
            lons: 站点经度数组
            lats: 站点纬度数组
            vals: 站点观测值数组
            mesh: 目标网格

        Returns:
            插值结果二维数组
        """
        rbf = Rbf(lons, lats, vals, function="linear", smooth=0.0004, epsilon=0.0)
        return rbf(mesh[0], mesh[1])

    @staticmethod
    def _interpolate_idw(lons: np.ndarray, lats: np.ndarray, vals: np.ndarray, mesh: tuple[np.ndarray, np.ndarray], power: float = 2.0) -> np.ndarray:
        """IDW (反距离加权) 插值, 取最近 k=10 个站点加权.

        Args:
            lons: 站点经度数组
            lats: 站点纬度数组
            vals: 站点观测值数组
            mesh: 目标网格
            power: 距离权重指数, 默认 2.0

        Returns:
            插值结果二维数组
        """
        from scipy.spatial import cKDTree

        tree = cKDTree(np.column_stack([lons, lats]))
        grid = np.column_stack([mesh[0].ravel(), mesh[1].ravel()])
        k = min(10, len(lons))
        distances, indices = tree.query(grid, k=k)
        distances = np.where(distances < 1e-10, 1e-10, distances)
        weights = 1.0 / (distances**power)
        weighted_vals = vals[indices] * weights
        return (np.sum(weighted_vals, axis=1) / np.sum(weights, axis=1)).reshape(mesh[0].shape)

    @staticmethod
    def _interpolate_cressman(lons: np.ndarray, lats: np.ndarray, vals: np.ndarray, mesh: tuple[np.ndarray, np.ndarray], radius: float = 0.1, iterations: int = 3) -> np.ndarray:
        """Cressman 插值, 基于影响半径的逐步逼近方法.

        Args:
            lons: 站点经度数组
            lats: 站点纬度数组
            vals: 站点观测值数组
            mesh: 目标网格
            radius: 影响半径 (经纬度单位), 默认 0.1
            iterations: 迭代次数, 默认 3

        Returns:
            插值结果二维数组
        """
        grid = np.column_stack([mesh[0].ravel(), mesh[1].ravel()])
        sp = np.column_stack([lons, lats])
        r2 = radius * radius

        result = np.zeros(len(grid))
        for _ in range(iterations):
            for i, gp in enumerate(grid):
                d2 = np.sum((sp - gp) ** 2, axis=1)
                w = np.where(d2 < r2, (r2 - d2) / (r2 + d2), 0.0)
                ws = np.sum(w)
                if ws > 0:
                    result[i] = np.sum(vals * w) / ws

        return result.reshape(mesh[0].shape)
