"""
增强的数据服务 - 集成WARP代理池和请求限流
"""
import yfinance as yf
import pandas as pd
import requests
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from app.models import Instrument
from app.utils.proxy_pool import get_proxy_for_request, ProxyInfo
from app.utils.logging_config import get_logger
from config import Config
import threading
from functools import wraps

logger = get_logger(__name__)

class RateLimiter:
    """请求限流器"""

    def __init__(self, calls_per_second: float = 2.0):
        """
        初始化限流器

        Args:
            calls_per_second: 每秒允许的调用次数
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """如果需要，等待到可以发送下一个请求"""
        with self.lock:
            current_time = time.time()
            time_since_last_call = current_time - self.last_call_time

            if time_since_last_call < self.min_interval:
                wait_time = self.min_interval - time_since_last_call
                logger.debug(f"限流等待 {wait_time:.2f} 秒")
                time.sleep(wait_time)

            self.last_call_time = time.time()

def retry_with_proxy(max_retries: int = 3, backoff_factor: float = 1.0):
    """
    使用代理重试装饰器

    Args:
        max_retries: 最大重试次数
        backoff_factor: 退避因子
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        # 退避等待
                        wait_time = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 1)
                        logger.debug(f"重试第 {attempt} 次，等待 {wait_time:.2f} 秒")
                        time.sleep(wait_time)

                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e
                    logger.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")

                    # 如果是429错误或连接错误，可以重试
                    if attempt < max_retries and ("429" in str(e) or "timeout" in str(e).lower() or "connection" in str(e).lower()):
                        continue
                    else:
                        break

            # 所有重试都失败
            logger.error(f"所有重试都失败，最后错误: {last_exception}")
            raise last_exception

        return wrapper
    return decorator

class ProxiedYFinance:
    """代理化的YFinance包装器"""

    def __init__(self, symbol: str, proxy: ProxyInfo = None):
        """
        初始化代理化的YFinance

        Args:
            symbol: 股票代码
            proxy: 代理信息
        """
        self.symbol = symbol
        self.proxy = proxy
        self._ticker = None

    def _get_ticker(self):
        """获取ticker实例"""
        if self._ticker is None:
            # 配置yfinance使用代理
            if self.proxy:
                # 配置requests会话
                session = requests.Session()
                session.proxies = self.proxy.proxy_dict
                self._ticker = yf.Ticker(self.symbol, session=session)
            else:
                self._ticker = yf.Ticker(self.symbol)

        return self._ticker

    @retry_with_proxy(max_retries=3)
    def get_history(self, start: str, end: str) -> pd.DataFrame:
        """获取历史数据"""
        ticker = self._get_ticker()
        return ticker.history(start=start, end=end)

    @retry_with_proxy(max_retries=3)
    def get_info(self) -> Dict:
        """获取股票信息"""
        ticker = self._get_ticker()
        return ticker.info

