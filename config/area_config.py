from __future__ import annotations


_DEFAULT_LAYOUT = {
    "top_location": "0,0,0.28,0.25",
    "face_location": "0.7,0,0.3,0.25",
    "width": 900,
    "height": 700,
}

_CUSTOM_LAYOUTS: dict[str, dict] = {
    "330100": {"top_location": "0.7,0,0.3,0.25", "face_location": "0.0,0.7,0.3,0.3"},
    "330500": {"top_location": "0,0.55,0.28,0.25", "face_location": "0.8,0.08,0.2,0.25"},
    "330523": {"top_location": "0.78,0.08,0.1,0.1", "face_location": "0,0.80,0.28,0.25"},
    "330800": {"top_location": "0,0.01,0.28,0.3", "face_location": "0.75,0.08,0.25,0.25", "width": 800},
    "330802": {"face_location": "0.75,0.1,0.25,0.1"},
}


def get_area_layout(code: str) -> dict:
    """根据区划代码获取布局配置, 自定义配置覆盖默认值.

    Args:
        code: 区划代码, 如 "330100"

    Returns:
        布局配置字典, 包含 top_location/face_location/width/height 等键
    """
    custom = _CUSTOM_LAYOUTS.get(str(code), {})
    return {**_DEFAULT_LAYOUT, **custom}


AREAS = {
    "330100": "杭州市", "330102": "上城区", "330105": "拱墅区", "330106": "西湖区", "330108": "滨江区",
    "330109": "萧山区", "330110": "余杭区", "330111": "富阳区", "330112": "临安区", "330113": "临平区",
    "330114": "钱塘区", "330122": "桐庐县", "330127": "淳安县", "330182": "建德市", "330200": "宁波市",
    "330203": "海曙区", "330205": "江北区", "330206": "北仑区", "330211": "镇海区", "330212": "鄞州区",
    "330213": "奉化区", "330225": "象山县", "330226": "宁海县", "330281": "余姚市", "330282": "慈溪市",
    "330300": "温州市", "330302": "鹿城区", "330303": "龙湾区", "330304": "瓯海区", "330305": "洞头区",
    "330324": "永嘉县", "330326": "平阳县", "330327": "苍南县", "330328": "文成县", "330329": "泰顺县",
    "330381": "瑞安市", "330382": "乐清市", "330383": "龙港市", "330400": "嘉兴市", "330402": "南湖区",
    "330411": "秀洲区", "330421": "嘉善县", "330424": "海盐县", "330481": "海宁市", "330482": "平湖市",
    "330483": "桐乡市", "330500": "湖州市", "330502": "吴兴区", "330503": "南浔区", "330521": "德清县",
    "330522": "长兴县", "330523": "安吉县", "330600": "绍兴市", "330602": "越城区", "330603": "柯桥区",
    "330604": "上虞区", "330624": "新昌县", "330681": "诸暨市", "330683": "嵊州市", "330700": "金华市",
    "330702": "婺城区", "330703": "金东区", "330723": "武义县", "330726": "浦江县", "330727": "磐安县",
    "330781": "兰溪市", "330782": "义乌市", "330783": "东阳市", "330784": "永康市", "330800": "衢州市",
    "330802": "柯城区", "330803": "衢江区", "330822": "常山县", "330824": "开化县", "330825": "龙游县",
    "330881": "江山市", "330900": "舟山市", "330902": "定海区", "330903": "普陀区", "330921": "岱山县",
    "330922": "嵊泗县", "331000": "台州市", "331002": "椒江区", "331003": "黄岩区", "331004": "路桥区",
    "331022": "三门县", "331023": "天台县", "331024": "仙居县", "331081": "温岭市", "331082": "临海市",
    "331083": "玉环市", "331100": "丽水市", "331102": "莲都区", "331121": "青田县", "331122": "缙云县",
    "331123": "遂昌县", "331124": "松阳县", "331125": "云和县", "331126": "庆元县", "331127": "景宁畲族自治县",
    "331181": "龙泉市",
    "330000": "浙江省",
}

