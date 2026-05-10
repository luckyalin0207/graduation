"""
基于 jshook/CDP 的浏览器内爬虫
- 复用已打开的浏览器页面（51job / BOSS直聘）
- 通过 CDP Runtime.evaluate 执行 JS，自动携带 sign/cookie 等验证参数
- 不需要手动维护 Cookie，不需要逆向 sign 算法
"""
import json
import time
import logging
import threading

logger = logging.getLogger(__name__)

_browser_lock = threading.Lock()


# ── 通用工具 ──────────────────────────────────────────────────────────────────

def _get_tab_ws(url_keyword: str = None) -> str | None:
    """
    获取 Chrome DevTools WebSocket URL
    url_keyword: 优先匹配包含该关键词的标签页，None 则返回第一个
    """
    try:
        import requests as req
        r = req.get('http://localhost:9222/json', timeout=2)
        tabs = r.json()
        if url_keyword:
            for tab in tabs:
                if url_keyword in tab.get('url', ''):
                    return tab['webSocketDebuggerUrl']
        if tabs:
            return tabs[0]['webSocketDebuggerUrl']
    except Exception:
        pass
    return None


def is_browser_available() -> bool:
    """检查 jshook 浏览器是否有 51job 标签页"""
    try:
        import requests as req
        r = req.get('http://localhost:9222/json', timeout=2)
        tabs = r.json()
        return any('51job' in t.get('url', '') for t in tabs)
    except Exception:
        return False


def is_boss_available() -> bool:
    """检查 jshook 浏览器是否有 BOSS 直聘标签页"""
    try:
        import requests as req
        r = req.get('http://localhost:9222/json', timeout=2)
        tabs = r.json()
        return any('zhipin' in t.get('url', '') for t in tabs)
    except Exception:
        return False


def _cdp_eval(ws_url: str, js: str, timeout: int = 15) -> str | None:
    """
    通过 CDP Runtime.evaluate 执行 JS，返回字符串结果
    """
    try:
        import websocket
        ws = websocket.create_connection(
            ws_url,
            timeout=timeout + 10,
            origin='http://localhost:9222',
            header={'Host': 'localhost:9222'},
        )
        # 用大随机数避免与 Chrome 内部事件 id 冲突
        import random
        msg_id = random.randint(100000, 999999)
        cmd = {
            'id': msg_id,
            'method': 'Runtime.evaluate',
            'params': {
                'expression': js,
                'awaitPromise': True,
                'returnByValue': True,
                'timeout': timeout * 1000,
            }
        }
        ws.send(json.dumps(cmd))
        deadline = time.time() + timeout + 10
        while time.time() < deadline:
            try:
                ws.settimeout(deadline - time.time())
                raw = ws.recv()
                msg = json.loads(raw)
                # 只处理我们发出的那条命令的响应，其他事件继续等
                if msg.get('id') != msg_id:
                    continue
                result = msg.get('result', {})
                if 'exceptionDetails' in result:
                    logger.warning(f'[CDP] JS 异常: {result["exceptionDetails"]}')
                    ws.close()
                    return None
                value = result.get('result', {}).get('value')
                ws.close()
                return value
            except websocket.WebSocketTimeoutException:
                # 真正超时，退出
                logger.warning(f'[CDP] 等待响应超时（{timeout}s）')
                break
            except Exception as e:
                # 其他异常（如收到非 JSON 数据）记录后继续等
                logger.debug(f'[CDP] recv 异常（继续等待）: {e}')
                continue
        ws.close()
    except ImportError:
        logger.warning('[CDP] 需要安装 websocket-client: pip install websocket-client')
    except Exception as e:
        logger.error(f'[CDP] 出错: {e}')
    return None


# ── 51job 爬虫 ────────────────────────────────────────────────────────────────

