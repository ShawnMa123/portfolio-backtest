# ETF/股票回测与策略监控系统

基于Python Flask的投资组合回测系统，支持定期定额投资策略分析和历史数据回测。

## 系统特性

- 📈 **投资组合管理**: 创建和管理多个投资组合
- 🔄 **定期定额投资**: 支持日、周、月等多种投资频率
- 📊 **历史数据回测**: 基于真实历史数据的回测分析
- 📉 **绩效分析**: 计算收益率、夏普比率、最大回撤等指标
- 💾 **数据存储**: PostgreSQL + InfluxDB 双数据库架构
- 🚀 **RESTful API**: 完整的API接口，支持前端集成

## 技术栈

### 后端
- **框架**: Flask + Flask-RESTX
- **数据库**: PostgreSQL (业务数据) + InfluxDB (时序数据)
- **缓存**: Redis
- **数据处理**: Pandas + NumPy
- **数据源**: Yahoo Finance (yfinance)

### 数据库设计
- **PostgreSQL**: 用户、投资组合、回测结果等业务数据
- **InfluxDB**: 历史价格数据、投资组合快照等时序数据
- **Redis**: 缓存和会话管理

## 快速开始

### 环境要求

- Python 3.8+
- Docker & Docker Compose
- Git

### 1. 克隆项目

```bash
git clone <repository-url>
cd portfolio-backtest
```

### 2. 启动数据库服务

使用Docker Compose启动PostgreSQL、InfluxDB和Redis：

```bash
# 启动所有数据库服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

服务端口映射：
- PostgreSQL: `localhost:5432`
- InfluxDB: `localhost:8086`
- Redis: `localhost:6379`

### 3. 设置Python环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\\Scripts\\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制环境变量文件
cp .env.example .env

# 编辑 .env 文件（可选，默认配置已经可用）
```

### 5. 初始化数据

```bash
# 初始化示例数据
python scripts/init_data.py --init

# 同步历史数据（可选，需要时间较长）
python scripts/init_data.py --sync
```

### 6. 启动应用

```bash
# 启动Flask应用
python app.py
```

应用将在 `http://localhost:5000` 启动

### 7. 测试API

```bash
# 运行API测试
python test_api.py
```

## 数据库连接信息

### PostgreSQL
- **主机**: localhost:5432
- **数据库**: portfolio_backtest
- **用户名**: postgres
- **密码**: password

### InfluxDB
- **URL**: http://localhost:8086
- **组织**: portfolio-org
- **Bucket**: market-data
- **Token**: my-super-secret-auth-token
- **用户名**: admin
- **密码**: password123

### Redis
- **URL**: redis://localhost:6379/0

## API 接口文档

启动应用后，访问 `http://localhost:5000/api/docs/` 查看完整的API文档。

### 主要接口

#### 认证接口
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/profile` - 获取用户信息

#### 投资标的接口
- `GET /api/instruments` - 获取标的列表
- `GET /api/instruments/search?symbol=SPY` - 搜索标的
- `GET /api/instruments/SPY/price` - 获取价格数据

#### 投资组合接口
- `GET /api/portfolios` - 获取投资组合列表
- `POST /api/portfolios` - 创建投资组合
- `GET /api/portfolios/{id}/configurations` - 获取配置

#### 回测接口
- `POST /api/backtests` - 发起回测
- `GET /api/backtests/{id}` - 获取回测结果
- `GET /api/backtests/{id}/performance` - 获取绩效数据

## 示例用法

### 1. 用户登录

```bash
curl -X POST http://localhost:5000/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username": "demo", "password": "password123"}'
```

### 2. 创建投资组合

```bash
curl -X POST http://localhost:5000/api/portfolios \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "我的投资组合",
    "description": "定期定额投资SPY",
    "initial_capital": 10000.00,
    "currency": "USD"
  }'
```

### 3. 添加投资配置

```bash
curl -X POST http://localhost:5000/api/portfolios/1/configurations \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "instrument_id": 1,
    "investment_frequency": "MONTHLY",
    "frequency_detail": {"day": 1},
    "buy_type": "AMOUNT",
    "buy_amount": 1000.00,
    "start_date": "2023-01-01"
  }'
