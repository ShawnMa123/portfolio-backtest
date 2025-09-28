#!/bin/bash
# 系统诊断脚本 - 检查登录失败问题

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

# 检测Docker Compose命令
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    print_error "Docker Compose未找到"
    exit 1
fi

# 1. 检查容器状态
print_section "1. 容器状态检查"
$DOCKER_COMPOSE_CMD -f docker-compose.full.yml ps

echo ""
print_info "容器健康状态："
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(portfolio|redis|postgres|warp)" || print_warning "未找到相关容器"

# 2. 检查关键端口
print_section "2. 端口检查"
ports=(5000 5432 6379 6380)
for port in "${ports[@]}"; do
    if netstat -tlnp 2>/dev/null | grep ":$port " > /dev/null; then
        print_info "✅ 端口 $port 已监听"
    else
        print_error "❌ 端口 $port 未监听"
    fi
done

# 3. 检查应用健康状态
print_section "3. 应用健康检查"
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    print_info "✅ 应用健康检查通过"
    echo "健康状态："
    curl -s http://localhost:5000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:5000/health
else
    print_error "❌ 应用健康检查失败"
    print_info "尝试连接应用..."
    curl -v http://localhost:5000/health 2>&1 | head -10 || echo "连接失败"
fi

# 4. 检查数据库连接
print_section "4. 数据库连接检查"
if docker exec portfolio-postgres pg_isready -U postgres > /dev/null 2>&1; then
    print_info "✅ PostgreSQL 可用"

    # 检查数据库内容
    print_info "检查用户表..."
    user_count=$(docker exec portfolio-postgres psql -U postgres -d portfolio_backtest -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ' || echo "0")
    if [ "$user_count" -gt 0 ]; then
        print_info "✅ 用户表有 $user_count 条记录"
        print_info "用户列表："
        docker exec portfolio-postgres psql -U postgres -d portfolio_backtest -c "SELECT id, username, email, created_at FROM users;" 2>/dev/null || print_warning "无法查询用户"
    else
        print_error "❌ 用户表为空或不存在"
    fi
else
    print_error "❌ PostgreSQL 不可用"
fi

# 5. 检查Redis连接
print_section "5. Redis连接检查"
if docker exec portfolio-redis redis-cli ping > /dev/null 2>&1; then
    print_info "✅ Redis 主服务可用"
else
    print_error "❌ Redis 主服务不可用"
fi

if docker exec redis-proxy-pool-full redis-cli ping > /dev/null 2>&1; then
    print_info "✅ Redis 代理池服务可用"
else
    print_error "❌ Redis 代理池服务不可用"
fi

# 6. 检查应用日志
print_section "6. 应用日志检查"
print_info "最近的应用日志："
docker logs portfolio-app --tail=20 2>/dev/null || print_warning "无法获取应用日志"

print_info ""
print_info "最近的初始化日志："
docker logs portfolio-init --tail=20 2>/dev/null || print_warning "无法获取初始化日志"

# 7. 测试API端点
print_section "7. API端点测试"

# 测试登录API
print_info "测试登录API..."
login_response=$(curl -s -X POST http://localhost:5000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "demo", "password": "password123"}' \
    -w "%{http_code}" 2>/dev/null || echo "000")

http_code="${login_response: -3}"
response_body="${login_response%???}"

if [ "$http_code" = "200" ]; then
    print_info "✅ 登录API正常 (HTTP $http_code)"
elif [ "$http_code" = "401" ]; then
    print_warning "⚠️ 登录失败 - 用户名或密码错误 (HTTP $http_code)"
    echo "响应: $response_body"
elif [ "$http_code" = "500" ]; then
    print_error "❌ 服务器内部错误 (HTTP $http_code)"
    echo "响应: $response_body"
else
    print_error "❌ API不可访问 (HTTP $http_code)"
fi

# 8. 总结和建议
print_section "8. 诊断总结"

print_info "如果登录失败，可能的解决方案："
echo "1. 重新初始化数据库："
echo "   docker exec portfolio-init python /app/scripts/docker-init.py"
echo ""
echo "2. 重启应用服务："
echo "   ./deploy.sh --stop"
echo "   ./deploy.sh --full"
echo ""
echo "3. 查看详细日志："
echo "   ./deploy.sh --logs"
echo ""
echo "4. 手动创建用户："
echo "   docker exec -it portfolio-postgres psql -U postgres -d portfolio_backtest"
echo "   然后执行SQL创建用户"

print_info "诊断完成！"