def crawl_via_browser(keyword: str, page: int, page_size: int = 20) -> list[dict]:
    """
    通过浏览器内的 window.axios 爬取 51job 数据
    需要 jshook 已打开 we.51job.com 页面
    """
    ws_url = _get_tab_ws('51job')
    if not ws_url:
        logger.warning('[51job] 未找到 51job 标签页')
        return []

    js_code = f"""
(function() {{
    return new Promise((resolve, reject) => {{
        if (!window.axios) {{ reject('no axios'); return; }}
        window.axios.get('https://we.51job.com/api/job/search-pc', {{
            params: {{
                api_key: '51job',
                timestamp: Math.floor(Date.now()/1000),
                keyword: '{keyword}',
                searchType: 2,
                function: '', industry: '',
                jobArea: '', jobArea2: '', landmark: '', metro: '',
                salary: '', workYear: '', degree: '',
                companyType: '', companySize: '', jobType: '', issueDate: '',
                sortType: 0, pageNum: {page}, requestId: '',
                pageSize: {page_size}, source: 1, accountId: '',
                pageCode: 'sou|sou|soulb', scene: 7, language: 0
            }}
        }}).then(r => {{
            const items = r.data?.resultbody?.job?.items || [];
            resolve(JSON.stringify(items.map(j => ({{
                name: j.jobName || '',
                company: j.companyName || '',
                salary: j.provideSalaryString || '面议',
                salary_min: j.jobSalaryMin || null,
                salary_max: j.jobSalaryMax || null,
                city: j.jobAreaString || '',
                edu: j.degreeString || '不限',
                exp: j.workYearString || '不限',
                industry: j.industryType1Str || '',
                company_type: j.companyTypeString || '',
                scale: j.companySizeString || '',
                href: j.jobId ? 'https://jobs.51job.com/all/co' + j.jobId + '.html' : (j.jobHref || '')
            }}))));
        }}).catch(e => reject(e.message));
    }});
}})()
"""
    value = _cdp_eval(ws_url, js_code, timeout=15)
    if value and isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            pass
    return []


# ── BOSS 直聘爬虫 ─────────────────────────────────────────────────────────────

# 单页爬取 JS，每次只爬一页，避免大循环超时
_BOSS_PAGE_JS = """
(async () => {{
  try {{
    const body = `page={page}&pageSize=15&city=100010000&query={keyword}&expectInfo=&multiSubway=&multiBusinessDistrict=&position=&jobType=&salary=&experience=&degree=&industry=&scale=&stage=&scene=1&encryptExpectId=`;
    const r = await fetch('/wapi/zpgeek/search/joblist.json?_=' + Date.now(), {{
      method: 'POST',
      headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
      body: body
    }});
    const data = await r.json();
    const code = data?.code;
    const list = data?.zpData?.jobList || [];
    if (code !== 0) {{
      return JSON.stringify({{ok: false, code: code, msg: data?.message || '', jobs: []}});
    }}
    const jobs = list.map(j => {{
      const encryptJobId = j.encryptJobId || '';
      return {{
        name: j.jobName || '',
        company: j.brandName || '',
        salary: j.salaryDesc || '面议',
        city: j.cityName || '',
        edu: j.jobDegree || '不限',
        exp: j.jobExperience || '不限',
        industry: j.brandIndustry || '',
        scale: j.brandScaleName || '',
        skills: (j.skills || []).join(','),
        href: encryptJobId ? 'https://www.zhipin.com/job_detail/' + encryptJobId + '.html' : ''
      }};
    }});
    return JSON.stringify({{ok: true, code: code, jobs: jobs, hasMore: list.length >= 15}});
  }} catch(e) {{
    return JSON.stringify({{ok: false, code: -1, msg: e.message, jobs: []}});
  }}
}})()
"""


