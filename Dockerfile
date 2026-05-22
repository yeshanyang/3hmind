FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建持久化数据目录（可通过 volume 挂载覆盖）
RUN mkdir -p /app/data /app/memory/topics /app/chroma_db

# 环境变量默认值（运行时通过 -e 或 env-file 覆盖）
ENV HOST=0.0.0.0
ENV PORT=8080
ENV MEMORY_PATH=/app/data/agent_memory.json
ENV DB_PATH=/app/data/memory.db
ENV TOPIC_DIR=/app/data/topics
ENV VECTOR_PATH=/app/data/vector_memory

# ChromaDB 持久化目录重定向到 /app/data
ENV CHROMA_DB_PATH=/app/data/chroma_db

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/api/status || exit 1

CMD ["python", "main.py"]
