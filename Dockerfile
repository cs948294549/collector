FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 复制 requirements.txt
COPY requirements.txt .

# 安装 Python 依赖（aiosnmp 是纯 Python 实现，无需系统依赖）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/logs

# 设置权限
RUN chmod +x /app/main.py

# 健康检查（检查主进程是否运行）
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD ps aux | grep -v grep | grep -q "python.*main.py" || exit 1

# 启动应用
CMD ["python3", "-u", "main.py"]
