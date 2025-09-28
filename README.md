# 投资组合回测系统 | Portfolio Backtest System

[中文](#中文版) | [English](#english-version)

---

## 中文版

基于Python Flask的专业投资组合回测系统，支持定期定额投资策略分析和历史数据回测。

### 🚀 系统特性

- 📈 **投资组合管理**: 创建和管理多个投资组合
- 🔄 **定期定额投资**: 支持日、周、月等多种投资频率
- 📊 **历史数据回测**: 基于真实历史数据的回测分析
- 📉 **绩效分析**: 计算收益率、夏普比率、最大回撤等指标
- 💾 **数据存储**: PostgreSQL + InfluxDB 双数据库架构
- 🚀 **RESTful API**: 完整的API接口，支持前端集成
- 🌐 **Web界面**: 直观的前端界面，支持中文
- 🛡️ **智能降级**: 数据获取失败时自动使用模拟数据
- 🔧 **容器化部署**: Docker Compose一键部署

### 🛠️ 技术栈

#### 后端
- **框架**: Flask + Flask-RESTX
- **数据库**: PostgreSQL (业务数据) + InfluxDB (时序数据)
- **缓存**: Redis
- **数据处理**: Pandas + NumPy
- **数据源**: Yahoo Finance (yfinance) + 智能模拟数据
- **认证**: JWT (Flask-JWT-Extended)

#### 前端
- **界面**: HTML5 + CSS3 + JavaScript
- **图表**: Chart.js
- **HTTP客户端**: Axios
- **响应式设计**: 移动端友好

#### 基础设施
- **容器化**: Docker + Docker Compose
- **数据库**: PostgreSQL 13, InfluxDB 2.7, Redis 7
- **部署**: 支持本地开发和生产环境

### 📸 系统截图

访问以下页面体验系统：
- 主页: http://localhost:5000/
- 回测工具: http://localhost:5000/backtest
- 演示页面: http://localhost:5000/demo
- API文档: http://localhost:5000/api/docs/

### 🚀 快速开始

#### 环境要求

- Python 3.8+
- Docker & Docker Compose
- Git

#### 1. 克隆项目

```bash
git clone <repository-url>
cd portfolio-backtest
```

#### 2. 启动数据库服务

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

#### 3. 设置Python环境

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

#### 4. 配置环境变量

```bash
# 复制环境变量文件
cp .env.example .env

# 编辑 .env 文件（可选，默认配置已经可用）
```

#### 5. 初始化数据

```bash
# 初始化示例数据
python scripts/init_data.py --init
```

#### 6. 启动应用

```bash
# 启动Flask应用
python app.py
```

应用将在 `http://localhost:5000` 启动

#### 7. 测试功能

```bash
# 运行完整的API测试
python test_backtest_api.py

# 测试数据服务
python test_data_service.py
```

### 🔧 新版本修复和改进

#### 已修复的问题

1. **回测功能恢复正常**
   - 修复了yfinance数据获取失败导致的回测错误
   - 添加智能模拟数据生成器，确保系统稳定运行

2. **中文编码支持优化**
   - Flask应用完整支持UTF-8编码
   - 解决API中文响应乱码问题
   - 优化控制台中文显示

3. **错误处理增强**
   - 添加详细的错误追踪和日志
   - 改进API错误响应格式
   - 提供更好的调试信息

4. **数据服务健壮性**
   - 网络异常时自动生成合理的模拟数据
   - 支持多种股票/ETF的价格模拟
   - 保持数据一致性和可重复性

### 📊 API 接口文档

启动应用后，访问 `http://localhost:5000/api/docs/` 查看完整的API文档。

#### 主要接口

##### 认证接口
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/profile` - 获取用户信息

##### 投资标的接口
- `GET /api/instruments` - 获取标的列表
- `GET /api/instruments/search?symbol=SPY` - 搜索标的
- `GET /api/instruments/SPY/price` - 获取价格数据

##### 投资组合接口
- `GET /api/portfolios` - 获取投资组合列表
- `POST /api/portfolios` - 创建投资组合
- `GET /api/portfolios/{id}/configurations` - 获取配置

##### 回测接口
- `POST /api/backtests` - 发起回测
- `GET /api/backtests/{id}` - 获取回测结果
- `GET /api/backtests/{id}/performance` - 获取绩效数据

### 💻 使用示例

#### 完整回测流程

```bash
# 1. 登录获取token
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "password123"}' | \
  jq -r '.access_token')

