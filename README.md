# 📈 投资组合回测系统

一个功能完整的投资组合回测系统，支持WARP代理池、异步任务处理和多种投资策略分析。

## ✨ 功能特点

- 🚀 **异步回测处理**: 基于Celery的分布式任务队列
- 🌐 **WARP代理池**: 5个代理节点轮询，避免API限制
- 📊 **多种投资策略**: 定投、价值平均法等策略支持
- 💰 **费用计算**: 精确的交易费用和税费计算
- 📈 **性能分析**: 收益率、夏普比率、最大回撤等指标
- 🔄 **实时数据**: 集成Yahoo Finance API获取最新市场数据
- 📝 **结构化日志**: JSON格式日志，便于监控和分析
- 🛡️ **全局异常处理**: 统一的错误处理和恢复机制

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Flask Web API │    │   Celery Tasks  │    │   WARP Proxies  │
│   + SQLAlchemy  │────│   + Redis Queue │────│     (5 nodes)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │
│   (用户数据)     │    │   (任务队列)     │
└─────────────────┘    └─────────────────┘
```

## 📋 系统要求

### 开发环境
- Python 3.9+
- Docker & Docker Compose
- PostgreSQL 13+
- Redis 7+

### 生产环境
- **最低配置**: 2核CPU, 4GB内存, 20GB存储
- **推荐配置**: 4核CPU, 8GB内存, 50GB SSD存储
- Ubuntu 20.04+ / CentOS 8+ / RHEL 8+

## 🚀 快速开始

### 方案1: 完全Docker化部署 (推荐)

**一键部署，包含所有服务**

```bash
# 克隆项目
git clone <your-repo-url> portfolio-backtest
cd portfolio-backtest

# 如果Docker Compose未安装（仅Debian/Ubuntu）
./install-docker-compose.sh

# 一键部署（包含应用、数据库、Redis、WARP代理池）
./deploy.sh --full
```

访问地址：
- 应用主页: http://localhost:5000
- API文档: http://localhost:5000/api/docs/
- 健康检查: http://localhost:5000/health

### 方案2: 混合部署

**Docker中间件 + Python手动启动**

```bash
# 1. 启动中间件（数据库、Redis、代理池）
./deploy.sh --hybrid

# 2. 配置Python环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 复制环境配置
cp .env.hybrid .env

# 5. 启动Celery Worker（新终端）
python scripts/celery_worker.py

# 6. 启动Flask应用
python app.py
```

### 管理命令

```bash
# 查看服务状态
./deploy.sh --status

# 查看日志
./deploy.sh --logs

# 停止所有服务
./deploy.sh --stop

# 清理所有数据（谨慎使用）
./deploy.sh --clean
```

### 自动化特性

✅ **自动数据库初始化**: 容器启动时自动创建表和示例数据
✅ **自动代理池配置**: WARP代理自动注册和健康检查
✅ **自动服务依赖**: 正确的启动顺序和健康检查
✅ **自动错误恢复**: 服务异常时自动重启

## 📖 使用指南

### API文档

启动应用后访问: `http://localhost:5000/api/docs/`

### 创建回测任务

```bash
# 1. 用户登录
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "password123"}'

# 2. 创建投资组合
curl -X POST http://localhost:5000/api/portfolios \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试组合",
    "description": "定投SPY策略",
    "initial_capital": 10000,
    "currency": "USD"
  }'

# 3. 配置投资策略
curl -X POST http://localhost:5000/api/portfolios/{portfolio_id}/configurations \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "instrument_id": 1,
    "weight": 1.0,
    "investment_frequency": "MONTHLY",
    "frequency_detail": {"day": 1},
    "transaction_fee_rate": 0.0003,
    "buy_type": "AMOUNT",
    "buy_amount": 1000,
    "start_date": "2023-01-01"
  }'

# 4. 启动回测
curl -X POST http://localhost:5000/api/backtests \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio_id": 1,
    "name": "2023年定投回测",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  }'
```

### 监控任务状态

```bash
# 查看回测状态
curl -X GET http://localhost:5000/api/backtests/{backtest_id}/status \
  -H "Authorization: Bearer <your_token>"

# 获取回测结果
curl -X GET http://localhost:5000/api/backtests/{backtest_id}/results \
  -H "Authorization: Bearer <your_token>"
```

## 📁 项目结构

