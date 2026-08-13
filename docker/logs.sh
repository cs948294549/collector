#!/bin/bash

# Collector 日志查看脚本
# 快速查看和排查 Docker 容器日志

set -e

CONTAINER_NAME="collector"
DATA_BASE_DIR="${COLLECTOR_DATA_DIR:-$(pwd)}"
LOGS_DIR="${DATA_BASE_DIR}/logs"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 显示帮助信息
show_help() {
    echo -e "${GREEN}Collector 日志查看工具${NC}"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  follow, -f        实时跟踪 Docker 日志（默认）"
    echo "  tail [N]          查看最后 N 行日志（默认 100）"
    echo "  app               查看应用日志文件列表"
    echo "  scheduler         实时跟踪调度器日志"
    echo "  collector         实时跟踪采集器日志"
    echo "  error             查看错误日志"
    echo "  search [keyword]  搜索包含关键字的日志"
    echo "  clear             清空应用日志文件"
    echo "  help, -h          显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                    # 实时查看 Docker 日志"
    echo "  $0 tail 200           # 查看最后 200 行"
    echo "  $0 app                # 列出应用日志文件"
    echo "  $0 scheduler          # 实时查看调度器日志"
    echo "  $0 collector          # 实时查看采集器日志"
    echo "  $0 error              # 查看错误日志"
    echo "  $0 search \"采集\"      # 搜索包含关键字的日志"
    echo ""
}

# 检查容器是否运行
check_container() {
    if ! docker ps | grep -q "${CONTAINER_NAME}"; then
        echo -e "${RED}错误: 容器 ${CONTAINER_NAME} 未运行${NC}"
        echo -e "${YELLOW}提示: 使用 ./docker/app_start.sh 启动容器${NC}"
        exit 1
    fi
}

# 实时跟踪 Docker 日志
follow_docker_logs() {
    check_container
    echo -e "${GREEN}实时跟踪 Docker 日志 (Ctrl+C 退出)${NC}"
    echo -e "${YELLOW}容器: ${CONTAINER_NAME}${NC}"
    echo ""
    docker logs -f "${CONTAINER_NAME}"
}

# 查看最后 N 行日志
tail_docker_logs() {
    local lines=${1:-100}
    check_container
    echo -e "${GREEN}查看最后 ${lines} 行 Docker 日志${NC}"
    echo ""
    docker logs --tail "${lines}" "${CONTAINER_NAME}"
}

# 列出应用日志文件
list_app_logs() {
    echo -e "${GREEN}应用日志文件列表${NC}"
    echo -e "${YELLOW}日志目录: ${LOGS_DIR}${NC}"
    echo ""

    if [ ! -d "${LOGS_DIR}" ]; then
        echo -e "${RED}错误: 日志目录不存在${NC}"
        exit 1
    fi

    if [ -z "$(ls -A ${LOGS_DIR} 2>/dev/null)" ]; then
        echo -e "${YELLOW}日志目录为空${NC}"
    else
        ls -lh "${LOGS_DIR}"
    fi
}

# 实时跟踪调度器日志
tail_scheduler_log() {
    local logpath="${LOGS_DIR}/scheduler.log"

    if [ ! -f "${logpath}" ]; then
        echo -e "${RED}错误: 调度器日志文件不存在: ${logpath}${NC}"
        exit 1
    fi

    echo -e "${GREEN}实时跟踪调度器日志 (Ctrl+C 退出)${NC}"
    echo -e "${YELLOW}文件: ${logpath}${NC}"
    echo ""
    tail -f "${logpath}"
}

# 实时跟踪采集器日志
tail_collector_log() {
    local logpath="${LOGS_DIR}/collector.log"

    if [ ! -f "${logpath}" ]; then
        echo -e "${RED}错误: 采集器日志文件不存在: ${logpath}${NC}"
        exit 1
    fi

    echo -e "${GREEN}实时跟踪采集器日志 (Ctrl+C 退出)${NC}"
    echo -e "${YELLOW}文件: ${logpath}${NC}"
    echo ""
    tail -f "${logpath}"
}

# 查看错误日志
show_error_logs() {
    check_container
    echo -e "${GREEN}查看错误日志${NC}"
    echo ""
    docker logs "${CONTAINER_NAME}" 2>&1 | grep -iE "error|exception|fail|traceback" --color=always
}

# 搜索日志
search_logs() {
    local keyword="$1"

    if [ -z "$keyword" ]; then
        echo -e "${RED}错误: 请提供搜索关键字${NC}"
        exit 1
    fi

    check_container
    echo -e "${GREEN}搜索包含 '${keyword}' 的日志${NC}"
    echo ""
    docker logs "${CONTAINER_NAME}" 2>&1 | grep -i "${keyword}" --color=always
}

# 清空应用日志
clear_logs() {
    echo -e "${YELLOW}确认要清空应用日志吗? (y/N)${NC}"
    read -r confirm

    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        rm -f "${LOGS_DIR}"/*.log
        echo -e "${GREEN}✓ 应用日志已清空${NC}"
    else
        echo -e "${YELLOW}已取消${NC}"
    fi
}

# 主逻辑
case "${1:-follow}" in
    follow|-f)
        follow_docker_logs
        ;;
    tail)
        tail_docker_logs "$2"
        ;;
    app)
        list_app_logs
        ;;
    scheduler)
        tail_scheduler_log
        ;;
    collector)
        tail_collector_log
        ;;
    error)
        show_error_logs
        ;;
    search)
        search_logs "$2"
        ;;
    clear)
        clear_logs
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        echo -e "${RED}未知选项: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
