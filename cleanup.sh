#!/bin/bash
# 快速清理脚本 - 解决容器名冲突问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检测Docker Compose命令
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    print_error "Docker Compose未找到"
    exit 1
fi

print_info "清理所有冲突的容器..."

# 停止所有相关的Docker Compose项目
print_info "停止Docker Compose项目..."
$DOCKER_COMPOSE_CMD -f docker-compose.full.yml down --remove-orphans 2>/dev/null || true
$DOCKER_COMPOSE_CMD -f docker-compose.hybrid.yml down --remove-orphans 2>/dev/null || true

# 强制删除可能冲突的容器
print_info "删除冲突容器..."
docker rm -f \
    redis-proxy-pool \
    redis-proxy-pool-full \
    redis-proxy-pool-hybrid \
    warp-proxy-1 \
    warp-proxy-2 \
    warp-proxy-3 \
    warp-proxy-4 \
    warp-proxy-5 \
    warp-proxy-1-full \
    warp-proxy-2-full \
    warp-proxy-3-full \
    warp-proxy-4-full \
    warp-proxy-5-full \
    warp-proxy-1-hybrid \
    warp-proxy-2-hybrid \
    warp-proxy-3-hybrid \
    warp-proxy-4-hybrid \
    warp-proxy-5-hybrid \
    portfolio-postgres \
    portfolio-postgres-hybrid \
    portfolio-redis \
    portfolio-redis-hybrid \
    portfolio-app \
    portfolio-celery-worker \
    portfolio-monitor \
    portfolio-init \
    portfolio-db-init-hybrid \
    2>/dev/null || true

# 清理未使用的网络
print_info "清理Docker网络..."
docker network prune -f 2>/dev/null || true

# 显示当前容器状态
print_info "当前容器状态:"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

print_info "✅ 清理完成！现在可以重新部署了。"
print_info ""
print_info "运行部署命令:"
print_info "  ./deploy.sh --full    # 完全Docker化部署"
print_info "  ./deploy.sh --hybrid  # 混合部署"