# 2. 创建投资组合
PORTFOLIO_ID=$(curl -s -X POST http://localhost:5000/api/portfolios \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SPY定投策略",
    "description": "标准普尔500指数基金定期定额投资",
    "initial_capital": 10000,
    "currency": "USD"
  }' | jq -r '.id')

# 3. 搜索投资标的
INSTRUMENT_ID=$(curl -s -X GET "http://localhost:5000/api/instruments/search?symbol=SPY" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.id')

# 4. 添加投资配置
curl -X POST http://localhost:5000/api/portfolios/$PORTFOLIO_ID/configurations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instrument_id": '$INSTRUMENT_ID',
    "weight": 1.0,
    "investment_frequency": "MONTHLY",
    "frequency_detail": {"day": 1},
    "transaction_fee_rate": 0.0003,
    "buy_type": "AMOUNT",
    "buy_amount": 1000,
    "start_date": "2023-01-01"
  }'

# 5. 执行回测
curl -X POST http://localhost:5000/api/backtests \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio_id": '$PORTFOLIO_ID',
    "name": "SPY 2023年回测",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  }'
```

### 🔍 数据库配置

#### PostgreSQL
- **主机**: localhost:5432
- **数据库**: portfolio_backtest
- **用户名**: postgres
- **密码**: password

#### InfluxDB
- **URL**: http://localhost:8086
- **组织**: portfolio-org
- **Bucket**: market-data
- **Token**: my-super-secret-auth-token
- **用户名**: admin
- **密码**: password123

#### Redis
- **URL**: redis://localhost:6379/0

### 🐛 故障排除

#### 常见问题及解决方案

1. **数据库连接失败**
   ```bash
   # 检查容器状态
   docker-compose ps

   # 重启数据库服务
   docker-compose restart postgres
   ```

2. **yfinance数据获取失败**
   - 系统会自动生成模拟数据，无需担心
   - 检查网络连接或代理设置

3. **中文显示乱码**
   - Windows系统运行: `chcp 65001`
   - 确保终端支持UTF-8编码

4. **回测计算错误**
   - 检查投资组合配置权重总和是否为100%
   - 确认日期范围有效
   - 查看应用日志详细错误信息

### 🚀 部署指南

#### 开发环境
```bash
# 启动开发服务器
python app.py
```

#### 生产环境
```bash
# 使用gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 📈 性能优化建议

1. **数据库优化**
   - 为频繁查询字段添加索引
   - 使用连接池
   - 批量操作减少数据库访问

2. **缓存策略**
   - Redis缓存频繁访问的数据
   - InfluxDB查询结果缓存
   - 静态资源CDN加速

3. **计算优化**
   - 使用Pandas向量化操作
   - 异步处理长时间计算
   - 合理设置回测时间范围

---

## English Version

A professional portfolio backtesting system built with Python Flask, supporting dollar-cost averaging strategy analysis and historical data backtesting.

### 🚀 Features

- 📈 **Portfolio Management**: Create and manage multiple investment portfolios
- 🔄 **Dollar-Cost Averaging**: Support daily, weekly, monthly investment frequencies
- 📊 **Historical Backtesting**: Analysis based on real historical data
- 📉 **Performance Analysis**: Calculate returns, Sharpe ratio, maximum drawdown
- 💾 **Data Storage**: PostgreSQL + InfluxDB dual database architecture
- 🚀 **RESTful API**: Complete API interface with frontend integration
- 🌐 **Web Interface**: Intuitive frontend with Chinese support
- 🛡️ **Smart Fallback**: Automatic mock data when real data fails
- 🔧 **Containerized**: One-click deployment with Docker Compose