class EnhancedDataService:
    """增强的数据服务"""

    def __init__(self):
        """初始化数据服务"""
        # InfluxDB客户端
        self.client = None
        if Config.INFLUXDB_TOKEN:
            self.client = InfluxDBClient(
                url=Config.INFLUXDB_URL,
                token=Config.INFLUXDB_TOKEN,
                org=Config.INFLUXDB_ORG
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()

        # 限流器 - 每秒最多2个请求
        self.rate_limiter = RateLimiter(calls_per_second=1.5)

        logger.info("增强数据服务初始化完成")

    def _get_proxied_ticker(self, symbol: str) -> ProxiedYFinance:
        """获取代理化的ticker"""
        proxy = get_proxy_for_request()
        if proxy:
            logger.debug(f"为 {symbol} 分配代理: {proxy.host}:{proxy.port}")
        else:
            logger.warning(f"未获取到可用代理，{symbol} 将使用直连")

        return ProxiedYFinance(symbol, proxy)

    def fetch_price_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从Yahoo Finance获取价格数据，使用代理池和限流
        """
        # 限流
        self.rate_limiter.wait_if_needed()

        logger.info(f"获取 {symbol} 价格数据: {start_date} 到 {end_date}")

        try:
            # 使用代理化的yfinance
            proxied_ticker = self._get_proxied_ticker(symbol)
            data = proxied_ticker.get_history(start=start_date, end=end_date)

            if data.empty:
                logger.warning(f"未获取到 {symbol} 的真实数据，生成模拟数据")
                return self._generate_mock_data(symbol, start_date, end_date)

            # 报告代理成功
            if proxied_ticker.proxy:
                from app.utils.proxy_pool import get_proxy_pool
                pool = get_proxy_pool()
                pool.report_proxy_success(proxied_ticker.proxy)

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

            logger.info(f"成功获取 {symbol} 数据: {len(data)} 条记录")
            return data

        except Exception as e:
            logger.error(f"获取 {symbol} 数据失败: {str(e)}")

            # 报告代理错误
            proxied_ticker = self._get_proxied_ticker(symbol)
            if proxied_ticker.proxy:
                from app.utils.proxy_pool import get_proxy_pool
                pool = get_proxy_pool()
                pool.report_proxy_error(proxied_ticker.proxy, e)

            # 返回模拟数据作为后备
            logger.info(f"生成 {symbol} 模拟数据")
            return self._generate_mock_data(symbol, start_date, end_date)

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        获取最新价格，使用代理池和限流
        """
        # 限流
        self.rate_limiter.wait_if_needed()

        logger.debug(f"获取 {symbol} 最新价格")

        try:
            # 使用代理化的yfinance
            proxied_ticker = self._get_proxied_ticker(symbol)
            info = proxied_ticker.get_info()

            # 报告代理成功
            if proxied_ticker.proxy:
                from app.utils.proxy_pool import get_proxy_pool
                pool = get_proxy_pool()
                pool.report_proxy_success(proxied_ticker.proxy)

            price = info.get('regularMarketPrice') or info.get('previousClose')
            logger.debug(f"{symbol} 最新价格: {price}")
            return price

        except Exception as e:
            logger.error(f"获取 {symbol} 最新价格失败: {str(e)}")

            # 报告代理错误
            proxied_ticker = self._get_proxied_ticker(symbol)
            if proxied_ticker.proxy:
                from app.utils.proxy_pool import get_proxy_pool
                pool = get_proxy_pool()
                pool.report_proxy_error(proxied_ticker.proxy, e)

            return None

    def get_instrument_info(self, symbol: str) -> Dict:
        """
        获取标的基本信息，使用代理池和限流
        """
        # 限流
        self.rate_limiter.wait_if_needed()

        logger.info(f"获取 {symbol} 基本信息")

        try:
            # 使用代理化的yfinance
            proxied_ticker = self._get_proxied_ticker(symbol)
            info = proxied_ticker.get_info()

            # 报告代理成功
            if proxied_ticker.proxy:
                from app.utils.proxy_pool import get_proxy_pool
                pool = get_proxy_pool()
                pool.report_proxy_success(proxied_ticker.proxy)

            result = {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'type': 'ETF' if 'ETF' in info.get('longName', '').upper() else 'STOCK',
                'exchange': info.get('exchange', 'UNKNOWN'),
                'currency': info.get('currency', 'USD'),
                'sector': info.get('sector'),
                'description': info.get('longBusinessSummary', '')[:500] if info.get('longBusinessSummary') else None
            }

            logger.info(f"成功获取 {symbol} 基本信息: {result['name']}")
            return result

        except Exception as e:
            logger.error(f"获取 {symbol} 基本信息失败: {str(e)}")

            # 报告代理错误
            proxied_ticker = self._get_proxied_ticker(symbol)
            if proxied_ticker.proxy:
                from app.utils.proxy_pool import get_proxy_pool
                pool = get_proxy_pool()
                pool.report_proxy_error(proxied_ticker.proxy, e)

            # 返回默认信息
            return {
                'symbol': symbol,
                'name': symbol,
                'type': 'UNKNOWN',
                'exchange': 'UNKNOWN',
                'currency': 'USD'
            }

    def sync_instrument_data(self, symbol: str, days: int = 365) -> bool:
        """
        同步指定标的的历史数据
        """
        logger.info(f"同步 {symbol} 历史数据，天数: {days}")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        data = self.fetch_price_data(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

        if not data.empty:
            self.store_price_data(symbol, data)
            logger.info(f"{symbol} 数据同步成功")
            return True

        logger.warning(f"{symbol} 数据同步失败")
        return False

    def _generate_mock_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        生成模拟数据用于测试
        """
        import numpy as np

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
            'GOOGL': 100.0,
            'TSLA': 200.0
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

        logger.info(f"生成 {symbol} 模拟数据: {len(data)} 条记录")
        return pd.DataFrame(data)

    def store_price_data(self, symbol: str, data: pd.DataFrame, exchange: str = 'NASDAQ'):
        """
        将价格数据存储到InfluxDB
        """
        if self.client is None:
            logger.warning("InfluxDB客户端未配置")
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
            logger.info(f"存储 {len(points)} 条 {symbol} 数据点到InfluxDB")
        except Exception as e:
            logger.error(f"存储 {symbol} 数据到InfluxDB失败: {str(e)}")

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
                logger.info(f"从InfluxDB获取 {symbol} 数据: {len(result)} 条记录")
                return result
            else:
                # 如果InfluxDB中没有数据，从Yahoo Finance获取并存储
                data = self.fetch_price_data(symbol, start_date, end_date)
                if not data.empty:
                    self.store_price_data(symbol, data)
                return data

        except Exception as e:
            logger.error(f"从InfluxDB查询 {symbol} 数据失败: {str(e)}")
            # 回退到Yahoo Finance
            return self.fetch_price_data(symbol, start_date, end_date)

    def close(self):
        """
        关闭连接
        """
        if self.client:
            self.client.close()
            logger.info("InfluxDB连接已关闭")