"""
Cookie 自动刷新管理器
- 优先从数据库读取上次保存的 Cookie
- 用户手动粘贴后自动持久化
- Cookie 失效时用非 headless Selenium 刷新（能通过 WAF）
"""
import time
import logging
import threading

logger = logging.getLogger(__name__)

COOKIE_TTL = 6 * 3600  # 6小时，保守估计


class CookieManager:

    def __init__(self):
        self._cookie_str = ''
        self._fetched_at = 0
        self._lock = threading.Lock()
        self._refresh_lock = threading.Lock()  # 防止并发刷新
        self._load_from_db()

    # ── 对外接口 ──────────────────────────────────────────

    def get(self, force=False) -> str:
        """获取有效 Cookie，过期则自动刷新（线程安全，只刷新一次）"""
        with self._lock:
            age = time.time() - self._fetched_at
            if not force and self._cookie_str and age < COOKIE_TTL:
                return self._cookie_str

        # 用刷新锁保证多线程只有一个在刷新，其他等待结果
        with self._refresh_lock:
            # 二次检查：可能已被其他线程刷新好了
            with self._lock:
                age = time.time() - self._fetched_at
                if not force and self._cookie_str and age < COOKIE_TTL:
                    return self._cookie_str

            logger.info('[CookieManager] 开始刷新 Cookie（其他线程将等待）...')
            cookie = self._fetch_via_selenium()
            if cookie:
                self._save(cookie)
            else:
                logger.warning('[CookieManager] 刷新失败，返回旧值（可能为空）')

        return self._cookie_str

    def set_manual(self, cookie_str: str):
        """用户手动粘贴 Cookie，持久化保存"""
        self._save(cookie_str.strip())
        logger.info(f'[CookieManager] 手动设置 Cookie，长度 {len(cookie_str)}')

    def is_valid(self) -> bool:
        with self._lock:
            return bool(self._cookie_str) and (time.time() - self._fetched_at < COOKIE_TTL)

    # ── 内部方法 ──────────────────────────────────────────

    def _save(self, cookie_str: str):
        with self._lock:
            self._cookie_str = cookie_str
            self._fetched_at = time.time()
        # 持久化到数据库（存在 SpiderInfo 的扩展字段，或用 Django cache）
        try:
            from django.core.cache import cache
            cache.set('spider_51job_cookie', cookie_str, timeout=COOKIE_TTL)
            cache.set('spider_51job_cookie_ts', self._fetched_at, timeout=COOKIE_TTL)
        except Exception:
            pass

    def _load_from_db(self):
        """启动时从缓存恢复 Cookie"""
        try:
            from django.core.cache import cache
            cookie = cache.get('spider_51job_cookie', '')
            ts = cache.get('spider_51job_cookie_ts', 0)
            if cookie and (time.time() - ts < COOKIE_TTL):
                with self._lock:
                    self._cookie_str = cookie
                    self._fetched_at = ts
                logger.info(f'[CookieManager] 从缓存恢复 Cookie，长度 {len(cookie)}')
        except Exception:
            pass

    def _fetch_via_selenium(self) -> str:
        """
        用非 headless Selenium 访问 51job 获取 Cookie
        注意：headless 模式跑不过 WAF，必须用有界面模式
        自动使用 selenium-manager（selenium>=4.6 内置）匹配 ChromeDriver 版本
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

            opts = Options()
            # 不加 --headless，用真实浏览器窗口才能通过 WAF
            opts.add_argument('--disable-gpu')
            opts.add_argument('--no-sandbox')
            opts.add_argument('--disable-blink-features=AutomationControlled')
            opts.add_argument('--disable-dev-shm-usage')
            opts.add_argument('--window-size=1280,800')
            opts.add_argument('--log-level=3')
            opts.add_argument('--disable-extensions')
            opts.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
            opts.add_experimental_option('useAutomationExtension', False)
            opts.add_argument(
                'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            # 优先尝试 webdriver-manager 自动匹配版本
            driver = None
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=opts)
                logger.info('[CookieManager] 使用 webdriver-manager 自动匹配 ChromeDriver')
            except Exception as wdm_err:
                logger.warning(f'[CookieManager] webdriver-manager 失败: {wdm_err}，尝试 selenium 内置管理')
                try:
                    # selenium >= 4.6 内置 selenium-manager，会自动下载匹配版本
                    driver = webdriver.Chrome(options=opts)
                except Exception as e2:
                    logger.error(f'[CookieManager] selenium 内置管理也失败: {e2}')
                    return ''

            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': '''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                window.chrome = {runtime: {}};
            '''})

            try:
                logger.info('[CookieManager] 打开浏览器访问 51job...')
                driver.get('https://www.51job.com/')
                time.sleep(3)
                driver.get('https://we.51job.com/pc/search?keyword=Python&searchType=2&sortType=0&pageNum=1&pageSize=20')

                # 等待 WAF Cookie 出现，最多 20 秒
                deadline = time.time() + 20
                while time.time() < deadline:
                    names = {c['name'] for c in driver.get_cookies()}
                    if 'acw_sc__v3' in names or 'JSESSIONID' in names:
                        logger.info('[CookieManager] WAF Cookie 已获取')
                        break
                    time.sleep(0.5)

                time.sleep(2)  # 等待其他 Cookie 稳定
                cookies = driver.get_cookies()
                cookie_str = '; '.join(
                    f"{c['name']}={c['value']}"
                    for c in cookies if c.get('value')
                )
                logger.info(f'[CookieManager] 获取到 {len(cookies)} 个 Cookie')
                return cookie_str

            finally:
                driver.quit()

        except Exception as e:
            logger.error(f'[CookieManager] Selenium 刷新失败: {e}')
            return ''


# 全局单例
_manager: CookieManager | None = None
_manager_lock = threading.Lock()


def get_cookie_manager() -> CookieManager:
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = CookieManager()
    return _manager