```

### 4. 发起回测

```bash
curl -X POST http://localhost:5000/api/backtests \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "portfolio_id": 1,
    "name": "2023年回测",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  }'
```

## 本地开发调试

### 查看数据库数据

#### PostgreSQL
```bash
# 连接到PostgreSQL
docker exec -it portfolio-postgres psql -U postgres -d portfolio_backtest

# 查看用户表
\\dt
SELECT * FROM users;
SELECT * FROM portfolios;
```

#### InfluxDB
访问 `http://localhost:8086` 登录InfluxDB Web界面：
- 用户名: admin
- 密码: password123

#### Redis
```bash
# 连接到Redis
docker exec -it portfolio-redis redis-cli

# 查看所有key
KEYS *
```

### 调试技巧

#### 1. 查看应用日志
Flask应用运行时会在控制台显示详细日志，包括API请求和数据库查询。

#### 2. 数据库连接测试
```python
# 测试PostgreSQL连接
from app import create_app, db
app = create_app()
with app.app_context():
    try:
        db.engine.execute('SELECT 1')
        print("PostgreSQL连接成功")
    except Exception as e:
        print(f"PostgreSQL连接失败: {e}")
```

#### 3. InfluxDB连接测试
```python
from app.services.data_service import DataService
data_service = DataService()
try:
    # 测试获取数据
    data = data_service.get_price_data('SPY', '2023-01-01', '2023-01-31')
    print(f"InfluxDB连接成功，获取到 {len(data)} 条数据")
except Exception as e:
    print(f"InfluxDB连接失败: {e}")
```

### 常见问题

#### 1. 数据库连接失败
- 确保Docker服务正在运行：`docker-compose ps`
- 检查端口是否被占用：`netstat -an | findstr 5432`
- 重启数据库服务：`docker-compose restart postgres`

#### 2. InfluxDB Token错误
- 查看InfluxDB容器日志：`docker logs portfolio-influxdb`
- 重新初始化InfluxDB：`docker-compose down -v && docker-compose up -d`

#### 3. Yahoo Finance数据获取失败
- 检查网络连接
- 某些地区可能需要设置代理
- 数据源偶尔不稳定，可以重试

#### 4. 回测计算错误
- 确保投资组合配置正确
- 检查日期范围是否有效
- 查看应用日志中的详细错误信息

### 性能优化

#### 1. 数据库查询优化
- 确保经常查询的字段有索引
- 使用连接池减少连接开销
- 批量操作减少数据库往返

#### 2. 历史数据缓存
- InfluxDB自动缓存查询结果
- Redis缓存频繁访问的数据
- 定期清理过期缓存

#### 3. 回测性能优化
- 向量化计算使用Pandas
- 避免循环中的数据库查询
- 使用异步任务处理长时间计算

## 开发指南

### 添加新的投资标的

1. 在数据库中添加标的信息
2. 使用DataService同步历史数据
3. 配置投资策略

### 扩展回测策略

1. 修改 `BacktestEngine.should_buy_today()` 方法
2. 添加新的买入条件逻辑
3. 更新配置模型支持新参数

### 添加新的绩效指标

1. 在 `BacktestEngine._calculate_performance_metrics()` 中添加计算逻辑
2. 更新API返回模型
3. 扩展前端展示

## 部署说明

### 生产环境部署

1. 修改 `.env` 文件中的生产配置
2. 使用 `docker-compose.prod.yml`
3. 配置Nginx反向代理
4. 设置SSL证书
5. 配置监控和日志

### 数据备份

```bash
# PostgreSQL备份
docker exec portfolio-postgres pg_dump -U postgres portfolio_backtest > backup.sql

# InfluxDB备份
docker exec portfolio-influxdb influx backup /tmp/backup
docker cp portfolio-influxdb:/tmp/backup ./influx_backup/
```

## 贡献指南

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 发起Pull Request

## 许可证

MIT License

## 联系方式

如有问题，请创建Issue或联系开发团队。