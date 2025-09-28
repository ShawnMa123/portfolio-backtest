#!/usr/bin/env python3
"""
初始化数据脚本
用于创建示例用户和数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Instrument, Portfolio, PortfolioConfiguration
from app.services.data_service import DataService
from datetime import datetime, date, timedelta

def init_sample_data():
    """初始化示例数据"""
    app = create_app()

    with app.app_context():
        # 创建数据库表
        db.create_all()

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
            print("创建示例用户: demo / password123")

        # 确保有一些基本的投资标的
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
        print("创建示例投资标的")

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
                    frequency_detail={'day': 1},  # 每月1号
                    buy_type='AMOUNT',
                    buy_amount=1000.00,
                    transaction_fee_rate=0.0003,
                    start_date=date(2023, 1, 1),
                    end_date=None
                )
                db.session.add(config)
                db.session.commit()

            print(f"为用户 {demo_user.username} 创建示例投资组合")

        print("数据初始化完成!")

def sync_sample_data():
    """同步示例标的的历史数据"""
    app = create_app()

    with app.app_context():
        data_service = DataService()

        symbols = ['SPY', 'QQQ', 'VTI', 'AAPL', 'MSFT']

        for symbol in symbols:
            print(f"正在同步 {symbol} 的历史数据...")
            try:
                success = data_service.sync_instrument_data(symbol, days=365*2)  # 同步2年数据
                if success:
                    print(f"✓ {symbol} 数据同步成功")
                else:
                    print(f"✗ {symbol} 数据同步失败")
            except Exception as e:
                print(f"✗ {symbol} 数据同步出错: {str(e)}")

        data_service.close()
        print("历史数据同步完成!")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='初始化数据脚本')
    parser.add_argument('--init', action='store_true', help='初始化示例数据')
    parser.add_argument('--sync', action='store_true', help='同步历史数据')

    args = parser.parse_args()

    if args.init:
        init_sample_data()

    if args.sync:
        sync_sample_data()

    if not args.init and not args.sync:
        print("请指定操作:")
        print("  --init  初始化示例数据")
        print("  --sync  同步历史数据")
        print("  python scripts/init_data.py --init --sync  同时执行两个操作")