from __future__ import annotations

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


MARGIN_OBJ = {
    "bottom": (10, 10, 10, 10),
    "top": (10, 10, 10, 10),
    "left": (10, 10, 10, 10),
    "right": (10, 10, 10, 10),
}

UNITS = {
    "vis": "能见度(m)",
    "rain": "降雨(毫米)",
    "tem": "温度(℃)",
    "wind": "风速(m/s)",
    "rh": "湿度(%)",
}


class Settings(BaseSettings):
    """应用全局配置, 从环境变量 (PYDRAW_ 前缀) 或 .env 文件加载."""

    base_path: str = "/home/tu"

    width: int = 700
    height: int = 700
    cache_ttl: int = 300
    cache_max_files: int = 500
    render_workers: int = 0
    render_max_workers: int = 4

    shape_path: str = ""
    img_path: str = ""
    log_path: str = ""
    temp_path: str = ""
    img_data_path: str = ""

    data_service_url: str = ""
    data_service_key: str = ""
    data_service_sign_key: str = ""

    model_config = SettingsConfigDict(env_prefix="PYDRAW_", env_file=".env", extra="ignore")

    @computed_field
    @property
    def shape_path_resolved(self) -> str:
        """Shapefile 目录路径, 未配置时默认 {base_path}/zjaws."""
        return self.shape_path or f"{self.base_path}/zjaws"

    @computed_field
    @property
    def img_path_resolved(self) -> str:
        """图片输出目录路径, 未配置时默认 {base_path}/pic."""
        return self.img_path or f"{self.base_path}/pic"

    @computed_field
    @property
    def log_path_resolved(self) -> str:
        """日志目录路径, 未配置时默认 {base_path}/log."""
        return self.log_path or f"{self.base_path}/log"

    @computed_field
    @property
    def temp_path_resolved(self) -> str:
        """临时文件目录路径, 未配置时默认 {base_path}/temp."""
        return self.temp_path or f"{self.base_path}/temp"

    @computed_field
    @property
    def img_data_path_resolved(self) -> str:
        """数据图片目录路径, 位于 img_path 下的 imgs 子目录."""
        return self.img_path_resolved + "/imgs"

    @computed_field
    @property
    def save_img_path_template(self) -> str:
        """保存图片路径模板, {} 占位符替换为文件名."""
        return self.img_data_path_resolved + "/{}.png"


settings = Settings()
