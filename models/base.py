from pydantic import BaseModel, Field


class ItemNc(BaseModel):
    data: list = Field([], description="上传的nc数据")
    el: str = Field("T", description="数据类型")
    pre: str = Field("Ruler", description="文件前缀")
    timestr: str = Field("20200107010000", description="日期字符串")
    mid: str = Field(default="000", description="中间字符串")

    @property
    def filename(self):
        """生成 NC 文件名, 格式: {pre}.{timestr}.{mid}.{el}.nc."""
        return f"{self.pre}.{self.timestr}.{self.mid}.{self.el}.nc"


class ItemImg(BaseModel):
    show_wind: bool = Field(False, description="是否显示风向杆 默认:false")
    show_name: bool | None = Field(None, description="是否显示站点名称 默认:城市级显示,区县级不显示")
    show_value: bool = Field(True, description="是否显示站点数值 默认:true")
    show_face: bool = Field(False, description="是否显示面雨量 默认:false")
    hide_rain_zero: bool = Field(False, description="是否隐藏零值降水站点 默认:false")
    show_no_rain_logo: bool = Field(False, description="是否显示无降水logo 默认:false")
    show_border: bool = Field(False, description="是否显示边框 默认:false")
    show_contourf: bool = Field(True, description="是否显示填色图 默认:true")
    show_point: bool = Field(True, description="是否显示站点圆点 默认:true")
    show_unit: bool = Field(True, description="色标是否显示单位 默认:true")
    show_real_station: bool = Field(True, description="是否显示站点实际位置(否则显示乡镇位置) 默认:true")
    is_clip: bool = Field(True, description="是否裁剪图片至行政区边界 默认:true")
    is_inner: bool = Field(True, description="色标是否显示在边框内(仅show_border=true时有效) 默认:true")
    show_town: bool = Field(True, description="是否显示乡镇边界 默认:true")
    show_town_name: bool = Field(True, description="是否显示乡镇名称(需show_town=true) 默认:true")
    show_mesh: bool = Field(True, description="是否显示经纬度网格 默认:true")
    arrow: bool = Field(False, description="是否显示箭头 默认:false")
    fix: bool = Field(True, description="是否固定图片尺寸 默认:true")
    color: str = Field(
        "0",
        description="自定义色标 格式:#fff,1,#000,100(颜色,值交替) 传'1'自动色标 传-999999~999999只显示对应色标范围",
    )
    title: str | None = Field(None, description="图片标题 默认:不显示")
    unit: str | None = Field(None, description="单位标题 '0'不显示 不传显示默认 其他显示传入值")
    label_location: str = Field("", description="单位标题位置")
    datestr: str | None = Field(None, description="结束时间(世界时) 格式yyyyMMddHHmmss eg:20230727110000")
    start_time: str | None = Field(None, description="起始时间(世界时) 格式yyyyMMddHHmmss eg:20230727110000")
    location: str = Field("bottom", description="色标位置: bottom(下方)/right(右侧)/top(上方)/left(左侧)")
    wind_location: str = Field("0,0,0.28,0.25", description="风向杆区域位置 格式:左,下,宽,高(百分比0~1)")
    top_location: str | None = Field(None, description="排行榜位置 格式:左,下,宽,高(百分比0~1)")
    face_location: str | None = Field(None, description="面雨量区域位置 格式:左,下,宽,高(百分比0~1)")
    publisher_location: str | None = Field(
        "0.7,0.0,0.3,0.15", description="发布单位区域位置 格式:左,下,宽,高(百分比0~1)"
    )
    mesh_padding: str | None = Field(
        "0.0, 0.0, 0.0, 0.0", description="地图内边距(经纬度单位) 格式:上,右,下,左 eg:0.1,0.1,0.1,0.1"
    )
    is_has_data: bool | None = Field(True, description="是否已携带数据(内部字段,无需传递)")
    data: list = Field([], description="站点数据列表 字段:Station_Name/Station_Id_C/Lon/Lat/V")
    subconfig: dict = Field({}, description="乡镇级配置 字段示例:{'330681201':{'bounds':'0.01,0.015,0.01,0.1'}}")
    width: int | None = Field(None, description="图片宽度(像素) 默认:配置文件值")
    axis: str = Field("", description="数据别名 eg:TEM_H_POINT")
    publisher: str = Field("", description="发布单位文字")
    height: int | None = Field(None, description="图片高度(像素) 默认:配置文件值")
    filter_list: str | None = Field(None, description="过滤显示的站点ID列表 逗号分隔 eg:K8785,587458")
    wind_fontsize: int | None = Field(20, description="风向杆字体大小(磅)")
    wind_color: str | None = Field("#fff", description="风向杆颜色 eg:#fff/blue")
    point_color: str | None = Field("#666", description="站点圆点颜色 eg:#666")
    txt_fontcolor: str | None = Field("#666", description="站点名称字体颜色 eg:#666")
    val_fontcolor: str | None = Field("#666", description="站点数值字体颜色 eg:#666")
    top: int = Field(0, description="取排名前N个站点 0表示不限制")
    bar_aspect: int = Field(20, description="色标长宽比")
    bar_width: float | None = Field(None, description="色标高度占比(0~1)")
    bar_pad: float | None = Field(None, description="色标距离边框的距离(像素)")
    bar_fontsize: int = Field(14, description="色标字体大小(磅)")
    offset_lat: float = Field(15.0, description="纬度偏移量(度)")
    bar_txtcolor: str = Field("#666", description="色标字体颜色 eg:#666")
    area_txtcolor: str = Field("#999", description="区域名称字体颜色 eg:#999")
    title_fontsize: int = Field(16, description="标题字体大小(磅)")
    txt_fontsize: int = Field(14, description="站点名称字体大小(磅)")
    val_fontsize: int = Field(14, description="站点数值字体大小(磅)")
    town_fontsize: int = Field(12, description="乡镇名称字体大小(磅)")
    title_pad: int = Field(15, description="标题距离图片的间距(像素)")
    bar_margin: int = Field(95, description="色标距离图片的间距(像素)")
    gen_all: bool = Field(False, description="是否生成所有下级行政区图片 默认:false")
    interpolation_method: str = Field(
        "rbf", description="插值方式: rbf(径向基函数,默认)/idw(反距离加权)/cressman(Cressman客观分析)"
    )
    bounds_lines: str | None = Field(
        None, description="边界线宽度(磅) 格式:主边界,区县边界,乡镇边界 eg:2,1.5,0.7 必须3个数"
    )
    bounds_colors: str | None = Field(
        None, description="边界线颜色 格式:主边界,区县边界,乡镇边界 eg:#333,#333,#666 必须3个数"
    )