def crawl_boss_via_browser(keyword: str, pages: int = 5) -> list[dict]:
    """
    通过 jshook 浏览器爬取 BOSS 直聘，逐页调用避免大循环超时
    """
    if not is_boss_available():
        logger.warning('[BOSS] jshook 浏览器未运行或未打开 zhipin.com，跳过')
        return []

    ws_url = _get_tab_ws('zhipin')
    if not ws_url:
        logger.warning('[BOSS] 无法获取 zhipin WebSocket URL')
        return []

    _inject_stealth(ws_url)

    all_jobs = []
    seen_keys = set()
    import random as _random

    for page in range(1, pages + 1):
        js = _BOSS_PAGE_JS.format(keyword=keyword, page=page)
        value = _cdp_eval(ws_url, js, timeout=20)

        if not value:
            logger.warning(f'[BOSS] {keyword} 第{page}页 CDP 无返回，停止')
            break

        try:
            parsed = json.loads(value)
        except Exception as e:
            logger.error(f'[BOSS] {keyword} 第{page}页 JSON 解析失败: {e}, raw={value[:200]}')
            break

        if not parsed.get('ok'):
            code = parsed.get('code', -1)
            msg = parsed.get('msg', '')
            logger.warning(f'[BOSS] {keyword} 第{page}页 API 返回错误 code={code} msg={msg}')
            if code in (35, 40, -1):
                # 风控或频率限制，等待后重试一次
                wait = _random.uniform(8, 15)
                logger.info(f'[BOSS] 触发风控，等待 {wait:.1f}s 后重试...')
                time.sleep(wait)
                value2 = _cdp_eval(ws_url, js, timeout=20)
                if value2:
                    try:
                        parsed2 = json.loads(value2)
                        if parsed2.get('ok'):
                            parsed = parsed2
                        else:
                            logger.warning(f'[BOSS] 重试仍失败 code={parsed2.get("code")}，停止本关键词')
                            break
                    except Exception:
                        break
                else:
                    break
            else:
                break

        page_jobs = parsed.get('jobs', [])
        logger.info(f'[BOSS] {keyword} 第{page}页获取 {len(page_jobs)} 条')

        if not page_jobs:
            logger.info(f'[BOSS] {keyword} 第{page}页为空，停止翻页')
            break

        for j in page_jobs:
            key = j.get('name', '') + '|' + j.get('company', '')
            if key not in seen_keys:
                seen_keys.add(key)
                all_jobs.append(j)

        # 不足15条说明是最后一页
        if not parsed.get('hasMore', True):
            logger.info(f'[BOSS] {keyword} 第{page}页已是最后一页')
            break

        # 模拟人类浏览间隔：3~8秒，每隔3页额外休息
        wait = _random.uniform(3, 8)
        if page % 3 == 0:
            wait += _random.uniform(5, 10)
        logger.info(f'[BOSS] 翻页等待 {wait:.1f}s...')
        time.sleep(wait)

    logger.info(f'[BOSS] {keyword} 共获取 {len(all_jobs)} 条')
    return all_jobs

def _inject_stealth(ws_url: str):
    """通过 CDP 注入 stealth 脚本，绕过自动化检测"""
    stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']});
        window.chrome = window.chrome || {runtime: {}};
        Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({state: Notification.permission})
                : originalQuery(parameters);
    """
    try:
        import websocket as _ws
        import json as _json
        ws = _ws.create_connection(
            ws_url, timeout=8,
            origin='http://localhost:9222',
            header={'Host': 'localhost:9222'},
        )
        # 注入到新文档（持久生效）
        ws.send(_json.dumps({
            'id': 9001,
            'method': 'Page.addScriptToEvaluateOnNewDocument',
            'params': {'source': stealth_js}
        }))
        ws.recv()
        # 同时在当前页面立即执行一次
        ws.send(_json.dumps({
            'id': 9002,
            'method': 'Runtime.evaluate',
            'params': {'expression': stealth_js, 'returnByValue': False}
        }))
        ws.recv()
        ws.close()
        logger.info('[BOSS] stealth 脚本注入成功')
    except Exception as e:
        logger.warning(f'[BOSS] stealth 注入失败（不影响爬取）: {e}')
