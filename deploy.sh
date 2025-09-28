#!/bin/bash
# 简化部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示使用方法
show_usage() {
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --full      完全Docker化部署（推荐）"
    echo "  --hybrid    混合部署（Python手动 + Docker中间件）"
    echo "  --stop      停止所有服务"
    echo "  --clean     清理所有容器和数据"
    echo "  --status    查看服务状态"
    echo "  --logs      查看日志"
    echo "  --help      显示此帮助信息"
}

# 检查Docker和Docker Compose
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi

    # 检查Docker Compose (支持新旧两种方式)
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
        print_info "使用传统docker-compose命令"
    elif docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
        print_info "使用新版docker compose插件"
    else
        print_error "Docker Compose未安装，请安装Docker Compose"
        print_info "安装方法1: sudo apt install docker-compose-plugin"
        print_info "安装方法2: sudo apt install docker-compose"
        exit 1
    fi

    print_info "Docker环境检查通过"
}

# 完全Docker化部署
deploy_full() {
    print_info "开始完全Docker化部署..."

    # 停止现有服务
    print_info "停止现有服务..."
    $DOCKER_COMPOSE_CMD -f docker-compose.full.yml down 2>/dev/null || true

    # 构建镜像
    print_info "构建应用镜像..."
    $DOCKER_COMPOSE_CMD -f docker-compose.full.yml build

    # 启动服务
    print_info "启动所有服务..."
    $DOCKER_COMPOSE_CMD -f docker-compose.full.yml up -d

    print_info "等待服务启动..."
    sleep 10

    # 检查服务状态
    print_info "检查服务状态..."
    $DOCKER_COMPOSE_CMD -f docker-compose.full.yml ps

    print_info "完全Docker化部署完成！"
    print_info "访问地址: http://localhost:5000"
    print_info "API文档: http://localhost:5000/api/docs/"
    print_info "健康检查: http://localhost:5000/health"
}

# 混合部署
deploy_hybrid() {
    print_info "开始混合部署..."

    # 停止现有服务
    print_info "停止现有中间件服务..."
    $DOCKER_COMPOSE_CMD -f docker-compose.hybrid.yml down 2>/dev/null || true

    # 启动中间件
    print_info "启动中间件服务（数据库、Redis、代理池）..."
    $DOCKER_COMPOSE_CMD -f docker-compose.hybrid.yml up -d

    print_info "等待中间件启动..."
    sleep 15

    # 检查服务状态
    print_info "检查中间件状态..."
    $DOCKER_COMPOSE_CMD -f docker-compose.hybrid.yml ps

    print_info "混合部署中间件启动完成！"
    print_info ""
    print_info "现在需要手动启动Python应用:"
    print_info "1. 复制环境配置: cp .env.hybrid .env"
    print_info "2. 安装依赖: pip install -r requirements.txt"
    print_info "3. 启动Celery: python scripts/celery_worker.py"
    print_info "4. 启动应用: python app.py"
}

# 停止服务
stop_services() {
    print_info "停止所有服务..."

    $DOCKER_COMPOSE_CMD -f docker-compose.full.yml down 2>/dev/null || true
    $DOCKER_COMPOSE_CMD -f docker-compose.hybrid.yml down 2>/dev/null || true

    print_info "所有服务已停止"
}

# 清理所有
clean_all() {
    print_warning "这将删除所有容器、镜像和数据，请确认！"
    read -p "确认清理所有数据？ (y/N): " confirm

    if [[ $confirm == [yY] ]]; then
        print_info "清理所有容器和数据..."

        $DOCKER_COMPOSE_CMD -f docker-compose.full.yml down -v --rmi all 2>/dev/null || true
        $DOCKER_COMPOSE_CMD -f docker-compose.hybrid.yml down -v --rmi all 2>/dev/null || true

        # 清理孤立容器
        docker container prune -f 2>/dev/null || true
        docker image prune -f 2>/dev/null || true
        docker volume prune -f 2>/dev/null || true

        print_info "清理完成"
    else
        print_info "取消清理操作"
    fi
}

# 查看状态
show_status() {
    print_info "=== 完全Docker化部署状态 ==="
    $DOCKER_COMPOSE_CMD -f docker-compose.full.yml ps 2>/dev/null || print_warning "完全Docker化部署未运行"

    echo ""
    print_info "=== 混合部署状态 ==="
    $DOCKER_COMPOSE_CMD -f docker-compose.hybrid.yml ps 2>/dev/null || print_warning "混合部署未运行"

    echo ""
    print_info "=== 端口占用情况 ==="
    netstat -tlnp 2>/dev/null | grep -E ":(5000|5432|6379|6380|40001|40002|40003|40004|40005)" || print_warning "相关端口未被占用"
}

# 查看日志
show_logs() {
    print_info "选择要查看的日志:"
    echo "1. 完全Docker化部署日志"
    echo "2. 混合部署日志"
    echo "3. 特定服务日志"

    read -p "请选择 (1-3): " choice

    case $choice in
        1)
            $DOCKER_COMPOSE_CMD -f docker-compose.full.yml logs -f --tail=100
            ;;
        2)
            $DOCKER_COMPOSE_CMD -f docker-compose.hybrid.yml logs -f --tail=100
            ;;
        3)
            echo "可用服务:"
            echo "  app, celery-worker, postgres, redis, warp-1, warp-2, warp-3, warp-4, warp-5"
            read -p "请输入服务名: " service
            $DOCKER_COMPOSE_CMD -f docker-compose.full.yml logs -f --tail=100 $service 2>/dev/null || \
            $DOCKER_COMPOSE_CMD -f docker-compose.hybrid.yml logs -f --tail=100 $service 2>/dev/null || \
            print_error "服务不存在或未运行"
            ;;
        *)
            print_error "无效选择"
            ;;
    esac
}

# 主函数
main() {
    case "${1:-}" in
        --full)
            check_docker
            deploy_full
            ;;
        --hybrid)
            check_docker
            deploy_hybrid
            ;;
        --stop)
            stop_services
            ;;
        --clean)
            clean_all
            ;;
        --status)
            show_status
            ;;
        --logs)
            show_logs
            ;;
        --help)
            show_usage
            ;;
        "")
            print_error "请指定部署方式"
            show_usage
            exit 1
            ;;
        *)
            print_error "未知选项: $1"
            show_usage
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"