SHOW_MINS = [
    "VIS", "VIS_H_POINT", "VIS_MIN_1H", "VIS_MIN_DAY", "VIS_MIN_24H", "VIS_AVG_1MI",
    "VIS_AVG_1MI_H", "VIS_AVG_10MI", "VIS_AVG_10MI_H", "VIS_MIN_MI", "VIS_MIN_H",
    "VIS_H", "VIS_MI_BY_MI", "VIS_H_BY_H", "TEM_MIN_1H", "TEM_MIN_24H", "TEM_MIN_DAY",
    "SUM_TEM_MIN_FREE", "TEM_MIN_H_BY_H", "TEM_MIN_2020", "TEM_MIN_0808", "PRS_MIN_1H",
    "PRS_MIN_3H", "PRS_MIN_6H", "PRS_MIN_24H", "PRS_MIN_STATION_POINT", "RHU_MIN_DAY",
    "RHU_MIN_24H", "PRE_H_BY_H",
]

ELS = {
    "wind": ["WIN_S_INST_H_POINT", "WIN_S_INST_MAX_1H", "WIN_S_INST_MAX_3H"],
    "rain": ["SUM_PRE_1H_POINT", "SUM_PRE_3H_POINT", "SUM_PRE_12H_POINT", "SUM_PRE_12H_POINT"],
    "tem": ["TEM_MAX_1H", "TEM_MIN_1H", "TEM_H_POINT", "TEM_MAX_24H", "TEM_MIN_24H"],
}

RAIN_PRE = {
    "SUM_PRE_5MI": 5, "SUM_PRE_10MI": 10, "SUM_PRE_30MI": 30, "SUM_PRE_1H": 60,
    "SUM_PRE_3H": 3 * 60, "SUM_PRE_6H": 6 * 60, "SUM_PRE_12H": 12 * 60,
    "SUM_PRE_24H": 24 * 60, "SUM_PRE_36H": 36 * 60, "SUM_PRE_48H": 48 * 60,
    "SUM_PRE_72H": 72 * 60, "SUM_PRE_SINCE_MI": 60, "SUM_PRE_1H_POINT": 1 * 60,
    "SUM_PRE_3H_POINT": 3 * 60, "SUM_PRE_6H_POINT": 6 * 60, "SUM_PRE_12H_POINT": 12 * 60,
    "SUM_PRE_24H_POINT": 24 * 60, "SUM_PRE_36H_POINT": 36 * 60, "SUM_PRE_48H_POINT": 48 * 60,
    "SUM_PRE_72H_POINT": 72 * 60, "SUM_PRE_0808": 24 * 60, "SUM_PRE_2020": 24 * 60,
    "SUM_PRE_0505": 24 * 60, "SUM_PRE_FREE": -1, "PRE_MI_BY_MI": -1, "PRE_H_BY_H": -1,
    "PRE_D_BY_D": -1, "PRE_MAX_1H_HISTORY": -1, "PRE_MAX_3H_HISTORY": -1,
    "PRE_MAX_6H_HISTORY": -1, "PRE_MAX_12H_HISTORY": -1, "PRE_MAX_24H_HISTORY": -1,
    "SUM_PRE_1H_POINT_WATER": 60, "SUM_PRE_3H_POINT_WATER": 3 * 60,
    "SUM_PRE_6H_POINT_WATER": 6 * 60, "SUM_PRE_12H_POINT_WATER": 12 * 60,
    "SUM_PRE_24H_POINT_WATER": 24 * 60, "SUM_PRE_36H_POINT_WATER": 36 * 60,
    "SUM_PRE_48H_POINT_WATER": 48 * 60, "SUM_PRE_72H_POINT_WATER": 72 * 60,
    "SUM_PRE_0808_WATER": 24 * 60, "SUM_PRE_2020_WATER": 24 * 60,
}
