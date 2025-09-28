# 🚀 快速开始指南

## 方案1: 一键Docker部署 (推荐)

**3分钟完成部署，包含所有服务**

```bash
# 1. 克隆项目
git clone <your-repo-url> portfolio-backtest
cd portfolio-backtest

# 2. 安装Docker Compose（如果需要）
./install-docker-compose.sh  # Debian/Ubuntu自动安装

# 3. 一键部署
./deploy.sh --full     # Linux/Mac
# deploy.bat --full    # Windows

# 4. 验证部署
curl http://localhost:5000/health
```

**访问地址:**
- 🌐 应用主页: http://localhost:5000
- 📚 API文档: http://localhost:5000/api/docs/
- ❤️ 健康检查: http://localhost:5000/health

## 方案2: 混合部署

**Docker中间件 + Python手动启动**

```bash
# 1. 启动中间件
./deploy.sh --hybrid

# 2. 配置Python环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
cp .env.hybrid .env

# 3. 启动应用 (两个终端)
# 终端1:
python scripts/celery_worker.py

# 终端2:
python app.py
```

## 🎯 测试API

```bash
# 1. 用户登录
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "password123"}'

# 保存返回的token
export TOKEN="your_token_here"

# 2. 查看投资组合
curl -X GET http://localhost:5000/api/portfolios \
  -H "Authorization: Bearer $TOKEN"

# 3. 启动回测
curl -X POST http://localhost:5000/api/backtests \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio_id": 1,
    "name": "测试回测",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  }'
```

## 🔧 管理命令

```bash
# 查看状态
./deploy.sh --status

# 查看日志
./deploy.sh --logs

# 停止服务
./deploy.sh --stop

# 清理数据（危险）
./deploy.sh --clean
```

## 📊 默认数据

系统会自动创建:
- **用户**: demo / password123
- **投资组合**: Demo Portfolio (SPY定投策略)
- **投资标的**: SPY, QQQ, VTI, AAPL, MSFT

## 🆘 故障排除

### Docker Compose未安装（Debian/Ubuntu）
```bash
# 自动安装
./install-docker-compose.sh

# 验证安装
docker compose version  # 或 docker-compose --version
```

### 端口占用
```bash
# 检查端口占用
netstat -tlpn | grep -E ":(5000|5432|6379)"

# 停止冲突服务
./deploy.sh --stop
```

### 容器无法启动
```bash
# 查看详细日志
./deploy.sh --logs

# 重新构建和部署
./deploy.sh --stop
./deploy.sh --full
```

### WARP代理问题
```bash
# 检查WARP容器
docker ps | grep warp

# 重启代理
docker restart warp-proxy-1

# 测试代理连接
curl --proxy socks5://localhost:40001 https://httpbin.org/ip
```

## 🔗 相关链接

- 📖 [完整文档](README.md)
- 🏗️ [部署指南](docs/DEPLOYMENT.md)
- 🐛 [问题报告](https://github.com/your-repo/issues)

---

**开始您的投资回测之旅！** 🚀