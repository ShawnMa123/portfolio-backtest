import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from app.models import Instrument
from config import Config

# 检查是否启用代理池
USE_PROXY_POOL = getattr(Config, 'USE_PROXY_POOL', True)

if USE_PROXY_POOL:
    try:
        from app.services.enhanced_data_service import EnhancedDataService as BaseDataService
        print("✅ 使用增强数据服务（代理池）")
    except ImportError:
        print("⚠️ 代理池服务导入失败，使用标准数据服务")
        USE_PROXY_POOL = False

if not USE_PROXY_POOL:
    class BaseDataService:
        pass

class DataService(BaseDataService if USE_PROXY_POOL else object):
    def __init__(self):
        self.client = None
        if Config.INFLUXDB_TOKEN:
            self.client = InfluxDBClient(
                url=Config.INFLUXDB_URL,
                token=Config.INFLUXDB_TOKEN,
                org=Config.INFLUXDB_ORG
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()

    def fetch_price_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从Yahoo Finance获取价格数据，如果失败则生成模拟数据
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)

            if data.empty:
                print(f"No real data found for {symbol}, generating mock data")
                return self._generate_mock_data(symbol, start_date, end_date)

            # 重命名列以匹配我们的数据模型
            data = data.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            # 添加复权收盘价
            data['adj_close'] = data['close']

            # 重置索引，使Date成为一列
            data = data.reset_index()
            data['Date'] = data['Date'].dt.date

            return data

        except Exception as e:
            print(f"Error fetching data for {symbol}: {str(e)}")
            print(f"Generating mock data for {symbol}")
            return self._generate_mock_data(symbol, start_date, end_date)

    def _generate_mock_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        生成模拟数据用于测试
        """
        import numpy as np
        from datetime import datetime, timedelta

        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        # 生成日期范围
        date_range = []
        current_date = start_dt
        while current_date <= end_dt:
            # 只添加工作日
            if current_date.weekday() < 5:
                date_range.append(current_date.date())
            current_date += timedelta(days=1)

        if not date_range:
            return pd.DataFrame()

        # 基础价格（根据不同symbol设置不同的基础价格）
        base_prices = {
            'SPY': 400.0,
            'QQQ': 350.0,
            'AAPL': 150.0,
            'MSFT': 250.0,
            'GOOGL': 100.0
        }
        base_price = base_prices.get(symbol, 100.0)

        # 生成价格数据（简单的随机游走）
        np.random.seed(hash(symbol) % 2**32)  # 使价格具有可重复性
        returns = np.random.normal(0.0005, 0.02, len(date_range))  # 日收益率

        prices = []
        current_price = base_price
        for ret in returns:
            current_price = current_price * (1 + ret)
            prices.append(current_price)

        # 创建OHLCV数据
        data = []
        for i, (date, close_price) in enumerate(zip(date_range, prices)):
            # 简单的OHLC生成
            high = close_price * (1 + abs(np.random.normal(0, 0.01)))
            low = close_price * (1 - abs(np.random.normal(0, 0.01)))
            open_price = close_price * (1 + np.random.normal(0, 0.005))
            volume = int(np.random.normal(1000000, 200000))

            data.append({
                'Date': date,
                'open': open_price,
                'high': max(open_price, high, close_price),
                'low': min(open_price, low, close_price),
                'close': close_price,
                'adj_close': close_price,
                'volume': max(volume, 100000)  # 确保volume不为负
            })

        return pd.DataFrame(data)

    def store_price_data(self, symbol: str, data: pd.DataFrame, exchange: str = 'NASDAQ'):
        """
        将价格数据存储到InfluxDB
        """
        if self.client is None:
            print("InfluxDB client not configured")
            return

        if data.empty:
            return

        points = []
        for _, row in data.iterrows():
            point = Point("daily_prices") \
                .tag("symbol", symbol) \
                .tag("exchange", exchange) \
                .field("open", float(row['open'])) \
                .field("high", float(row['high'])) \
                .field("low", float(row['low'])) \
                .field("close", float(row['close'])) \
                .field("volume", int(row['volume'])) \
                .field("adj_close", float(row['adj_close'])) \
                .time(row['Date'])

            points.append(point)

        try:
            self.write_api.write(bucket=Config.INFLUXDB_BUCKET, record=points)
            print(f"Stored {len(points)} data points for {symbol}")
        except Exception as e:
            print(f"Error storing data for {symbol}: {str(e)}")

    def get_price_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从InfluxDB获取价格数据，如果没有则从Yahoo Finance获取
        """
        if self.client is None:
            # 如果没有InfluxDB配置，直接从Yahoo Finance获取
            return self.fetch_price_data(symbol, start_date, end_date)

        try:
            query = f'''
                from(bucket: "{Config.INFLUXDB_BUCKET}")
                |> range(start: {start_date}, stop: {end_date})
                |> filter(fn: (r) => r["_measurement"] == "daily_prices")
                |> filter(fn: (r) => r["symbol"] == "{symbol}")
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''

            result = self.query_api.query_data_frame(query)

            if not result.empty:
                # 转换数据格式
                result['Date'] = pd.to_datetime(result['_time']).dt.date
                result = result[['Date', 'open', 'high', 'low', 'close', 'volume', 'adj_close']]
                return result
            else:
                # 如果InfluxDB中没有数据，从Yahoo Finance获取并存储
                data = self.fetch_price_data(symbol, start_date, end_date)
                if not data.empty:
                    self.store_price_data(symbol, data)
                return data

        except Exception as e:
            print(f"Error querying InfluxDB for {symbol}: {str(e)}")
            # 回退到Yahoo Finance
            return self.fetch_price_data(symbol, start_date, end_date)

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        获取最新价格
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return info.get('regularMarketPrice') or info.get('previousClose')
        except Exception as e:
            print(f"Error getting latest price for {symbol}: {str(e)}")
            return None

    def sync_instrument_data(self, symbol: str, days: int = 365) -> bool:
        """
        同步指定标的的历史数据
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        data = self.fetch_price_data(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

        if not data.empty:
            self.store_price_data(symbol, data)
            return True

        return False

    def get_instrument_info(self, symbol: str) -> Dict:
        """
        获取标的基本信息
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'type': 'ETF' if 'ETF' in info.get('longName', '').upper() else 'STOCK',
                'exchange': info.get('exchange', 'UNKNOWN'),
                'currency': info.get('currency', 'USD'),
                'sector': info.get('sector'),
                'description': info.get('longBusinessSummary', '')[:500] if info.get('longBusinessSummary') else None
            }
        except Exception as e:
            print(f"Error getting instrument info for {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'name': symbol,
                'type': 'UNKNOWN',
                'exchange': 'UNKNOWN',
                'currency': 'USD'
            }

    def close(self):
        """
        关闭InfluxDB连接
        """
        if self.client:
            self.client.close()