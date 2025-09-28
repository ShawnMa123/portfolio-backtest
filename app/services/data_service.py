import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from app.models import Instrument
from config import Config

class DataService:
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
        从Yahoo Finance获取价格数据
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)

            if data.empty:
                raise ValueError(f"No data found for symbol {symbol}")

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
            return pd.DataFrame()

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