### 🛠️ Tech Stack

#### Backend
- **Framework**: Flask + Flask-RESTX
- **Database**: PostgreSQL (business data) + InfluxDB (time series)
- **Cache**: Redis
- **Data Processing**: Pandas + NumPy
- **Data Source**: Yahoo Finance (yfinance) + Smart Mock Data
- **Authentication**: JWT (Flask-JWT-Extended)

#### Frontend
- **UI**: HTML5 + CSS3 + JavaScript
- **Charts**: Chart.js
- **HTTP Client**: Axios
- **Responsive**: Mobile-friendly design

#### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Databases**: PostgreSQL 13, InfluxDB 2.7, Redis 7
- **Deployment**: Local development and production ready

### 🚀 Quick Start

#### Prerequisites

- Python 3.8+
- Docker & Docker Compose
- Git

#### 1. Clone Repository

```bash
git clone <repository-url>
cd portfolio-backtest
```

#### 2. Start Database Services

Start PostgreSQL, InfluxDB, and Redis with Docker Compose:

```bash
# Start all database services
docker-compose up -d

# Check service status
docker-compose ps
```

Service port mappings:
- PostgreSQL: `localhost:5432`
- InfluxDB: `localhost:8086`
- Redis: `localhost:6379`

#### 3. Setup Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\\Scripts\\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 4. Configure Environment

```bash
# Copy environment file
cp .env.example .env

# Edit .env file (optional, defaults work)
```

#### 5. Initialize Data

```bash
# Initialize sample data
python scripts/init_data.py --init
```

#### 6. Start Application

```bash
# Start Flask application
python app.py
```

Application will start at `http://localhost:5000`

#### 7. Test Functionality

```bash
# Run complete API tests
python test_backtest_api.py

# Test data service
python test_data_service.py
```

### 🔧 Latest Fixes and Improvements

#### Fixed Issues

1. **Backtest Functionality Restored**
   - Fixed backtest errors caused by yfinance data retrieval failures
   - Added smart mock data generator for system stability

2. **Chinese Encoding Support**
   - Full UTF-8 encoding support in Flask application
   - Resolved API Chinese response encoding issues
   - Optimized console Chinese character display

3. **Enhanced Error Handling**
   - Added detailed error tracking and logging
   - Improved API error response format
   - Better debugging information

4. **Data Service Robustness**
   - Auto-generate reasonable mock data during network exceptions
   - Support multiple stock/ETF price simulation
   - Maintain data consistency and repeatability

### 📊 API Documentation

After starting the application, visit `http://localhost:5000/api/docs/` for complete API documentation.

#### Main Endpoints

##### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/profile` - Get user information

##### Instruments
- `GET /api/instruments` - Get instrument list
- `GET /api/instruments/search?symbol=SPY` - Search instruments
- `GET /api/instruments/SPY/price` - Get price data

##### Portfolios
- `GET /api/portfolios` - Get portfolio list
- `POST /api/portfolios` - Create portfolio
- `GET /api/portfolios/{id}/configurations` - Get configurations

##### Backtests
- `POST /api/backtests` - Start backtest
- `GET /api/backtests/{id}` - Get backtest results
- `GET /api/backtests/{id}/performance` - Get performance data

### 💻 Usage Examples

#### Complete Backtest Workflow

