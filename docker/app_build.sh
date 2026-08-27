#!/bin/bash

# Collector Docker 构建脚本
# 用于构建 collector 的 Docker 镜像

set -e

# 配置变量
IMAGE_NAME="collector"
IMAGE_TAG="${1:-v1}"
DOCKERFILE_PATH="docker/Dockerfile"
BUILD_CONTEXT=".."

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Collector Docker 镜像构建${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}镜像名称:${NC} ${IMAGE_NAME}:${IMAGE_TAG}"
echo -e "${YELLOW}Dockerfile:${NC} ${DOCKERFILE_PATH}"
echo ""

# 切换到脚本所在目录的父目录（项目根目录）
cd "$(dirname "$0")/.."

# 检查 Dockerfile 是否存在
if [ ! -f "${DOCKERFILE_PATH}" ]; then
    echo -e "${RED}错误: Dockerfile 不存在: ${DOCKERFILE_PATH}${NC}"
    exit 1
fi

# 检查必要文件
echo -e "${YELLOW}检查必要文件...${NC}"
required_files=("requirements.txt" "main.py" "scheduler.py" "config/config.py" "config/task_config.yaml")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}错误: $file 不存在${NC}"
        exit 1
    else
        echo -e "${GREEN}✓${NC} $file"
    fi
done
echo ""

# 显示构建选项
echo -e "${YELLOW}构建选项:${NC}"
echo "  --no-cache: 不使用缓存"
echo "  --pull: 拉取最新基础镜像"
echo ""

# 开始构建
echo -e "${GREEN}开始构建镜像...${NC}"
echo ""

docker build \
    --no-cache \
    --pull \
    -f "${DOCKERFILE_PATH}" \
    -t "${IMAGE_NAME}:${IMAGE_TAG}" \
    -t "${IMAGE_NAME}:latest" \
    .

# 检查构建结果
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  构建成功!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}镜像信息:${NC}"
    docker images | grep "${IMAGE_NAME}" | head -2
    echo ""
    echo -e "${YELLOW}使用以下命令启动容器:${NC}"
    echo -e "  ${GREEN}./docker/app_start.sh${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  构建失败!${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
