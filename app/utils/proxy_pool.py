"""
WARP代理池管理系统
"""
import requests
import time
import random
import threading
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import redis
import json
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

@dataclass
class ProxyInfo:
    """代理信息"""
    host: str
    port: int
    protocol: str = 'socks5'
    is_healthy: bool = True
    last_check: datetime = None
    response_time: float = 0.0
    error_count: int = 0
    success_count: int = 0
    last_used: datetime = None

    @property
    def proxy_url(self) -> str:
        """获取代理URL"""
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def proxy_dict(self) -> Dict[str, str]:
        """获取requests使用的代理字典"""
        return {
            'http': self.proxy_url,
            'https': self.proxy_url
        }

    def to_dict(self) -> Dict:
        """转换为字典，确保所有值都是Redis可序列化的"""
        return {
            'host': str(self.host),
            'port': str(self.port),
            'protocol': str(self.protocol),
            'is_healthy': str(self.is_healthy).lower(),  # 转换为字符串
            'last_check': self.last_check.isoformat() if self.last_check else '',
            'response_time': str(self.response_time),
            'error_count': str(self.error_count),
            'success_count': str(self.success_count),
            'last_used': self.last_used.isoformat() if self.last_used else ''
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProxyInfo':
        """从字典创建实例，处理字符串转换"""
        proxy = cls(
            host=str(data['host']),
            port=int(data['port']),
            protocol=str(data.get('protocol', 'socks5')),
            is_healthy=str(data.get('is_healthy', 'true')).lower() == 'true',  # 字符串转布尔
            response_time=float(data.get('response_time', 0.0)),
            error_count=int(data.get('error_count', 0)),
            success_count=int(data.get('success_count', 0))
        )

        if data.get('last_check') and data['last_check']:
            proxy.last_check = datetime.fromisoformat(data['last_check'])
        if data.get('last_used') and data['last_used']:
            proxy.last_used = datetime.fromisoformat(data['last_used'])

        return proxy

class WARPProxyPool:
    """WARP代理池管理器"""

    def __init__(self, redis_url: str = "redis://localhost:6380/0"):
        """
        初始化代理池

        Args:
            redis_url: Redis连接URL
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.proxies: Dict[str, ProxyInfo] = {}
        self.current_proxy_index = 0
        self.lock = threading.RLock()

        # 配置参数
        self.health_check_interval = 60  # 健康检查间隔（秒）
        self.health_check_timeout = 10   # 健康检查超时（秒）
        self.max_error_count = 3         # 最大错误次数
        self.test_url = "https://httpbin.org/ip"  # 测试URL

        # 默认WARP代理配置
        self.default_proxies = [
            {'host': 'localhost', 'port': 40001},
            {'host': 'localhost', 'port': 40002},
            {'host': 'localhost', 'port': 40003},
            {'host': 'localhost', 'port': 40004},
            {'host': 'localhost', 'port': 40005},
        ]

        # 初始化
        self._initialize_proxies()
        self._start_health_checker()

    def _initialize_proxies(self):
        """初始化代理列表"""
        logger.info("初始化WARP代理池...")

        # 从Redis加载已保存的代理状态
        saved_proxies = self._load_proxies_from_redis()

        # 初始化或更新代理列表
        for proxy_config in self.default_proxies:
            proxy_key = f"{proxy_config['host']}:{proxy_config['port']}"

            if proxy_key in saved_proxies:
                # 使用保存的代理信息
                self.proxies[proxy_key] = saved_proxies[proxy_key]
            else:
                # 创建新的代理信息
                self.proxies[proxy_key] = ProxyInfo(
                    host=proxy_config['host'],
                    port=proxy_config['port']
                )

        logger.info(f"初始化完成，共 {len(self.proxies)} 个代理")

    def _load_proxies_from_redis(self) -> Dict[str, ProxyInfo]:
        """从Redis加载代理状态"""
        try:
            proxies = {}
            keys = self.redis_client.keys("proxy:*")

            for key in keys:
                proxy_data = self.redis_client.hgetall(key)
                if proxy_data:
                    proxy_key = key.replace("proxy:", "")
                    proxies[proxy_key] = ProxyInfo.from_dict(proxy_data)

            logger.info(f"从Redis加载了 {len(proxies)} 个代理状态")
            return proxies

        except Exception as e:
            logger.warning(f"从Redis加载代理状态失败: {e}")
            return {}

    def _save_proxy_to_redis(self, proxy_key: str, proxy: ProxyInfo):
        """保存代理状态到Redis"""
        try:
            self.redis_client.hset(f"proxy:{proxy_key}", mapping=proxy.to_dict())
        except Exception as e:
            logger.warning(f"保存代理状态到Redis失败: {e}")

    def _start_health_checker(self):
        """启动健康检查线程"""
        def health_check_worker():
            while True:
                try:
                    self._check_all_proxies_health()
                    time.sleep(self.health_check_interval)
                except Exception as e:
                    logger.error(f"健康检查线程异常: {e}")
                    time.sleep(10)  # 异常时等待10秒再重试

        health_thread = threading.Thread(target=health_check_worker, daemon=True)
        health_thread.start()
        logger.info("健康检查线程已启动")

    def _check_all_proxies_health(self):
        """检查所有代理的健康状态"""
        logger.debug("开始检查代理健康状态...")

        with self.lock:
            for proxy_key, proxy in self.proxies.items():
                self._check_proxy_health(proxy_key, proxy)

    def _check_proxy_health(self, proxy_key: str, proxy: ProxyInfo):
        """检查单个代理的健康状态"""
        try:
            start_time = time.time()

            # 使用代理发送测试请求
            response = requests.get(
                self.test_url,
                proxies=proxy.proxy_dict,
                timeout=self.health_check_timeout
            )

            response_time = time.time() - start_time

            if response.status_code == 200:
                # 代理健康
                proxy.is_healthy = True
                proxy.response_time = response_time
                proxy.last_check = datetime.now()
                proxy.error_count = 0
                proxy.success_count += 1

                # 记录IP信息
                try:
                    ip_info = response.json()
                    logger.debug(f"代理 {proxy_key} 健康，IP: {ip_info.get('origin', 'unknown')}")
                except:
                    logger.debug(f"代理 {proxy_key} 健康，响应时间: {response_time:.2f}s")
            else:
                raise Exception(f"HTTP {response.status_code}")

        except Exception as e:
            # 代理异常
            proxy.error_count += 1
            proxy.last_check = datetime.now()

            if proxy.error_count >= self.max_error_count:
                proxy.is_healthy = False
                logger.warning(f"代理 {proxy_key} 标记为不健康: {e}")
            else:
                logger.debug(f"代理 {proxy_key} 检查失败 ({proxy.error_count}/{self.max_error_count}): {e}")

        # 保存状态到Redis
        self._save_proxy_to_redis(proxy_key, proxy)

    def get_healthy_proxies(self) -> List[ProxyInfo]:
        """获取所有健康的代理"""
        with self.lock:
            return [proxy for proxy in self.proxies.values() if proxy.is_healthy]

    def get_best_proxy(self) -> Optional[ProxyInfo]:
        """获取最佳代理（响应时间最短的健康代理）"""
        healthy_proxies = self.get_healthy_proxies()

        if not healthy_proxies:
            logger.warning("没有可用的健康代理")
            return None

        # 按响应时间排序
        healthy_proxies.sort(key=lambda p: p.response_time)
        return healthy_proxies[0]

    def get_random_proxy(self) -> Optional[ProxyInfo]:
        """随机获取一个健康代理"""
        healthy_proxies = self.get_healthy_proxies()

        if not healthy_proxies:
            logger.warning("没有可用的健康代理")
            return None

        return random.choice(healthy_proxies)

    def get_next_proxy(self) -> Optional[ProxyInfo]:
        """轮询获取下一个健康代理"""
        healthy_proxies = self.get_healthy_proxies()

        if not healthy_proxies:
            logger.warning("没有可用的健康代理")
            return None

        with self.lock:
            proxy = healthy_proxies[self.current_proxy_index % len(healthy_proxies)]
            self.current_proxy_index += 1
            proxy.last_used = datetime.now()

            return proxy

    def report_proxy_success(self, proxy: ProxyInfo):
        """报告代理使用成功"""
        with self.lock:
            proxy.success_count += 1
            proxy.error_count = max(0, proxy.error_count - 1)  # 减少错误计数
            proxy.last_used = datetime.now()

            # 保存状态
            proxy_key = f"{proxy.host}:{proxy.port}"
            self._save_proxy_to_redis(proxy_key, proxy)

    def report_proxy_error(self, proxy: ProxyInfo, error: Exception):
        """报告代理使用错误"""
        with self.lock:
            proxy.error_count += 1

            if proxy.error_count >= self.max_error_count:
                proxy.is_healthy = False
                logger.warning(f"代理 {proxy.host}:{proxy.port} 因错误过多被标记为不健康: {error}")

            # 保存状态
            proxy_key = f"{proxy.host}:{proxy.port}"
            self._save_proxy_to_redis(proxy_key, proxy)

    def get_pool_status(self) -> Dict:
        """获取代理池状态"""
        with self.lock:
            healthy_count = len(self.get_healthy_proxies())
            total_count = len(self.proxies)

            proxy_details = []
            for proxy_key, proxy in self.proxies.items():
                proxy_details.append({
                    'key': proxy_key,
                    'is_healthy': proxy.is_healthy,
                    'response_time': proxy.response_time,
                    'error_count': proxy.error_count,
                    'success_count': proxy.success_count,
                    'last_check': proxy.last_check.isoformat() if proxy.last_check else None,
                    'last_used': proxy.last_used.isoformat() if proxy.last_used else None
                })

            return {
                'total_proxies': total_count,
                'healthy_proxies': healthy_count,
                'unhealthy_proxies': total_count - healthy_count,
                'health_rate': healthy_count / total_count if total_count > 0 else 0,
                'proxies': proxy_details
            }

    def force_health_check(self):
        """强制执行健康检查"""
        logger.info("强制执行代理健康检查...")
        self._check_all_proxies_health()
        logger.info("健康检查完成")

# 全局代理池实例
_proxy_pool = None

def get_proxy_pool() -> WARPProxyPool:
    """获取全局代理池实例"""
    global _proxy_pool
    if _proxy_pool is None:
        _proxy_pool = WARPProxyPool()
    return _proxy_pool

def get_proxy_for_request() -> Optional[ProxyInfo]:
    """为请求获取代理"""
    pool = get_proxy_pool()
    return pool.get_next_proxy()  # 使用轮询策略