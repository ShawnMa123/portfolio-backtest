#!/bin/bash
# Docker Compose 安装脚本（适用于Debian/Ubuntu）

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

# 检测系统
detect_system() {
    if [ -f /etc/debian_version ]; then
        print_info "检测到Debian/Ubuntu系统"
        SYSTEM="debian"
    elif [ -f /etc/redhat-release ]; then
        print_info "检测到RedHat/CentOS系统"
        SYSTEM="redhat"
    else
        print_warning "未知系统类型，尝试通用安装方法"
        SYSTEM="unknown"
    fi
}

# 检查Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        print_info "安装命令: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi

    print_info "Docker已安装: $(docker --version)"
}

# 安装Docker Compose
install_docker_compose() {
    print_info "开始安装Docker Compose..."

    # 方法1: 尝试使用包管理器安装插件版本
    if [ "$SYSTEM" = "debian" ]; then
        print_info "尝试安装docker-compose-plugin..."

        if sudo apt update && sudo apt install -y docker-compose-plugin; then
            print_info "✅ docker-compose-plugin 安装成功"
            if docker compose version &> /dev/null; then
                print_info "✅ Docker Compose 插件安装成功"
                print_info "版本: $(docker compose version)"
                return 0
            fi
        fi

        print_warning "插件安装失败，尝试安装传统版本..."
        if sudo apt install -y docker-compose; then
            print_info "✅ docker-compose 传统版本安装成功"
            if command -v docker-compose &> /dev/null; then
                print_info "版本: $(docker-compose --version)"
                return 0
            fi
        fi
    fi

    # 方法2: 使用curl直接下载安装
    print_info "尝试下载最新版本的Docker Compose..."

    # 获取最新版本
    LATEST_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -oP '"tag_name": "\K(.*)(?=")')

    if [ -z "$LATEST_VERSION" ]; then
        LATEST_VERSION="v2.21.0"  # 备用版本
        print_warning "无法获取最新版本，使用备用版本: $LATEST_VERSION"
    else
        print_info "最新版本: $LATEST_VERSION"
    fi

    # 下载并安装
    COMPOSE_URL="https://github.com/docker/compose/releases/download/${LATEST_VERSION}/docker-compose-$(uname -s)-$(uname -m)"

    print_info "下载URL: $COMPOSE_URL"

    if sudo curl -L "$COMPOSE_URL" -o /usr/local/bin/docker-compose; then
        sudo chmod +x /usr/local/bin/docker-compose

        if command -v docker-compose &> /dev/null; then
            print_info "✅ Docker Compose 手动安装成功"
            print_info "版本: $(docker-compose --version)"
            return 0
        fi
    fi

    print_error "所有安装方法都失败了"
    return 1
}

# 验证安装
verify_installation() {
    print_info "验证Docker Compose安装..."

    if command -v docker-compose &> /dev/null; then
        print_info "✅ docker-compose 命令可用"
        docker-compose --version
    elif docker compose version &> /dev/null; then
        print_info "✅ docker compose 插件可用"
        docker compose version
    else
        print_error "Docker Compose安装验证失败"
        return 1
    fi

    print_info "🎉 Docker Compose安装成功！"
    print_info ""
    print_info "现在可以运行部署脚本了:"
    print_info "  ./deploy.sh --full"
}

# 主函数
main() {
    print_info "Docker Compose 自动安装脚本"
    print_info "=============================="

    detect_system
    check_docker

    if install_docker_compose; then
        verify_installation
    else
        print_error "安装失败，请手动安装Docker Compose"
        print_info ""
        print_info "手动安装方法:"
        print_info "1. 包管理器安装: sudo apt install docker-compose-plugin"
        print_info "2. 传统版本: sudo apt install docker-compose"
        print_info "3. 官方文档: https://docs.docker.com/compose/install/"
        exit 1
    fi
}

# 执行主函数
main "$@"