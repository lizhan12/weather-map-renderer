import logging
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, staticfiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html

from api import img_v2
from config import AREAS, settings
from config.area_config import AREAS as AREA_CODES
from services.shape_service import ShapeService
from util.file_dir_io import mk_dir
from util.trace_logger import TraceLogger


_shape_service = ShapeService(
    shape_dir=settings.shape_path_resolved,
    areas=AREAS,
)


def init():
    area_codes = [item for item in AREA_CODES if int(item[4:]) == 0]
    for code in area_codes:
        _shape_service.get_serialized(code, "_county")
        _shape_service.get_serialized(code, "_town")
        _shape_service.get_serialized(code, "")

    _warmup_matplotlib()


def _warmup_matplotlib():
    import matplotlib

    matplotlib.use("agg")
    import matplotlib.font_manager as fm

    from rendering.paths import SIMHEI_FONT

    fm.fontManager.addfont(SIMHEI_FONT)
    matplotlib.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False

    from io import BytesIO

    import cartopy.crs as ccrs
    from matplotlib.figure import Figure

    fig = Figure(figsize=[1, 1], dpi=80)
    ax = fig.add_subplot(projection=ccrs.Mercator())
    ax.set_title("预热")
    buf = BytesIO()
    fig.savefig(buf, format="png")
    fig.clear()
    logging.info("matplotlib font warmup completed")


def create_app(config_name):
    mk_dir(settings.log_path_resolved)
    mk_dir(settings.img_path_resolved)
    mk_dir(settings.img_data_path_resolved)
    mk_dir(settings.temp_path_resolved)

    TraceLogger.init(settings.log_path_resolved)

    logging.basicConfig(level=logging.INFO)
    handler = RotatingFileHandler(settings.log_path_resolved + "/app.log", maxBytes=1000000, backupCount=10)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s-%(funcName)s")
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)

    app = FastAPI(docs_url=None, redoc_url=None, version="1.3.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(img_v2.router, prefix="/api")
    app.mount("/static", staticfiles.StaticFiles(directory="static"), name="static")

    @app.on_event("startup")
    def startup_event():
        init()

    @app.on_event("shutdown")
    async def shutdown_event():
        await TraceLogger.shutdown()

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="/static/js/swagger-ui-bundle.js",
            swagger_css_url="/static/css/swagger-ui.css",
            swagger_favicon_url="/static/favicon.png",
        )

    @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()

    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=app.title + " - ReDoc",
            redoc_js_url="/static/js/redoc.standalone.js",
        )

    return app
