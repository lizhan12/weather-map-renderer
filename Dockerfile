# ── Builder ────────────────────────────────────────────────────────────────
FROM python:3.10-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ gfortran \
    libgeos-dev libproj-dev proj-bin \
    libgdal-dev \
    git \
    # builder 阶段不需要 gdal-bin（CLI 工具），只需编译头文件
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./

RUN uv venv --python 3.10 \
    && uv sync --frozen --no-dev --no-install-project

# ── Runtime ────────────────────────────────────────────────────────────────
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    # fonts-noto-cjk 在 slim 镜像中包名可能不同，按诊断结果二选一：
    fonts-noto-cjk \
    # 若上面报错，改用：fonts-noto（体积更小，覆盖大部分中日韩字符）
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY . .

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]