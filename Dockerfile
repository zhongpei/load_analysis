# 使用Python 3.10作为基础镜像
FROM python:3.10-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# 设置工作目录
WORKDIR /app

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN sed -i "s/http:\/\/deb\.debian\.org/https:\/\/mirrors\.tuna\.tsinghua\.edu\.cn/" /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    procps \
    net-tools \
    lsof \
    htop \
    iotop \
    sysstat \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt pyproject.toml ./

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 安装项目
RUN pip install -e .

# 创建非root用户
RUN useradd -m -u 1000 analyzer && \
    chown -R analyzer:analyzer /app

# 切换到非root用户
USER analyzer

# 设置入口点
ENTRYPOINT ["python","cli.py"]


