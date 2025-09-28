#!/usr/bin/env python3
"""
API测试脚本
用于测试主要的API功能
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = 'http://localhost:5000/api'

class APITester:
    def __init__(self):
        self.token = None
        self.session = requests.Session()

    def login(self, username='demo', password='password123'):
        """登录获取token"""
        response = self.session.post(f'{BASE_URL}/auth/login', json={
            'username': username,
            'password': password
        })

        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
            self.session.headers.update({'Authorization': f'Bearer {self.token}'})
            print(f"✓ 登录成功，用户: {data['user']['username']}")
            return True
        else:
            print(f"✗ 登录失败: {response.text}")
            return False

    def test_instruments(self):
        """测试标的相关API"""
        print("\n=== 测试投资标的API ===")

        # 获取标的列表
        response = self.session.get(f'{BASE_URL}/instruments')
        if response.status_code == 200:
            instruments = response.json()
            print(f"✓ 获取标的列表成功，共 {len(instruments)} 个标的")
        else:
            print(f"✗ 获取标的列表失败: {response.text}")

        # 搜索标的
        response = self.session.get(f'{BASE_URL}/instruments/search?symbol=SPY')
        if response.status_code == 200:
            instrument = response.json()
            print(f"✓ 搜索标的成功: {instrument['name']}")
        else:
            print(f"✗ 搜索标的失败: {response.text}")

        # 获取价格数据
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        response = self.session.get(f'{BASE_URL}/instruments/SPY/price?start_date={start_date}&end_date={end_date}')
        if response.status_code == 200:
            price_data = response.json()
            print(f"✓ 获取价格数据成功，共 {len(price_data['data'])} 个数据点")
        else:
            print(f"✗ 获取价格数据失败: {response.text}")

    def test_portfolios(self):
        """测试投资组合API"""
        print("\n=== 测试投资组合API ===")

        # 获取投资组合列表
        response = self.session.get(f'{BASE_URL}/portfolios')
        if response.status_code == 200:
            portfolios = response.json()
            print(f"✓ 获取投资组合列表成功，共 {len(portfolios)} 个组合")

            if portfolios:
                portfolio_id = portfolios[0]['id']
                print(f"使用投资组合ID: {portfolio_id}")

                # 获取投资组合配置
                response = self.session.get(f'{BASE_URL}/portfolios/{portfolio_id}/configurations')
                if response.status_code == 200:
                    configs = response.json()
                    print(f"✓ 获取投资组合配置成功，共 {len(configs)} 个配置")
                else:
                    print(f"✗ 获取投资组合配置失败: {response.text}")

                return portfolio_id
        else:
            print(f"✗ 获取投资组合列表失败: {response.text}")

        return None

    def test_backtest(self, portfolio_id):
        """测试回测API"""
        if not portfolio_id:
            print("没有可用的投资组合，跳过回测测试")
            return

        print("\n=== 测试回测API ===")

        # 发起回测
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        backtest_data = {
            'portfolio_id': portfolio_id,
            'name': 'API测试回测',
            'start_date': start_date,
            'end_date': end_date
        }

        print(f"发起回测: {start_date} 到 {end_date}")
        response = self.session.post(f'{BASE_URL}/backtests', json=backtest_data)

        if response.status_code == 201:
            backtest = response.json()
            backtest_id = backtest['id']
            print(f"✓ 回测创建成功，回测ID: {backtest_id}")
            print(f"  初始资金: ${backtest['initial_capital']:,.2f}")
            print(f"  最终价值: ${backtest['final_value']:,.2f}")
            print(f"  总收益率: {backtest['total_return']:.2%}")
            print(f"  年化收益率: {backtest['annualized_return']:.2%}")
            print(f"  交易次数: {backtest['total_trades']}")

            # 获取交易记录
            response = self.session.get(f'{BASE_URL}/backtests/{backtest_id}/transactions')
            if response.status_code == 200:
                transactions = response.json()
                print(f"✓ 获取交易记录成功，共 {len(transactions)} 笔交易")
            else:
                print(f"✗ 获取交易记录失败: {response.text}")

            # 获取绩效数据
            response = self.session.get(f'{BASE_URL}/backtests/{backtest_id}/performance')
            if response.status_code == 200:
                performance = response.json()
                print(f"✓ 获取绩效数据成功")
                if 'daily_values' in performance:
                    print(f"  日度净值数据点: {len(performance['daily_values'])}")
            else:
                print(f"✗ 获取绩效数据失败: {response.text}")

        else:
            print(f"✗ 回测创建失败: {response.text}")

    def run_all_tests(self):
        """运行所有测试"""
        print("开始API测试...")

        if not self.login():
            return

        self.test_instruments()
        portfolio_id = self.test_portfolios()
        self.test_backtest(portfolio_id)

        print("\nAPI测试完成!")

if __name__ == '__main__':
    tester = APITester()
    tester.run_all_tests()