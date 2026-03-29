FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖 - 使用清华镜像源加速
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple --default-timeout=100 && \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple --default-timeout=100 -r requirements.txt

# 复制项目文件
COPY src/ ./src/
COPY run.py .

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "run.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
