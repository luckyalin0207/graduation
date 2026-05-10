"""
企业信息查询服务 — 多源策略
优先级（从高到低）：
  1. 企查查 Open API  — 付费，配置 QICHACHA_KEY + QICHACHA_SECRET
  2. 天眼查 Open API  — 付费，配置 TIANYANCHA_TOKEN
  3. 职位库本地数据   — 从已爬取的职位数据中聚合企业信息（无需外部请求）
  4. 爱企查 HTML 解析 — 免费，反爬较强，作为补充
  5. 国家企业信用信息公示系统 — 官方免费，反爬较强，作为兜底
"""
import os
import re
import time
import json
import logging
import hashlib
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 12
CACHE_HOURS = 24  # 缓存有效期（小时）

# ── 通用 Session ──────────────────────────────────────────────

def _session(extra_headers: dict = None) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': 'application/json, text/html, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    })
    if extra_headers:
        s.headers.update(extra_headers)
    return s


# ══════════════════════════════════════════════════════════════
# 数据源 1：企查查 Open API（付费）
# 申请：https://openapi.qcc.com/
# ══════════════════════════════════════════════════════════════

def query_qichacha(company_name: str) -> dict:
    api_key = os.getenv('QICHACHA_KEY', '') or getattr(settings, 'QICHACHA_KEY', '')
    api_secret = os.getenv('QICHACHA_SECRET', '') or getattr(settings, 'QICHACHA_SECRET', '')

    if not api_key or not api_secret:
        return _err('qichacha', '未配置企查查 API Key')

    try:
        timestamp = str(int(time.time()))
        token = hashlib.md5(f'{api_key}{timestamp}{api_secret}'.encode()).hexdigest().upper()

        s = _session({'Token': token, 'Timespan': timestamp})
        url = 'https://api.qichacha.com/ECIV4/GetBasicDetailsByName'
        resp = s.get(url, params={'key': api_key, 'keyword': company_name}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if data.get('Status') == '200' and data.get('Data'):
            c = data['Data']
            contact = c.get('ContactInfo') or {}
            if isinstance(contact, str):
                contact = {}
            return _ok('qichacha', {
                'company_name': c.get('Name', company_name),
                'unified_code': c.get('CreditCode', ''),
                'legal_person': c.get('OperName', ''),
                'registered_capital': c.get('RegistCapi', ''),
                'establishment_date': c.get('StartDate', ''),
                'business_status': c.get('Status', ''),
                'registered_address': c.get('Address', ''),
                'business_scope': c.get('Scope', ''),
                'company_type': c.get('EconKind', ''),
                'phone': contact.get('Tel', ''),
                'website': contact.get('WebSite', ''),
            })
        return _not_found('qichacha', data.get('Message', '未找到'))
    except Exception as e:
        logger.warning(f'[企查查] {company_name}: {e}')
        return _err('qichacha', str(e))


# ══════════════════════════════════════════════════════════════
# 数据源 2：天眼查 Open API（付费）
# 申请：https://www.tianyancha.com/cloud-other-information/openApi.html
# ══════════════════════════════════════════════════════════════

def query_tianyancha(company_name: str) -> dict:
    token = os.getenv('TIANYANCHA_TOKEN', '') or getattr(settings, 'TIANYANCHA_TOKEN', '')

    if not token:
        return _err('tianyancha', '未配置天眼查 Token')

    try:
        s = _session({'Authorization': token, 'Content-Type': 'application/json'})
        url = 'https://open.tianyancha.com/services/v4/search/companyV2'
        resp = s.get(url, params={'word': company_name, 'pageSize': 1, 'pageNum': 1},
                     timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        items = data.get('data', {}).get('items', [])
        if data.get('state') == 'ok' and items:
            c = items[0]
            return _ok('tianyancha', {
                'company_name': c.get('name', company_name),
                'unified_code': c.get('creditCode', ''),
                'legal_person': c.get('legalPersonName', ''),
                'registered_capital': c.get('regCapital', ''),
                'establishment_date': _ts_to_date(c.get('estiblishTime')),
                'business_status': c.get('regStatus', ''),
                'registered_address': c.get('regLocation', ''),
                'company_type': c.get('companyOrgType', ''),
                'industry': c.get('industry', ''),
                'staff_size': c.get('staffNumRange', ''),
                'phone': c.get('phoneNumber', ''),
                'website': c.get('websiteList', ''),
                'risk_count': int(c.get('riskCount') or 0),
                'lawsuit_count': int(c.get('lawSuitCount') or 0),
                'dishonest_count': int(c.get('dishonestCount') or 0),
            })
        return _not_found('tianyancha', '未找到企业信息')
    except Exception as e:
        logger.warning(f'[天眼查] {company_name}: {e}')
        return _err('tianyancha', str(e))


# ══════════════════════════════════════════════════════════════
# 数据源 3：本地职位库聚合（最可靠，无需外部请求）
# 从已爬取的职位数据中提取该公司的信息
# ══════════════════════════════════════════════════════════════

def query_local_jobs(company_name: str) -> dict:
    """
    从本地职位数据库中聚合企业信息。
    优点：完全离线，速度快，数据来自真实爬取。
    缺点：只有爬虫抓到的字段，没有统一信用代码等工商信息。
    """
    try:
        from jobs.models import JobData
        from django.db.models import Count, Q

        # 精确匹配 + 模糊匹配
        jobs = JobData.objects.filter(
            Q(company=company_name) | Q(company__icontains=company_name)
        ).order_by('-created_at')

        if not jobs.exists():
            return _not_found('local', '本地数据库中未找到该企业')

        # 取最新的一条作为基准
        latest = jobs.first()

        # 统计各字段最常见的值
        def most_common(field):
            result = (jobs.values(field)
                      .annotate(cnt=Count(field))
                      .order_by('-cnt')
                      .first())
            return result[field] if result else ''

        company_type = most_common('company_type') or latest.company_type or ''
        scale        = most_common('scale')        or latest.scale        or ''
        industry     = most_common('industry')     or latest.industry     or ''

        # 职位数量
        job_count = jobs.count()

        # 薪资范围
        from django.db.models import Avg, Min, Max
        salary_stats = jobs.filter(
            salary_min__isnull=False, salary_max__isnull=False
        ).aggregate(
            min_sal=Min('salary_min'),
            max_sal=Max('salary_max'),
            avg_sal=Avg('salary_min'),
        )

        salary_range = ''
        if salary_stats['min_sal'] and salary_stats['max_sal']:
            salary_range = f"{salary_stats['min_sal']:.0f}K - {salary_stats['max_sal']:.0f}K/月"

        # 在招城市
        cities = list(
            jobs.values_list('city', flat=True)
            .exclude(city='').exclude(city__isnull=True)
            .distinct()[:5]
        )

        return _ok('local', {
            'company_name': latest.company,
            'unified_code': '',
            'legal_person': '',
            'registered_capital': '',
            'establishment_date': '',
            'business_status': '存续',   # 有在招职位说明企业在运营
            'registered_address': '',
            'business_scope': '',
            'company_type': company_type,
            'industry': industry,
            'staff_size': scale,
            'phone': '',
            'website': '',
            'risk_count': 0,
            'lawsuit_count': 0,
            'dishonest_count': 0,
            # 额外字段
            'job_count': job_count,
            'salary_range': salary_range,
            'cities': ', '.join(cities),
            'data_source_note': f'数据来源：本地职位库（共 {job_count} 条在招职位）',
        })
    except Exception as e:
        logger.warning(f'[本地职位库] {company_name}: {e}')
        return _err('local', str(e))


# ══════════════════════════════════════════════════════════════
# 数据源 4：爱企查（百度）— 免费，无需 Key
# 使用其内嵌的搜索 API，比直接解析 HTML 更稳定
# ══════════════════════════════════════════════════════════════

def query_aiqicha(company_name: str) -> dict:
    """
    爱企查免费查询。
    策略：先尝试内嵌 JSON API，失败则解析搜索结果页 HTML。
    """
    # ── 方案 A：内嵌搜索 API ─────────────────────────────────
    try:
        s = _session({
            'Referer': 'https://aiqicha.baidu.com/',
            'Origin': 'https://aiqicha.baidu.com',
        })
        # 爱企查搜索接口（从页面 XHR 中提取）
        api_url = 'https://aiqicha.baidu.com/api/search/companyList'
        params = {
            'query': company_name,
            'pageIndex': 1,
            'pageSize': 5,
        }
        resp = s.get(api_url, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            try:
                data = resp.json()
                items = (data.get('data') or {}).get('resultList') or []
                if items:
                    return _ok('aiqicha', _parse_aiqicha_item(items[0], company_name))
            except Exception:
                pass
    except Exception:
        pass

    # ── 方案 B：搜索结果页 HTML 解析 ─────────────────────────
    try:
        s = _session({'Referer': 'https://aiqicha.baidu.com/'})
        resp = s.get(
            'https://aiqicha.baidu.com/s',
            params={'q': company_name, 'p': 1},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            html = resp.text

            # 尝试提取页面内嵌 JSON（__INITIAL_STATE__）
            m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*(?:;|</script>)', html, re.DOTALL)
            if m:
                try:
                    state = json.loads(m.group(1))
                    # 路径可能是 searchResult.resultList 或 data.resultList
                    result_list = (
                        state.get('searchResult', {}).get('resultList')
                        or state.get('data', {}).get('resultList')
                        or []
                    )
                    if result_list:
                        return _ok('aiqicha', _parse_aiqicha_item(result_list[0], company_name))
                except Exception:
                    pass

            # 最后兜底：正则提取关键字段
            parsed = _regex_extract(html, company_name)
            if parsed:
                return _ok('aiqicha', parsed)

        return _not_found('aiqicha', '未找到企业信息')
    except requests.Timeout:
        return _err('aiqicha', '请求超时')
    except Exception as e:
        logger.warning(f'[爱企查] {company_name}: {e}')
        return _err('aiqicha', str(e))


def _parse_aiqicha_item(item: dict, company_name: str) -> dict:
    """统一解析爱企查返回的企业条目"""
    return {
        'company_name': item.get('entName') or item.get('name') or company_name,
        'unified_code': item.get('uniscId') or item.get('creditCode') or '',
        'legal_person': item.get('legalPerson') or item.get('legalName') or '',
        'registered_capital': item.get('regCapital') or item.get('registeredCapital') or '',
        'establishment_date': item.get('startDate') or item.get('openTime') or '',
        'business_status': item.get('openStatus') or item.get('status') or '',
        'registered_address': item.get('regAddr') or item.get('address') or '',
        'company_type': item.get('entType') or item.get('companyType') or '',
        'industry': item.get('industry') or '',
        'staff_size': item.get('staffSize') or item.get('scale') or '',
        'phone': item.get('phoneNum') or item.get('phone') or '',
        'website': item.get('website') or '',
        'risk_count': int(item.get('riskCount') or 0),
        'lawsuit_count': int(item.get('lawsuitCount') or 0),
        'dishonest_count': int(item.get('dishonestCount') or 0),
    }


def _regex_extract(html: str, company_name: str) -> dict | None:
    """从 HTML 中用正则提取关键字段（最后兜底）"""
    data = {'company_name': company_name}

    patterns = [
        ('unified_code', r'统一社会信用代码[：:]\s*([A-Z0-9]{18})'),
        ('legal_person', r'法定代表人[：:]\s*([^\s<"]{2,10})'),
        ('registered_capital', r'注册资本[：:]\s*([^\s<"]{1,30}(?:万元|亿元|美元|港元))'),
        ('establishment_date', r'成立[日期时间]*[：:]\s*(\d{4}[-年]\d{1,2}[-月]\d{1,2})'),
        ('registered_address', r'注册地址[：:]\s*([^<"]{5,100})'),
    ]
    for key, pattern in patterns:
        m = re.search(pattern, html)
        if m:
            data[key] = m.group(1).strip()

    # 经营状态
    m = re.search(r'(存续|注销|吊销|迁出|撤销|正常|开业|在营)', html)
    if m:
        data['business_status'] = m.group(1)

    return data if len(data) > 2 else None


# ══════════════════════════════════════════════════════════════
# 数据源 4：国家企业信用信息公示系统（官方，兜底）
# ══════════════════════════════════════════════════════════════

def query_gsxt(company_name: str) -> dict:
    """
    国家企业信用信息公示系统（gsxt.gov.cn）。
    官方权威，完全免费，但有验证码保护，成功率较低。
    """
    try:
        s = _session({'Referer': 'https://www.gsxt.gov.cn/'})
        # 使用市场监管总局的企业查询接口
        url = 'https://www.gsxt.gov.cn/corp-query-search-1.html'
        resp = s.get(url, params={'searchword': company_name}, timeout=REQUEST_TIMEOUT)

        if resp.status_code == 200:
            html = resp.text
            data = _parse_gsxt_html(html, company_name)
            if data:
                return _ok('gsxt', data)

        return _not_found('gsxt', '未找到或需要验证码')
    except Exception as e:
        logger.debug(f'[国家信用系统] {company_name}: {e}')
        return _err('gsxt', str(e))


def _parse_gsxt_html(html: str, company_name: str) -> dict | None:
    data = {'company_name': company_name}
    patterns = [
        ('unified_code', r'([A-Z0-9]{18})'),
        ('legal_person', r'法定代表人[：:]\s*<[^>]*>([^<]{2,10})'),
        ('registered_capital', r'注册资本[：:]\s*<[^>]*>([^<]{1,30})'),
        ('establishment_date', r'成立日期[：:]\s*<[^>]*>(\d{4}-\d{2}-\d{2})'),
        ('business_status', r'登记状态[：:]\s*<[^>]*>([^<]{2,10})'),
        ('registered_address', r'住所[：:]\s*<[^>]*>([^<]{5,200})'),
    ]
    for key, pattern in patterns:
        m = re.search(pattern, html)
        if m:
            data[key] = m.group(1).strip()
    return data if len(data) > 2 else None


# ══════════════════════════════════════════════════════════════
# 统一查询入口
# ══════════════════════════════════════════════════════════════

def verify_company(company_name: str, force_refresh: bool = False) -> dict:
    """
    统一企业信息验证入口。
    策略：
    1. 优先读缓存（24h 内有效）
    2. 付费 API（企查查/天眼查）— 数据最全
    3. 本地职位库聚合 — 离线可用，速度快
    4. 爱企查 HTML 解析 — 在线免费，反爬较强
    5. 国家信用系统 — 官方权威，反爬最强
    """
    company_name = company_name.strip()
    if not company_name:
        return _err('', '公司名称不能为空')

    # ── 读缓存 ────────────────────────────────────────────────
    if not force_refresh:
        cached = _get_cache(company_name)
        if cached:
            return cached

    # ── 付费 API 优先 ─────────────────────────────────────────
    if os.getenv('QICHACHA_KEY'):
        result = query_qichacha(company_name)
        if result['status'] == 'verified':
            _save(company_name, result)
            return result

    if os.getenv('TIANYANCHA_TOKEN'):
        result = query_tianyancha(company_name)
        if result['status'] == 'verified':
            _save(company_name, result)
            return result

    # ── 本地职位库（离线，最可靠）────────────────────────────
    local_result = query_local_jobs(company_name)
    if local_result['status'] == 'verified':
        # 尝试用爱企查补充工商信息（不阻塞，失败就用本地数据）
        try:
            online = query_aiqicha(company_name)
            if online['status'] == 'verified':
                # 合并：用在线数据补充本地没有的字段
                merged_data = local_result['data'].copy()
                online_data = online['data']
                for key in ['unified_code', 'legal_person', 'registered_capital',
                            'establishment_date', 'business_status', 'registered_address',
                            'business_scope', 'risk_count', 'lawsuit_count', 'dishonest_count']:
                    if online_data.get(key):
                        merged_data[key] = online_data[key]
                merged_result = _ok('aiqicha', merged_data)
                _save(company_name, merged_result)
                return merged_result
        except Exception:
            pass

        # 在线查询失败，直接用本地数据
        _save(company_name, local_result)
        return local_result

    # ── 纯在线查询（本地也没有数据时）────────────────────────
    online = query_aiqicha(company_name)
    if online['status'] == 'verified':
        _save(company_name, online)
        return online

    gsxt = query_gsxt(company_name)
    if gsxt['status'] == 'verified':
        _save(company_name, gsxt)
        return gsxt

    # 全部失败
    final = online if online['status'] != 'error' else gsxt
    _save(company_name, final)
    return final


# ══════════════════════════════════════════════════════════════
# 缓存读写
# ══════════════════════════════════════════════════════════════

def _get_cache(company_name: str) -> dict | None:
    from .models import CompanyVerification
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(hours=CACHE_HOURS)
    try:
        obj = CompanyVerification.objects.get(
            company_name=company_name,
            status__in=['verified', 'not_found'],
            verified_at__gte=cutoff,
        )
        return _model_to_dict(obj)
    except Exception:
        return None


def _save(company_name: str, result: dict):
    from .models import CompanyVerification
    data = result.get('data') or {}
    try:
        obj, _ = CompanyVerification.objects.update_or_create(
            company_name=company_name,
            defaults={
                'status': result.get('status', 'error'),
                'source': result.get('source', 'aiqicha'),
                'unified_code': data.get('unified_code') or '',
                'legal_person': data.get('legal_person') or '',
                'registered_capital': data.get('registered_capital') or '',
                'establishment_date': data.get('establishment_date') or '',
                'business_status': data.get('business_status') or '',
                'registered_address': data.get('registered_address') or '',
                'business_scope': data.get('business_scope') or '',
                'company_type': data.get('company_type') or '',
                'industry': data.get('industry') or '',
                'staff_size': data.get('staff_size') or '',
                'phone': data.get('phone') or '',
                'email': data.get('email') or '',
                'website': data.get('website') or '',
                'risk_count': int(data.get('risk_count') or 0),
                'lawsuit_count': int(data.get('lawsuit_count') or 0),
                'dishonest_count': int(data.get('dishonest_count') or 0),
                'raw_data': data,
            }
        )
        # 计算风险等级
        total = obj.risk_count + obj.lawsuit_count + obj.dishonest_count
        if not obj.is_normal and obj.business_status:
            obj.risk_level = '高'
        elif total == 0:
            obj.risk_level = '低'
        elif total <= 5:
            obj.risk_level = '中'
        else:
            obj.risk_level = '高'
        obj.save(update_fields=['risk_level'])
    except Exception as e:
        logger.warning(f'保存企业验证结果失败: {e}')


def _model_to_dict(obj) -> dict:
    raw = obj.raw_data or {}
    return {
        'status': obj.status,
        'source': obj.source,
        'cached': True,
        'verified_at': obj.verified_at.strftime('%Y-%m-%d %H:%M') if obj.verified_at else None,
        'data': {
            'company_name': obj.company_name,
            'unified_code': obj.unified_code,
            'legal_person': obj.legal_person,
            'registered_capital': obj.registered_capital,
            'establishment_date': obj.establishment_date,
            'business_status': obj.business_status,
            'registered_address': obj.registered_address,
            'business_scope': obj.business_scope,
            'company_type': obj.company_type,
            'industry': obj.industry,
            'staff_size': obj.staff_size,
            'phone': obj.phone,
            'email': obj.email,
            'website': obj.website,
            'risk_count': obj.risk_count,
            'lawsuit_count': obj.lawsuit_count,
            'dishonest_count': obj.dishonest_count,
            'risk_level': obj.risk_level,
            'risk_summary': obj.risk_summary,
            'is_normal': obj.is_normal,
            # 本地数据额外字段
            'job_count': raw.get('job_count', 0),
            'salary_range': raw.get('salary_range', ''),
            'cities': raw.get('cities', ''),
            'data_source_note': raw.get('data_source_note', ''),
        },
    }


# ══════════════════════════════════════════════════════════════
# 辅助函数
# ══════════════════════════════════════════════════════════════

def _ok(source: str, data: dict) -> dict:
    return {'status': 'verified', 'source': source, 'cached': False, 'data': data}

def _not_found(source: str, msg: str = '') -> dict:
    return {'status': 'not_found', 'source': source, 'cached': False, 'data': {}, 'message': msg}

def _err(source: str, msg: str) -> dict:
    return {'status': 'error', 'source': source, 'cached': False, 'data': {}, 'message': msg}

def _ts_to_date(ts) -> str:
    """毫秒时间戳转日期字符串"""
    if not ts:
        return ''
    try:
        import datetime
        return datetime.datetime.fromtimestamp(int(ts) / 1000).strftime('%Y-%m-%d')
    except Exception:
        return str(ts)