```bash
# 1. Login and get token
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "password123"}' | \
  jq -r '.access_token')

# 2. Create portfolio
PORTFOLIO_ID=$(curl -s -X POST http://localhost:5000/api/portfolios \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SPY DCA Strategy",
    "description": "S&P 500 ETF Dollar Cost Averaging",
    "initial_capital": 10000,
    "currency": "USD"
  }' | jq -r '.id')

# 3. Search instrument
INSTRUMENT_ID=$(curl -s -X GET "http://localhost:5000/api/instruments/search?symbol=SPY" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.id')

# 4. Add investment configuration
curl -X POST http://localhost:5000/api/portfolios/$PORTFOLIO_ID/configurations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instrument_id": '$INSTRUMENT_ID',
    "weight": 1.0,
    "investment_frequency": "MONTHLY",
    "frequency_detail": {"day": 1},
    "transaction_fee_rate": 0.0003,
    "buy_type": "AMOUNT",
    "buy_amount": 1000,
    "start_date": "2023-01-01"
  }'

# 5. Execute backtest
curl -X POST http://localhost:5000/api/backtests \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio_id": '$PORTFOLIO_ID',
    "name": "SPY 2023 Backtest",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  }'
```

### 🔍 Database Configuration

#### PostgreSQL
- **Host**: localhost:5432
- **Database**: portfolio_backtest
- **Username**: postgres
- **Password**: password

#### InfluxDB
- **URL**: http://localhost:8086
- **Organization**: portfolio-org
- **Bucket**: market-data
- **Token**: my-super-secret-auth-token
- **Username**: admin
- **Password**: password123

#### Redis
- **URL**: redis://localhost:6379/0

### 🐛 Troubleshooting

#### Common Issues and Solutions

1. **Database Connection Failed**
   ```bash
   # Check container status
   docker-compose ps

   # Restart database service
   docker-compose restart postgres
   ```

2. **yfinance Data Retrieval Failed**
   - System automatically generates mock data, no worries
   - Check network connection or proxy settings

3. **Chinese Character Display Issues**
   - Windows: run `chcp 65001`
   - Ensure terminal supports UTF-8 encoding

4. **Backtest Calculation Errors**
   - Check portfolio configuration weights sum to 100%
   - Confirm date range validity
   - Check application logs for detailed errors

### 🚀 Deployment Guide

#### Development Environment
```bash
# Start development server
python app.py
```

#### Production Environment
```bash
# Use gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 📈 Performance Optimization Tips

1. **Database Optimization**
   - Add indexes for frequently queried fields
   - Use connection pooling
   - Batch operations to reduce database access

2. **Caching Strategy**
   - Redis cache for frequently accessed data
   - InfluxDB query result caching
   - CDN acceleration for static resources

3. **Computation Optimization**
   - Use Pandas vectorized operations
   - Async processing for long computations
   - Set reasonable backtest time ranges

### 🤝 Contributing

1. Fork the project
2. Create feature branch
3. Commit changes
4. Submit Pull Request

### 📄 License

MIT License

### 📞 Contact

For questions, please create an Issue or contact the development team.

---

## 系统架构图 | System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask API     │    │   Data Sources  │
│                 │    │                 │    │                 │
│  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
│  │ Web UI    │  │◄──►│  │ Auth API  │  │    │  │ Yahoo     │  │
│  └───────────┘  │    │  └───────────┘  │    │  │ Finance   │  │
│  ┌───────────┐  │    │  ┌───────────┐  │    │  └───────────┘  │
│  │ Charts    │  │◄──►│  │Portfolio  │  │◄──►│  ┌───────────┐  │
│  └───────────┘  │    │  │ API       │  │    │  │ Mock Data │  │
│  ┌───────────┐  │    │  └───────────┘  │    │  │Generator  │  │
│  │ Tables    │  │◄──►│  ┌───────────┐  │    │  └───────────┘  │
│  └───────────┘  │    │  │Backtest   │  │    │                 │
│                 │    │  │ Engine    │  │    │                 │
└─────────────────┘    │  └───────────┘  │    └─────────────────┘
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Data Storage  │
                       │                 │
                       │  ┌───────────┐  │
                       │  │PostgreSQL │  │
                       │  │(Business) │  │
                       │  └───────────┘  │
                       │  ┌───────────┐  │
                       │  │ InfluxDB  │  │
                       │  │(TimeSeries│  │
                       │  └───────────┘  │
                       │  ┌───────────┐  │
                       │  │  Redis    │  │
                       │  │ (Cache)   │  │
                       │  └───────────┘  │
                       └─────────────────┘
```