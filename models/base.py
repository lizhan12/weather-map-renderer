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
    show_wind: bool = Field(False, description="显示方向杆 eg:默认不显示风向杆，true false")
    show_name: bool | None = Field(None, description="显示站点名称 eg:默认城市显示，区县不显示，true，false")
    show_value: bool = Field(True, description="显示站点数值 eg:默认显示数值，false")
    show_face: bool = Field(False, description="是否显示面雨量eg:默认不显示，true，false")
    hide_rain_zero: bool = Field(False, description="是否显示零值eg:默认不显示，true，false")
    show_no_rain_logo: bool = Field(False, description="是否显示无降水logo:默认不显示，true，false")
    show_border: bool = Field(False, description="是否显示边框eg:默认不显示，true，false")
    show_contourf: bool = Field(True, description="是否显示填色图eg:默认显示，true，false")
    show_point: bool = Field(True, description="是否显示圆点默认,显示，true，false")
    show_unit: bool = Field(True, description="是否色标显示单位,显示，true，false")
    show_real_station: bool = Field(True, description="显示站点实际位置信息,true为实际位置，false为乡镇位置")
    is_clip: bool = Field(True, description="是否进行裁剪 eg:默认不裁剪")
    is_inner: bool = (Field(True, description="色标是否显示在边框内，只有在show_border为True有效"),)
    show_town: bool = Field(True, description="是否显示乡镇边界")
    show_town_name: bool = Field(True, description="是否显示乡镇名称，必须在show_town是true的情况下生效")
    show_mesh: bool = Field(True, description="是否显示经纬度")
    arrow: bool = Field(False, description="是否显示箭头")
    fix: bool = Field(True, description="是否固定尺寸")
    color: str = Field(
        "0",
        description="颜色设置 eg:为1,自动色标，自定义色标开始与结束传入-999999与999999,只显示对应色标，不显示对应的数值，自定义色标 #fff,1,#000,100",
    )
    title: str | None = Field(None, description="标题设置，默认不展示")
    unit: str | None = Field(None, description="单位标题 '0':不显示，不传：显示默认，其他：显示传入数据类型")
    label_location: str = Field("", description="单位标题位置")
    datestr: str | None = Field(None, description="结束时间世界时,eg:20230727110000")
    start_time: str | None = Field(None, description="起始时间世界时,eg:20230727110000")
    location: str = Field("bottom", description="色标的方向 eg:bottom right")
    wind_location: str = Field("0,0,0.28,0.25", description="风速 eg:0,0,0.28,0.25 左/下/宽/高,百分比")
    top_location: str | None = Field(None, description="排行位置 eg:0,0,0.28,0.25 左/下/宽/高,百分比")
    face_location: str | None = Field(None, description="面雨量位置 eg:0,0,0.28,0.25 左/下/宽/高,百分比")
    publisher_location: str | None = Field(
        "0.7,0.0,0.3,0.15", description="发布单位位置 eg:0,0,0.28,0.25 左/下/宽/高,百分比"
    )
    mesh_padding: str | None = Field(
        "0.0, 0.0, 0.0, 0.0", description="距离边框的内边界，步长单位经纬度,eg:0.1,0.1,0.1,0.1 上/右/下/左"
    )
    is_has_data: bool | None = Field(True, description="默认字段，不需要传递")
    data: list = Field([], description="数据字段,el:{'Station_Name', 'Station_Id_C', 'Lon', 'Lat','V'}")
    subconfig: dict = Field({}, description="乡镇配置,el:{'330681201':{'bounds':'0.01,0.015,0.01,0.1'}}")
    width: int | None = Field(None, description="图片的宽度")
    axis: str = Field("", description="别名自动站 eg:TEM")
    publisher: str = Field("", description="发布单位")
    height: int | None = Field(None, description="图片的高度")
    filter_list: str | None = Field(None, description="叠加到地图上显示的点;el:K8785,587458")
    wind_fontsize: int | None = Field(20, description="风向杆的大小")
    wind_color: str | None = Field("#fff", description="风向杆的颜色")
    point_color: str | None = Field("#666", description="圆点的颜色")
    txt_fontcolor: str | None = Field("#666", description="站名点颜色")
    val_fontcolor: str | None = Field("#666", description="站值点颜色")
    top: int = Field(0, description="获取排名")
    bar_aspect: int = Field(20, description="色标显示比例")
    bar_width: float | None = Field(None, description="色标高度占比，在0到1之间")
    bar_pad: float | None = Field(None, description="色标距离边框的距离eg:60")
    bar_fontsize: int = Field(14, description="色标字体设置")
    offset_lat: float = Field(15.0, description="纬度偏移量")
    bar_txtcolor: str = Field("#666", description="色标字体设置")
    area_txtcolor: str = Field("#999", description="区域字体设置")
    title_fontsize: int = Field(16, description="标题字体大小")
    txt_fontsize: int = Field(14, description="站点点字体大小")
    val_fontsize: int = Field(14, description="站值点字体大小")
    town_fontsize: int = Field(12, description="乡镇名称字体大小")
    title_pad: int = Field(15, description="标题离图的距离")
    bar_margin: int = Field(95, description="色标离图的距离")
    gen_all: bool = Field(False, description="生成所有图片")
    interpolation_method: str = Field(
        "rbf", description="插值方式: rbf(默认), idw(反距离加权), cressman(Cressman客观分析)"
    )
    bounds_lines: str | None = Field(
        None, description="边界线,传入str, el:'2,1.5,0.7'表示边界线宽为2,区县为1.5,镇为0.7，必须3个数"
    )
    bounds_colors: str | None = Field(
        None, description="边界线,传入str, el:'#333,#333, #666,第一个'表示边界线,第二区县为,第三个镇，必须3个数"
    )
