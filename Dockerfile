FROM python:3.12-slim

WORKDIR /app

# 先复制 requirements.txt，合并 apt 与 pip 为单层
COPY requirements.txt .
RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 复制项目文件
COPY . .

# 创建用户、数据目录、预置 ONNX 模型，合并为单层
RUN useradd -m -s /bin/bash appuser \
    && mkdir -p /app/data /app/memory/topics /app/chroma_db \
    && mkdir -p /home/appuser/.cache/chroma/onnx_models/all-MiniLM-L6-v2 \
    && if [ -f /app/onnx.tar.gz ]; then \
        mv /app/onnx.tar.gz /home/appuser/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz; \
    fi \
    && chown -R appuser:appuser /app /home/appuser/.cache

USER appuser

ENV HOST=0.0.0.0 \
    PORT=8080 \
    DB_PATH=/app/data/memory.db \
    TOPIC_DIR=/app/data/topics \
    CHROMA_DB_PATH=/app/data/chroma_db

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

CMD ["python", "main.py"]

#apt + pip 合并为单层 — COPY requirements.txt 提前，系统依赖和 Python 依赖在同一个 RUN 中安装
#useradd + mkdir + chown + ONNX 预置合并为单层 — 所有用户创建和目录初始化放在一个 RUN 里
#5 个 ENV 合并为 1 个 — 用反斜杠续行，避免每个 ENV 各产生一层
#非 root 用户 — USER appuser 替代 root 运行
#ONNX 路径修正 — 从 /root/.cache/chroma 改为 /home/appuser/.cache/chroma，与非 root 用户匹配