```
portfolio-backtest/
├── app/                    # 应用核心代码
│   ├── models/            # SQLAlchemy数据模型
│   ├── services/          # 业务逻辑服务
│   ├── tasks/             # Celery异步任务
│   ├── utils/             # 工具类和异常处理
│   └── routes/            # API路由定义
├── scripts/               # 部署和管理脚本
│   ├── deploy.py          # 生产环境部署
│   ├── monitor.py         # 系统监控
│   ├── celery_worker.py   # Celery Worker启动
│   └── init_data.py       # 数据库初始化
├── tests/                 # 测试文件
│   ├── test_backtest.py   # 回测功能测试
│   ├── test_data_service.py # 数据服务测试
│   └── test_warp_proxy.py # 代理池测试
├── docs/                  # 文档目录
│   └── DEPLOYMENT.md      # 部署文档
├── logs/                  # 日志文件
├── docker-compose.warp.yml # WARP代理配置
├── requirements.txt       # Python依赖
└── .env                   # 环境配置
```

## 🛠️ 开发指南

### 添加新的投资策略

1. 在 `app/services/backtest_service.py` 中扩展策略逻辑
2. 更新 `app/models/backtest.py` 中的配置模型
3. 添加相应的API端点和测试

### 扩展数据源

1. 在 `app/services/data_service.py` 中添加新的数据提供商
2. 实现统一的数据接口
3. 配置代理池支持

### 自定义性能指标

1. 扩展 `app/services/performance_analyzer.py`
2. 添加新的计算方法
3. 更新报告生成逻辑

## 🚀 生产部署

### 推荐：完全Docker化部署

```bash
# 克隆到生产服务器
git clone <your-repo-url> portfolio-backtest
cd portfolio-backtest

# 修改生产环境配置
nano .env.docker  # 修改密钥、API Key等

# 一键部署
./deploy.sh --full

# 查看状态
./deploy.sh --status
```

### 可选：混合部署

适合需要Python环境调试的场景：

```bash
# 启动中间件
./deploy.sh --hybrid

# 配置Python环境并启动应用
cp .env.hybrid .env
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/celery_worker.py &
python app.py
```

### 系统监控

```bash
# 查看所有服务状态
./deploy.sh --status

# 实时查看日志
./deploy.sh --logs

# 内置监控（完全Docker化部署）
# 监控服务会自动启动，每5分钟检查一次
docker logs portfolio-monitor
```

## 🔧 故障排除

### 常见问题

1. **Docker Compose未安装（Debian/Ubuntu）**
   ```bash
   # 自动安装Docker Compose
   ./install-docker-compose.sh

   # 或手动安装
   sudo apt update
   sudo apt install docker-compose-plugin
   # 或传统版本: sudo apt install docker-compose
   ```

2. **模块导入错误 (ModuleNotFoundError: No module named 'app')**
   ```bash
   # 确保在项目根目录执行脚本
   cd /path/to/portfolio-backtest
   python scripts/celery_worker.py

   # 或使用绝对路径
   cd /path/to/portfolio-backtest && python scripts/celery_worker.py
   ```

3. **WARP代理连接失败**
   ```bash
   # 重启代理池
   ./deploy.sh --stop
   ./deploy.sh --full

   # 检查代理状态
   ./deploy.sh --logs
   ```

4. **数据库连接问题**
   ```bash
   # 测试数据库连接
   psql $DATABASE_URL

   # 检查连接配置
   echo $DATABASE_URL
   ```

5. **Redis连接问题**
   ```bash
   # 查看服务状态
   ./deploy.sh --status

   # 重启所有服务
   ./deploy.sh --stop
   ./deploy.sh --full
   ```

6. **内存不足**
   ```bash
   # 查看系统资源
   free -h
   docker stats

   # 清理Docker资源
   docker system prune -a
   ```

### 日志分析

```bash
# 应用日志
tail -f logs/app.jsonl

# Celery任务日志
tail -f logs/celery.jsonl

# 错误日志
tail -f logs/error.jsonl

# WARP代理日志
docker logs -f warp-proxy-1
```

## 📊 性能优化

### 代理池优化

- 根据API调用频率调整代理数量
- 优化健康检查间隔
- 配置适当的请求限流

### 数据库优化

- 添加适当的索引
- 配置连接池
- 定期清理过期数据

### 缓存策略

- Redis缓存热点数据
- 配置合理的TTL
- 实现缓存预热

## 🤝 贡献指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/new-feature`)
3. 提交更改 (`git commit -am 'Add new feature'`)
4. 推送分支 (`git push origin feature/new-feature`)
5. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 📞 支持

- **文档**: 查看 `docs/` 目录
- **日志**: 检查 `logs/` 目录
- **监控**: 使用 `scripts/monitor.py`
- **问题**: 创建GitHub Issue

---

**开始您的投资回测之旅！** 🚀