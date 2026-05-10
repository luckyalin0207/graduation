"""
免费代理池
- 从多个免费代理源抓取代理
- 并发验证可用性
- 提供轮换接口供爬虫使用
"""
import requests
import threading
import time
import random
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# 验证代理时使用的目标地址（用百度，稳定）
VERIFY_URL = 'https://www.baidu.com'
VERIFY_TIMEOUT = 6


class ProxyPool:
    """线程安全的代理池"""

    def __init__(self):
        self._proxies: list[dict] = []   # [{'http': 'http://ip:port', 'https': '...'}]
        self._lock = threading.Lock()
        self._last_fetch = 0
        self._fetch_interval = 300       # 5分钟刷新一次

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------

    def get(self) -> dict | None:
        """取一个可用代理，没有则返回 None（直连）"""
        self._auto_refresh()
        with self._lock:
            if not self._proxies:
                return None
            return random.choice(self._proxies)

    def remove(self, proxy: dict):
        """标记某个代理失效，从池中移除"""
        with self._lock:
            try:
                self._proxies.remove(proxy)
                logger.debug(f"[代理池] 移除失效代理: {proxy.get('http','')}")
            except ValueError:
                pass

    def size(self) -> int:
        with self._lock:
            return len(self._proxies)

    def refresh(self):
        """强制刷新代理池"""
        logger.info("[代理池] 开始刷新...")
        raw = self._fetch_all()
        valid = self._verify_all(raw)
        with self._lock:
            self._proxies = valid
            self._last_fetch = time.time()
        logger.info(f"[代理池] 刷新完成，有效代理 {len(valid)} 个")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _auto_refresh(self):
        if time.time() - self._last_fetch > self._fetch_interval:
            t = threading.Thread(target=self.refresh, daemon=True)
            t.start()
            # 如果池是空的，等待首次刷新完成（最多15秒）
            if not self._proxies:
                t.join(timeout=15)

    def _fetch_all(self) -> list[str]:
        """从多个免费源抓取原始代理列表，返回 ['ip:port', ...]"""
        raw = []
        fetchers = [
            self._fetch_89ip,
            self._fetch_kuaidaili,
            self._fetch_ip3366,
            self._fetch_proxylist,
        ]
        for fn in fetchers:
            try:
                result = fn()
                raw.extend(result)
                logger.debug(f"[代理池] {fn.__name__} 获取 {len(result)} 个")
            except Exception as e:
                logger.debug(f"[代理池] {fn.__name__} 失败: {e}")
        # 去重
        raw = list(set(raw))
        logger.info(f"[代理池] 共抓取原始代理 {len(raw)} 个")
        return raw

    def _verify_all(self, raw: list[str]) -> list[dict]:
        """并发验证，返回可用代理列表"""
        valid = []
        lock = threading.Lock()

        def verify(ip_port: str):
            proxy = {
                'http': f'http://{ip_port}',
                'https': f'http://{ip_port}',
            }
            try:
                r = requests.get(VERIFY_URL, proxies=proxy,
                                 timeout=VERIFY_TIMEOUT, allow_redirects=True)
                if r.status_code == 200:
                    with lock:
                        valid.append(proxy)
            except Exception:
                pass

        with ThreadPoolExecutor(max_workers=30) as pool:
            pool.map(verify, raw)

        logger.info(f"[代理池] 验证完成，有效 {len(valid)}/{len(raw)}")
        return valid

    # ------------------------------------------------------------------
    # 各免费代理源
    # ------------------------------------------------------------------

    def _fetch_89ip(self) -> list[str]:
        """89免费代理"""
        url = 'https://www.89ip.cn/tqdl.html?num=100&address=&kill_address=&port=&kill_port=&time=1'
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        proxies = []
        for line in r.text.strip().splitlines():
            line = line.strip()
            if ':' in line and not line.startswith('<'):
                proxies.append(line)
        return proxies

    def _fetch_kuaidaili(self) -> list[str]:
        """快代理免费区（前3页）"""
        from bs4 import BeautifulSoup
        proxies = []
        headers = {'User-Agent': 'Mozilla/5.0'}
        for page in range(1, 4):
            try:
                url = f'https://www.kuaidaili.com/free/inha/{page}/'
                r = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(r.text, 'html.parser')
                for row in soup.select('table tbody tr'):
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        ip = cols[0].text.strip()
                        port = cols[1].text.strip()
                        if ip and port:
                            proxies.append(f'{ip}:{port}')
                time.sleep(1)  # 快代理有频率限制
            except Exception:
                pass
        return proxies

    def _fetch_ip3366(self) -> list[str]:
        """云代理"""
        from bs4 import BeautifulSoup
        proxies = []
        headers = {'User-Agent': 'Mozilla/5.0'}
        for page in range(1, 3):
            try:
                url = f'http://www.ip3366.net/free/?stype=1&page={page}'
                r = requests.get(url, headers=headers, timeout=10)
                r.encoding = 'gbk'
                soup = BeautifulSoup(r.text, 'html.parser')
                for row in soup.select('table tbody tr'):
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        ip = cols[0].text.strip()
                        port = cols[1].text.strip()
                        if ip and port:
                            proxies.append(f'{ip}:{port}')
            except Exception:
                pass
        return proxies

    def _fetch_proxylist(self) -> list[str]:
        """github 维护的公开代理列表"""
        url = 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt'
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        proxies = []
        for line in r.text.strip().splitlines():
            line = line.strip()
            if ':' in line:
                proxies.append(line)
        return proxies[:200]   # 只取前200个，避免验证太慢


# 全局单例
_pool: ProxyPool | None = None
_pool_lock = threading.Lock()


def get_proxy_pool() -> ProxyPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ProxyPool()
    return _pool
