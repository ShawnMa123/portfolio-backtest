#!/usr/bin/env python3
"""
Docker容器初始化脚本
用于在容器内自动初始化数据库和示例数据
"""

import os
import sys
import time
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, '/app')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def wait_for_database():
    """等待数据库可用"""
    logger.info("等待数据库连接...")
    max_retries = 30
    retry_count = 0

    while retry_count < max_retries:
        try:
            from app import create_app, db
            app = create_app()
            with app.app_context():
                # 使用新的SQLAlchemy语法
                with db.engine.connect() as conn:
                    conn.execute(db.text('SELECT 1'))
            logger.info("数据库连接成功")
            return True
        except Exception as e:
            retry_count += 1
            logger.warning(f"数据库连接失败 ({retry_count}/{max_retries}): {e}")
            time.sleep(2)

    logger.error("数据库连接超时")
    return False

def wait_for_redis():
    """等待Redis可用"""
    logger.info("等待Redis连接...")
    max_retries = 30
    retry_count = 0

    while retry_count < max_retries:
        try:
            import redis
            redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            logger.info("Redis连接成功")
            return True
        except Exception as e:
            retry_count += 1
            logger.warning(f"Redis连接失败 ({retry_count}/{max_retries}): {e}")
            time.sleep(2)

    logger.error("Redis连接超时")
    return False

def initialize_database():
    """初始化数据库"""
    logger.info("初始化数据库...")

    try:
        from app import create_app, db
        from app.models import User, Instrument, Portfolio, PortfolioConfiguration
        from datetime import date

        app = create_app()
        with app.app_context():
            # 创建数据库表
            db.create_all()
            logger.info("数据库表创建成功")

            # 创建示例用户
            if not User.query.filter_by(username='demo').first():
                demo_user = User(
                    username='demo',
                    email='demo@example.com',
                    full_name='Demo User'
                )
                demo_user.set_password('password123')
                db.session.add(demo_user)
                db.session.commit()
                logger.info("创建示例用户: demo / password123")

            # 创建示例投资标的
            sample_instruments = [
                {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF Trust', 'type': 'ETF', 'exchange': 'NYSE'},
                {'symbol': 'QQQ', 'name': 'Invesco QQQ Trust', 'type': 'ETF', 'exchange': 'NASDAQ'},
                {'symbol': 'VTI', 'name': 'Vanguard Total Stock Market ETF', 'type': 'ETF', 'exchange': 'NYSE'},
                {'symbol': 'AAPL', 'name': 'Apple Inc.', 'type': 'STOCK', 'exchange': 'NASDAQ'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'type': 'STOCK', 'exchange': 'NASDAQ'},
            ]

            for inst_data in sample_instruments:
                if not Instrument.query.filter_by(symbol=inst_data['symbol']).first():
                    instrument = Instrument(**inst_data)
                    db.session.add(instrument)

            db.session.commit()
            logger.info("创建示例投资标的")

            # 为demo用户创建示例投资组合
            demo_user = User.query.filter_by(username='demo').first()
            if demo_user and not Portfolio.query.filter_by(user_id=demo_user.id).first():
                portfolio = Portfolio(
                    user_id=demo_user.id,
                    name='Demo Portfolio',
                    description='示例投资组合 - 定期定额投资SPY',
                    initial_capital=10000.00,
                    currency='USD'
                )
                db.session.add(portfolio)
                db.session.commit()

                # 添加SPY配置
                spy_instrument = Instrument.query.filter_by(symbol='SPY').first()
                if spy_instrument:
                    config = PortfolioConfiguration(
                        portfolio_id=portfolio.id,
                        instrument_id=spy_instrument.id,
                        investment_frequency='MONTHLY',
                        frequency_detail={'day': 1},
                        buy_type='AMOUNT',
                        buy_amount=1000.00,
                        transaction_fee_rate=0.0003,
                        start_date=date(2023, 1, 1),
                        end_date=None
                    )
                    db.session.add(config)
                    db.session.commit()

                logger.info(f"为用户 {demo_user.username} 创建示例投资组合")

            logger.info("数据库初始化完成")
            return True

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False

def sync_sample_data():
    """同步示例数据"""
    logger.info("同步示例历史数据...")

    try:
        from app.services.data_service import DataService
        from app import create_app

        app = create_app()
        with app.app_context():
            data_service = DataService()
            symbols = ['SPY', 'QQQ', 'VTI']  # 减少符号数量，加快初始化

            for symbol in symbols:
                try:
                    logger.info(f"正在同步 {symbol} 的历史数据...")
                    success = data_service.sync_instrument_data(symbol, days=365)
                    if success:
                        logger.info(f"✓ {symbol} 数据同步成功")
                    else:
                        logger.warning(f"✗ {symbol} 数据同步失败")
                except Exception as e:
                    logger.warning(f"✗ {symbol} 数据同步出错: {e}")

            data_service.close()
            logger.info("历史数据同步完成")
            return True

    except Exception as e:
        logger.error(f"数据同步失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始Docker容器初始化...")

    # 等待依赖服务
    if not wait_for_database():
        sys.exit(1)

    if not wait_for_redis():
        sys.exit(1)

    # 初始化数据库
    if not initialize_database():
        sys.exit(1)

    # 同步示例数据（可选）
    if os.environ.get('SYNC_DATA', 'false').lower() == 'true':
        sync_sample_data()

    logger.info("Docker容器初始化完成")

if __name__ == "__main__":
    main()