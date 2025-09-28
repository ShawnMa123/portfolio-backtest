#!/bin/bash
# 手动创建用户脚本

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

# 检查PostgreSQL容器是否运行
if ! docker ps | grep portfolio-postgres > /dev/null; then
    print_error "PostgreSQL容器未运行，请先启动服务"
    exit 1
fi

print_info "生成密码hash..."

# 生成正确的密码hash
PASSWORD_HASH=$(python3 -c "
import sys, os
sys.path.insert(0, '.')
from werkzeug.security import generate_password_hash
print(generate_password_hash('password123'))
")

if [ -z "$PASSWORD_HASH" ]; then
    print_error "无法生成密码hash"
    exit 1
fi

print_info "连接到PostgreSQL数据库..."

# 创建数据库和用户的SQL
SQL_COMMANDS="
-- 创建用户表（如果不存在）
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    full_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建投资标的表（如果不存在）
CREATE TABLE IF NOT EXISTS instruments (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(20) NOT NULL,
    exchange VARCHAR(50),
    currency VARCHAR(10) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建投资组合表（如果不存在）
CREATE TABLE IF NOT EXISTS portfolios (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    initial_capital DECIMAL(15,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 删除现有demo用户（如果存在）
DELETE FROM users WHERE username = 'demo';

-- 创建demo用户
-- 密码是 'password123' 的hash值
INSERT INTO users (username, email, password_hash, full_name)
VALUES (
    'demo',
    'demo@example.com',
    '$PASSWORD_HASH',
    'Demo User'
);

-- 创建示例投资标的
INSERT INTO instruments (symbol, name, type, exchange) VALUES
('SPY', 'SPDR S&P 500 ETF Trust', 'ETF', 'NYSE'),
('QQQ', 'Invesco QQQ Trust', 'ETF', 'NASDAQ'),
('VTI', 'Vanguard Total Stock Market ETF', 'ETF', 'NYSE'),
('AAPL', 'Apple Inc.', 'STOCK', 'NASDAQ'),
('MSFT', 'Microsoft Corporation', 'STOCK', 'NASDAQ')
ON CONFLICT (symbol) DO NOTHING;

-- 为demo用户创建示例投资组合
INSERT INTO portfolios (user_id, name, description, initial_capital, currency)
SELECT u.id, 'Demo Portfolio', '示例投资组合 - SPY定投策略', 10000.00, 'USD'
FROM users u WHERE u.username = 'demo'
ON CONFLICT DO NOTHING;

-- 显示创建结果
SELECT 'Users:' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'Instruments:', COUNT(*) FROM instruments
UNION ALL
SELECT 'Portfolios:', COUNT(*) FROM portfolios;

-- 显示demo用户信息
SELECT id, username, email, full_name, created_at FROM users WHERE username = 'demo';
"

print_info "执行数据库初始化SQL..."

# 执行SQL命令
docker exec -i portfolio-postgres psql -U postgres -d portfolio_backtest << EOF
$SQL_COMMANDS
EOF

if [ $? -eq 0 ]; then
    print_info "✅ 用户创建成功！"
    print_info ""
    print_info "登录信息："
    print_info "用户名: demo"
    print_info "密码: password123"
    print_info ""
    print_info "现在可以尝试登录了:"
    print_info "curl -X POST http://localhost:5000/api/auth/login -H 'Content-Type: application/json' -d '{\"username\": \"demo\", \"password\": \"password123\"}'"
else
    print_error "❌ 用户创建失败"
    exit 1
fi