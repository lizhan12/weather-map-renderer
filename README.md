# py_draw

气象数据可视化地图图片渲染服务，基于 FastAPI + Matplotlib + Cartopy，将站点观测数据、NC 格点数据渲染为可视化地图图片。

## 功能特性

- 站点离散点数据填色图（温度、降水、风速、能见度等）
- NC 格点数据渲染
- 雷达/卫星数据叠加
- 自动缓存 + TTL 过期清理
- 多进程渲染，支持并发请求
- SM4 加密数据传输

## 快速开始

### 环境要求

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) 包管理器

### 本地开发

```bash
# 安装依赖
make install

# 安装开发依赖 + pre-commit
make dev

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际配置

# 启动服务
make run
```

服务默认监听 `http://0.0.0.0:8001`。

### Docker 部署

```bash
# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

## API 接口

### GET - 获取气象图片

```
GET /api/pic/{code}/{datestr}/{data_type}/{axis}
```

| 参数 | 说明 | 示例 |
|------|------|------|
| code | 行政区号6位 | 330700 |
| datestr | 日期时间 | 20260510080000 |
| data_type | 数据类型 | tem / rain / wind |
| axis | 数据别名 | TEM_H_POINT |

常用查询参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| show_contourf | true | 显示填色图 |
| show_value | true | 显示站点数值 |
| show_town | true | 显示乡镇边界 |
| show_wind | false | 显示风向杆 |
| is_clip | true | 裁剪图片 |
| width | 700 | 图片宽度 |
| height | 700 | 图片高度 |

完整参数列表参见 `/docs` 页面。

### POST - 提交数据渲染

```
POST /api/pic/{code}/{data_type}
```

请求体为 JSON，包含站点数据数组。POST 请求自动保存图片文件，返回文件 ID。

### 获取已保存图片

```
GET /api/pic/img/{id}
```

## 配置说明

所有配置通过环境变量注入，前缀为 `PYDRAW_`，支持 `.env` 文件。

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `PYDRAW_BASE_PATH` | `/home/lizhan/tu` | 基础路径 |
| `PYDRAW_WIDTH` | 700 | 图片默认宽度 |
| `PYDRAW_HEIGHT` | 700 | 图片默认高度 |
| `PYDRAW_CACHE_TTL` | 300 | 缓存过期时间（秒） |
| `PYDRAW_CACHE_MAX_FILES` | 500 | 最大缓存文件数 |
| `PYDRAW_RENDER_WORKERS` | 0 | 渲染进程数（0=自动） |
| `PYDRAW_RENDER_MAX_WORKERS` | 4 | 进程池最大工作数 |
| `PYDRAW_SHAPE_PATH` | | Shapefile 目录（留空用默认） |
| `PYDRAW_IMG_PATH` | | 图片输出目录（留空用默认） |
| `PYDRAW_LOG_PATH` | | 日志目录（留空用默认） |
| `PYDRAW_DATA_SERVICE_URL` | | 数据服务 URL |
| `PYDRAW_DATA_SERVICE_KEY` | | SM4 加密密钥 |
| `PYDRAW_DATA_SERVICE_SIGN_KEY` | | SM4 签名密钥 |

## 项目结构

```
py_draw/
├── main.py                 # 应用入口
├── manage.py               # FastAPI 应用工厂
├── api/                    # API 层（参数接收和响应）
│   └── img_v2.py           # 图片路由
├── models/                 # 数据模型层
│   └── base.py             # 请求/响应模型
├── services/               # 业务逻辑层
│   ├── data_service.py     # 数据获取与处理
│   ├── shape_service.py    # Shapefile 读取与缓存
│   └── render_service.py   # 渲染管线 + 缓存管理
├── rendering/              # 渲染引擎（子进程执行）
│   ├── worker.py           # 渲染 Worker
│   └── layers/             # 图层模块
├── config/                 # 配置（只读）
│   └── settings.py         # 全局配置
├── util/                   # 工具函数
│   ├── interpolate.py      # 插值算法
│   ├── sm4.py              # SM4 加解密
│   └── trace.py            # 链路追踪
├── font/                   # 字体资源
├── zjaws/                  # Shapefile 数据
└── static/                 # 静态文件
```

## 开发命令

```bash
make install    # 安装依赖
make dev        # 安装开发依赖 + 初始化 pre-commit
make lint       # 代码检查
make format     # 代码格式化
make test       # 运行测试
make run        # 启动服务
make clean      # 清理缓存
```

## 技术栈

- **Web 框架**: FastAPI + Uvicorn
- **地图渲染**: Matplotlib + Cartopy
- **空间计算**: Shapely + SciPy
- **数据加密**: gmalglib (SM4)
- **配置管理**: pydantic-settings
- **包管理**: uv
