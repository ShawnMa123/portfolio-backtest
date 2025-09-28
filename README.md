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

### 1. 克隆项目

```bash
git clone <your-repo-url> portfolio-backtest
cd portfolio-backtest
```

### 2. 环境配置

```bash
# 创建虚拟环境
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑配置文件
nano .env
```

**重要配置项:**
```bash
# 数据库配置
DATABASE_URL=postgresql://username:password@localhost:5432/portfolio_backtest

# Redis配置
REDIS_URL=redis://localhost:6379/0
PROXY_POOL_REDIS_URL=redis://localhost:6380/0

# API密钥
ALPHA_VANTAGE_API_KEY=your_api_key_here

# 代理池配置
USE_PROXY_POOL=true
PROXY_RATE_LIMIT=1.5
```

### 4. 启动WARP代理池

```bash
# 启动5个WARP代理实例
docker-compose -f docker-compose.warp.yml up -d

# 等待代理初始化 (约2分钟)
sleep 120

# 验证代理状态
docker ps | grep warp-proxy
```

### 5. 初始化数据库

```bash
# 创建数据库表
python scripts/init_data.py
```

### 6. 启动服务

**开发环境:**
```bash
# 启动Celery Worker (新终端)
# 注意：确保在项目根目录执行
cd /path/to/portfolio-backtest
python scripts/celery_worker.py

# 启动Flask应用
python app.py
```

**生产环境:**
```bash
# 使用部署脚本
python scripts/deploy.py --env production

# 或手动启动
nohup python scripts/celery_worker.py > logs/celery.log 2>&1 &
nohup python app.py > logs/app.log 2>&1 &
```

### 7. 验证安装

```bash
# 测试应用健康状态
curl http://localhost:5000/health

# 测试代理池
curl http://localhost:5000/api/proxy/test

# 访问API文档
# 浏览器打开: http://localhost:5000/api/docs/
```

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

### 自动部署

```bash
# 一键部署到生产环境
python scripts/deploy.py --env production
```

### 手动部署

详细的手动部署步骤请参考: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

### 系统监控

```bash
# 实时监控
python scripts/monitor.py --monitor

# 健康检查
python scripts/monitor.py

# 告警检查
python scripts/monitor.py --alert
```

## 🔧 故障排除

### 常见问题

1. **模块导入错误 (ModuleNotFoundError: No module named 'app')**
   ```bash
   # 确保在项目根目录执行脚本
   cd /path/to/portfolio-backtest
   python scripts/celery_worker.py

   # 或使用绝对路径
   cd /path/to/portfolio-backtest && python scripts/celery_worker.py
   ```

2. **WARP代理连接失败**
   ```bash
   # 重启代理池
   docker-compose -f docker-compose.warp.yml restart

   # 检查代理状态
   docker logs warp-proxy-1
   ```

3. **数据库连接问题**
   ```bash
   # 测试数据库连接
   psql $DATABASE_URL

   # 检查连接配置
   echo $DATABASE_URL
   ```

4. **Redis连接问题**
   ```bash
   # 测试Redis连接
   redis-cli -u $REDIS_URL ping

   # 检查Celery队列
   celery -A app.tasks inspect active
   ```

5. **内存不足**
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