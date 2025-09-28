#!/bin/bash
# 快速修复登录问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_section() {
    echo -e "${BLUE}[SECTION]${NC} $1"
    echo "=================================="
}

print_section "快速修复登录问题"

# 检查服务状态
print_info "1. 检查服务状态..."
if ! docker ps | grep portfolio-postgres > /dev/null; then
    print_error "PostgreSQL容器未运行，请先运行: ./deploy.sh --full"
    exit 1
fi

# 重新运行初始化
print_info "2. 重新运行数据库初始化..."
if docker ps | grep portfolio-init > /dev/null; then
    print_info "初始化容器正在运行，等待完成..."
    docker wait portfolio-init 2>/dev/null || true
fi

print_info "手动运行初始化..."
docker run --rm \
    --name portfolio-manual-init \
    --network portfolio-network \
    -e DATABASE_URL=postgresql://postgres:portfolio_password_2024@postgres:5432/portfolio_backtest \
    -e REDIS_URL=redis://redis:6379/0 \
    -e PROXY_POOL_REDIS_URL=redis://redis-proxy-pool-full:6379/0 \
    -e FLASK_ENV=production \
    -e SYNC_DATA=false \
    portfolio-backtest-init python /app/scripts/docker-init.py

# 验证用户是否创建成功
print_info "3. 验证用户创建..."
user_count=$(docker exec portfolio-postgres psql -U postgres -d portfolio_backtest -t -c "SELECT COUNT(*) FROM users WHERE username='demo';" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$user_count" -gt 0 ]; then
    print_info "✅ Demo用户已存在"
else
    print_warning "⚠️ Demo用户不存在，手动创建..."
    ./create-user.sh
fi

# 测试登录API
print_info "4. 测试登录API..."
sleep 2  # 等待服务稳定

login_response=$(curl -s -X POST http://localhost:5000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "demo", "password": "password123"}' \
    -w "%{http_code}" 2>/dev/null || echo "000")

http_code="${login_response: -3}"
response_body="${login_response%???}"

if [ "$http_code" = "200" ]; then
    print_info "✅ 登录成功！"
    echo "响应: $response_body"

    print_info ""
    print_info "🎉 修复完成！现在可以使用以下凭据登录:"
    print_info "用户名: demo"
    print_info "密码: password123"
    print_info "登录地址: http://localhost:5000"
else
    print_error "❌ 登录仍然失败 (HTTP $http_code)"
    echo "响应: $response_body"

    print_info ""
    print_info "进一步调试步骤:"
    print_info "1. 查看应用日志: docker logs portfolio-app"
    print_info "2. 查看数据库: docker exec -it portfolio-postgres psql -U postgres -d portfolio_backtest"
    print_info "3. 运行完整诊断: ./diagnose.sh"
fi