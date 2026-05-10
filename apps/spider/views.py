from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from .models import SpiderInfo
from jobs.models import JobData
import threading
import time
import re
import uuid
import csv
import io
import json


def spider_manage(request):
    """爬虫管理页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    spider_info = SpiderInfo.objects.first()
    if not spider_info:
        spider_info = SpiderInfo.objects.create(
            spider_name='前程无忧爬虫',
            target_site='51job.com',
            status=0,
            total_count=0,
            run_count=0
        )
    
    return render(request, "spider/spider_manage.html", {'spider_info': spider_info})


def get_spider_status(request):
    """获取爬虫状态"""
    spider_info = SpiderInfo.objects.first()
    if spider_info:
        data = {
            'status': spider_info.status,
            'total_count': spider_info.total_count,
            'last_new_count': spider_info.last_new_count,
            'run_count': spider_info.run_count,
            'last_run_time': spider_info.last_run_time.strftime('%Y-%m-%d %H:%M:%S') if spider_info.last_run_time else None
        }
    else:
        data = {'status': 0, 'total_count': 0, 'last_new_count': 0, 'run_count': 0, 'last_run_time': None}
    
    return JsonResponse({'code': 0, 'data': data})


def get_spider_mode(request):
    """检测当前可用的爬取模式"""
    from .browser_crawler import is_browser_available, is_boss_available
    return JsonResponse({
        'browser_available': is_browser_available(),
        'boss_available': is_boss_available(),
    })


def start_spider(request):
    """启动爬虫"""
    if request.method != 'POST':
        return JsonResponse({'code': 1, 'msg': '请求方式错误'})
    
    spider_info = SpiderInfo.objects.first()
    if spider_info and spider_info.status == 1:
        return JsonResponse({'code': 1, 'msg': '爬虫正在运行中，请稍后再试'})
    
    # 支持三种模式：
    # 1. 指定关键词：keyword="Python,Java"
    # 2. 随机模式：keyword="random" 或 use_random=true
    # 3. 空值默认随机
    keyword_raw = request.POST.get('keyword', '').strip()
    use_random = request.POST.get('use_random', 'false').lower() == 'true'
    random_count = int(request.POST.get('random_count', 5))  # 随机选择的关键词数量
    
    if not keyword_raw or keyword_raw.lower() == 'random' or use_random:
        # 随机模式：从关键词池中随机选择
        import random
        keywords = _get_random_keywords(random_count)
        mode_desc = f'随机模式（{len(keywords)}个关键词）'
    else:
        # 指定关键词模式
        keywords = [k.strip() for k in keyword_raw.split(',') if k.strip()]
        if not keywords:
            keywords = _get_random_keywords(random_count)
            mode_desc = f'随机模式（{len(keywords)}个关键词）'
        else:
            mode_desc = f'指定关键词模式（{len(keywords)}个）'
    
    pages = int(request.POST.get('pages', 3))
    cookie = request.POST.get('cookie', '')
    max_workers = int(request.POST.get('max_workers', 3))

    # 启动爬虫线程
    thread = threading.Thread(target=run_spider_batch, args=(keywords, pages, cookie, max_workers))
    thread.daemon = True
    thread.start()

    from .browser_crawler import is_browser_available
    browser_mode = 'jshook 浏览器模式' if is_browser_available() else 'requests 模式'
    return JsonResponse({
        'code': 0, 
        'msg': f'爬虫已启动 - {mode_desc}，{max_workers}个并行进程', 
        'mode': browser_mode,
        'keywords': keywords
    })


def _get_random_keywords(count=5):
    """
    从关键词池中随机选择指定数量的关键词
    涵盖技术、产品、运营、设计、职能等多个领域
    """
    import random
    
    KEYWORD_POOL = [
        # 技术开发类
        'Python', 'Java', 'Go', 'C++', 'JavaScript', 'TypeScript', 'Rust', 'Kotlin',
        '前端开发', '后端开发', '全栈开发', 'Node.js', 'PHP', 'Ruby',
        'Android', 'iOS', 'Flutter', 'React Native',
        
        # 数据与AI类
        '大数据', '数据分析', '数据挖掘', '机器学习', '深度学习', 'AI工程师',
        '算法工程师', 'NLP', '计算机视觉', '推荐系统',
        
        # 运维与架构类
        'DevOps', '运维工程师', '云计算', '架构师', '网络安全', '信息安全',
        'DBA', 'SRE', 'Kubernetes', 'Docker',
        
        # 测试与质量类
        '测试工程师', '自动化测试', '性能测试', 'QA',
        
        # 产品与设计类
        '产品经理', '产品运营', 'UI设计', 'UX设计', '平面设计', '视频剪辑',
        '交互设计', '用户研究',
        
        # 运营与市场类
        '运营', '新媒体运营', '内容运营', '用户运营', '电商运营',
        '市场营销', '品牌推广', 'SEO', 'SEM',
        
        # 职能支持类
        '人力资源', 'HR', '财务会计', '项目管理', '销售', '客服',
        '供应链', '采购', '行政', '法务',
        
        # 其他专业类
        '教育培训', '金融分析', '咨询顾问', '嵌入式', '游戏开发',
        '区块链', '物联网', '5G', '芯片设计',
    ]
    
    # 确保不超过池子大小
    actual_count = min(count, len(KEYWORD_POOL))
    return random.sample(KEYWORD_POOL, actual_count)


def run_spider_batch(keywords, pages, cookie='', max_workers=3):
    """
    多进程并行爬取多个关键词
    - 每个关键词一个独立进程（独立 Chrome 实例）
    - 每个进程使用代理池轮换 IP
    - max_workers: 最大并行进程数，建议 2-4，太多内存撑不住
    """
    import multiprocessing as mp

    spider_info, _ = SpiderInfo.objects.get_or_create(
        pk=1,
        defaults={
            'spider_name': '前程无忧爬虫',
            'target_site': '51job.com',
            'status': 0,
            'total_count': 0,
            'run_count': 0,
        }
    )
    spider_info.status = 1
    spider_info.save()

    print(f"[并行爬取] 关键词: {keywords}，每词 {pages} 页，最大并行 {max_workers} 个进程")
    print(f"[并行爬取] ⚠️ 注意：51job API通常只返回前3-5页数据，建议每词不超过5页")

    # 提前统一获取 Cookie，避免多线程并发刷新冲突
    from .cookie_manager import get_cookie_manager
    mgr = get_cookie_manager()
    if cookie and cookie.strip():
        mgr.set_manual(cookie)
    effective_cookie = mgr.get()
    if not effective_cookie:
        print("[并行爬取] 无法获取 Cookie，将尝试使用浏览器模式")
        effective_cookie = ''
    else:
        print(f"[并行爬取] Cookie 就绪（长度 {len(effective_cookie)}）")

    # 用进程池并行，每个关键词一个进程
    results = []
    try:
        # Windows 下 multiprocessing 需要 spawn，Django ORM 不能跨进程直接用
        # 改用多线程（每线程独立 Chrome），避免 Django ORM 跨进程问题
        from concurrent.futures import ThreadPoolExecutor, as_completed
        futures = {}
        
        # 🔧 修复：降低并行数，避免浏览器资源冲突
        actual_workers = min(max_workers, len(keywords), 2)  # 最多2个并行
        print(f"[并行爬取] 实际并行数：{actual_workers}（避免浏览器资源冲突）")
        
        with ThreadPoolExecutor(max_workers=actual_workers) as executor:
            for kw in keywords:
                f = executor.submit(_crawl_one_keyword, kw, pages, effective_cookie)
                futures[f] = kw

        total_count = 0
        success_count = 0
        for f in as_completed(futures):
            kw = futures[f]
            try:
                count = f.result()
                total_count += count
                if count > 0:
                    success_count += 1
                print(f"[并行爬取] [{kw}] 完成，+{count} 条")
            except Exception as e:
                print(f"[并行爬取] [{kw}] 出错: {e}")
                import traceback
                traceback.print_exc()

        print(f"[并行爬取] 全部完成，{success_count}/{len(keywords)} 个关键词成功，本次共 {total_count} 条")

    except Exception as e:
        print(f"[并行爬取] 出错: {e}")
        import traceback
        traceback.print_exc()
        total_count = 0
    finally:
        spider_info.refresh_from_db()
        spider_info.status = 0
        spider_info.total_count += total_count
        spider_info.last_new_count = total_count
        spider_info.run_count += 1
        spider_info.last_run_time = timezone.now()
        spider_info.save()
        print(f"[并行爬取] 统计：本次新增 {total_count} 条，累计 {spider_info.total_count} 条")


def _crawl_one_keyword(keyword, pages, cookie=''):
    """
    单关键词爬取
    优先用浏览器内 axios（不需要 Cookie，自动处理 sign）
    降级到 requests + Cookie
    """
    import time as _time
    import random

    from .browser_crawler import crawl_via_browser, is_browser_available

    count = 0
    use_browser = is_browser_available()
    empty_page_count = 0  # 连续空页计数
    MAX_EMPTY_PAGES = 3   # 连续3页为空则停止

    if use_browser:
        print(f"[{keyword}] 使用浏览器模式（自动 sign）")
    else:
        print(f"[{keyword}] 使用 requests 模式（需要 Cookie）")

    for page in range(1, pages + 1):
        try:
            jobs = []
            
            if use_browser:
                jobs = crawl_via_browser(keyword, page)
                if not jobs:
                    print(f"[{keyword}] 第{page}页浏览器返回空，降级到 requests")
                    use_browser = False
            
            if not use_browser:
                jobs = _crawl_page_requests(keyword, page, cookie)
                if jobs is None:  # 被拦截
                    print(f"[{keyword}] 第{page}页被拦截，停止爬取")
                    break

            # 检查是否返回空数据
            if not jobs or len(jobs) == 0:
                empty_page_count += 1
                print(f"[{keyword}] 第{page}页返回空数据（连续{empty_page_count}页为空）")
                
                if empty_page_count >= MAX_EMPTY_PAGES:
                    print(f"[{keyword}] 连续{MAX_EMPTY_PAGES}页为空，可能已到达数据末尾，停止爬取")
                    break
                
                # 空页也要等待，避免请求过快
                _time.sleep(random.uniform(1.0, 2.0))
                continue
            else:
                empty_page_count = 0  # 重置空页计数

            page_count = 0
            duplicate_count = 0
            
            print(f"[{keyword}] 第{page}页获取到 {len(jobs)} 条原始数据")
            
            for job in jobs:
                name = job.get('name', '').strip() or job.get('jobName', '').strip()
                company = job.get('company', '').strip() or job.get('companyName', '').strip()
                if not name or not company:
                    continue

                salary_str = job.get('salary', '') or job.get('provideSalaryString', '') or '面议'
                city = job.get('city', '') or job.get('jobAreaString', '')
                edu = job.get('edu', '') or job.get('degreeString', '') or '不限'
                exp = job.get('exp', '') or job.get('workYearString', '') or '不限'
                industry = job.get('industry', '') or job.get('industryType1Str', '')
                company_type = job.get('company_type', '') or job.get('companyTypeString', '')
                scale = job.get('scale', '') or job.get('companySizeString', '')

                salary_min_raw = job.get('salary_min') or job.get('jobSalaryMin')
                salary_max_raw = job.get('salary_max') or job.get('jobSalaryMax')
                if salary_min_raw and salary_max_raw:
                    try:
                        salary_min = float(salary_min_raw) / 1000
                        salary_max = float(salary_max_raw) / 1000
                    except Exception:
                        salary_min, salary_max = parse_salary(salary_str)
                else:
                    salary_min, salary_max = parse_salary(salary_str)

                # 检查是否已存在：优先用 href（唯一职位链接）去重，无 href 时回退到 (name, company, city)
                href_val = job.get('href', '') or ''
                if href_val:
                    if JobData.objects.filter(href=href_val).exists():
                        duplicate_count += 1
                        continue
                else:
                    if JobData.objects.filter(name=name, company=company, city=city).exists():
                        duplicate_count += 1
                        continue
                
                JobData.objects.create(
                    name=name,
                    salary=salary_str,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    city=city,
                    place=city,
                    education=edu,
                    experience=exp,
                    company=company,
                    company_type=company_type,
                    scale=scale,
                    industry=industry,
                    key_word=keyword,
                    source='51job',
                    href=job.get('href', '') or '',
                )
                page_count += 1

            count += page_count
            
            if duplicate_count > 0:
                print(f"[{keyword}] 第{page}页 +{page_count} 条新数据，{duplicate_count} 条重复（累计 {count} 条）")
            else:
                print(f"[{keyword}] 第{page}页 +{page_count} 条新数据（累计 {count} 条）")
            
            # 如果这一页全是重复数据，说明已爬取到已有数据区域，停止继续翻页
            if page_count == 0 and len(jobs) > 0:
                print(f"[{keyword}] 第{page}页全部为重复数据，已爬取到最新内容，停止翻页")
                break
            
            _time.sleep(random.uniform(0.8, 1.5))

        except Exception as e:
            print(f"[{keyword}] 第{page}页出错: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"[{keyword}] 爬取完成，共获取 {count} 条新数据")
    return count


def _crawl_page_requests(keyword: str, page: int, cookie: str) -> list | None:
    """requests 方式爬取单页，返回 None 表示被拦截"""
    import requests
    import urllib.parse
    import time as _time

    if not cookie or not cookie.strip():
        return None

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Origin': 'https://we.51job.com',
    })
    for item in cookie.strip().split(';'):
        item = item.strip()
        if '=' not in item:
            continue
        name, _, value = item.partition('=')
        session.cookies.set(name.strip(), value.strip(), domain='.51job.com')

    keyword_encoded = urllib.parse.quote(keyword)
    ts = int(_time.time())
    params = {
        'api_key': '51job', 'timestamp': ts,
        'keyword': keyword, 'searchType': 2,
        'function': '', 'industry': '', 'jobArea': '',
        'jobArea2': '', 'landmark': '', 'metro': '',
        'salary': '', 'workYear': '', 'degree': '',
        'companyType': '', 'companySize': '', 'jobType': '', 'issueDate': '',
        'sortType': 0, 'pageNum': page, 'requestId': '',
        'pageSize': 20, 'source': 1, 'accountId': '',
        'pageCode': 'sou|sou|soulb', 'scene': 7, 'language': 0,
    }
    session.headers['Referer'] = (
        f'https://we.51job.com/pc/search?keyword={keyword_encoded}'
        f'&searchType=2&sortType=0&pageNum={page}&pageSize=20'
    )

    r = session.get('https://we.51job.com/api/job/search-pc', params=params, timeout=15)
    if r.status_code != 200 or r.text.strip().startswith('<'):
        from .cookie_manager import get_cookie_manager
        get_cookie_manager()._fetched_at = 0
        return None

    data = r.json()
    return data.get('resultbody', {}).get('job', {}).get('items', [])


def run_spider(keyword, pages, cookie=''):
    """单关键词爬取（向后兼容）"""
    run_spider_batch([keyword], pages, cookie)


def debug_boss_spider(request):
    """
    诊断接口：直接执行一次 BOSS 直聘 API 调用，返回原始结果
    访问：/spider/api/debug-boss/?keyword=Python
    """
    from .browser_crawler import _get_tab_ws, _cdp_eval, is_boss_available
    keyword = request.GET.get('keyword', 'Python')

    if not is_boss_available():
        return JsonResponse({'ok': False, 'error': '未检测到 BOSS 直聘标签页，请先在 jshook 浏览器打开 zhipin.com'})

    ws_url = _get_tab_ws('zhipin')
    if not ws_url:
        return JsonResponse({'ok': False, 'error': '无法获取 WebSocket URL'})

    # 单页诊断 JS，返回完整原始响应
    diag_js = f"""
(async () => {{
  try {{
    const body = `page=1&pageSize=15&city=100010000&query={keyword}&expectInfo=&multiSubway=&multiBusinessDistrict=&position=&jobType=&salary=&experience=&degree=&industry=&scale=&stage=&scene=1&encryptExpectId=`;
    const r = await fetch('/wapi/zpgeek/search/joblist.json?_=' + Date.now(), {{
      method: 'POST',
      headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
      body: body
    }});
    const text = await r.text();
    return JSON.stringify({{
      status: r.status,
      url: r.url,
      body_preview: text.substring(0, 500),
      is_json: text.trim().startsWith('{{')
    }});
  }} catch(e) {{
    return JSON.stringify({{error: e.message}});
  }}
}})()
"""
    value = _cdp_eval(ws_url, diag_js, timeout=15)
    if value:
        try:
            result = json.loads(value)
            return JsonResponse({'ok': True, 'ws_url': ws_url, 'result': result})
        except Exception:
            return JsonResponse({'ok': True, 'ws_url': ws_url, 'raw': value})
    return JsonResponse({'ok': False, 'error': 'CDP 调用无返回，可能超时或 WebSocket 连接失败'})


def import_csv(request):
    """从CSV文件导入数据"""
    if request.method == 'GET':
        return render(request, "spider/import_csv.html")
    
    if request.method == 'POST':
        
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            return JsonResponse({'code': 1, 'msg': '请选择CSV文件'})
        
        if not csv_file.name.endswith('.csv'):
            return JsonResponse({'code': 1, 'msg': '请上传CSV格式文件'})
        
        try:
            # 读取文件内容
            file_content = csv_file.read()
            
            # 尝试使用chardet自动检测编码
            decoded_file = None
            detected_encoding = None
            
            try:
                import chardet
                result = chardet.detect(file_content)
                detected_encoding = result.get('encoding')
                confidence = result.get('confidence', 0)
                
                # 如果检测置信度较高，优先使用检测到的编码
                if detected_encoding and confidence > 0.7:
                    try:
                        decoded_file = file_content.decode(detected_encoding)
                    except (UnicodeDecodeError, LookupError):
                        detected_encoding = None
            except ImportError:
                # 如果没有安装chardet，使用备选方案
                pass
            except Exception:
                # chardet检测失败，使用备选方案
                pass
            
            # 如果自动检测失败，尝试常见编码格式
            if decoded_file is None:
                encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'latin1', 'cp1252']
                
                for encoding in encodings:
                    try:
                        decoded_file = file_content.decode(encoding)
                        detected_encoding = encoding
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
            
            if decoded_file is None:
                return JsonResponse({
                    'code': 1, 
                    'msg': f'无法识别CSV文件编码。请尝试：1) 用Excel打开文件，另存为"CSV UTF-8"格式；2) 或用记事本打开，另存为UTF-8编码'
                })
            
            def normalize_text(value, default=''):
                if value is None:
                    return default
                text = str(value).strip()
                return text if text else default

            reader = csv.DictReader(io.StringIO(decoded_file))
            
            count = 0
            for row in reader:
                name = normalize_text(row.get('name', row.get('职位名称', '')))
                if not name:
                    continue
                
                salary = normalize_text(row.get('salary', row.get('薪资', '')))
                salary_min, salary_max = parse_salary(salary)
                company = normalize_text(row.get('company', row.get('公司', '')))
                city = normalize_text(row.get('city', row.get('城市', '')))

                # 简单去重：职位名+公司+城市
                if JobData.objects.filter(name=name, company=company, city=city).exists():
                    continue

                JobData.objects.create(
                    name=name,
                    salary=salary or '面议',
                    salary_min=salary_min,
                    salary_max=salary_max,
                    city=city,
                    place=normalize_text(row.get('place', row.get('地点', ''))),
                    education=normalize_text(row.get('education', row.get('学历', '不限')), '不限'),
                    experience=normalize_text(row.get('experience', row.get('经验', '不限')), '不限'),
                    company=company,
                    company_type=normalize_text(row.get('company_type', row.get('公司类型', ''))),
                    scale=normalize_text(row.get('scale', row.get('规模', ''))),
                    industry=normalize_text(row.get('industry', row.get('行业', ''))),
                    key_word=normalize_text(row.get('key_word', row.get('关键词', 'Python')), 'Python'),
                    source='CSV导入'
                )
                count += 1
            
            # 更新爬虫统计
            spider_info = SpiderInfo.objects.first()
            if spider_info:
                spider_info.total_count += count
                spider_info.run_count += 1
                spider_info.last_run_time = timezone.now()
                spider_info.save()
            
            return JsonResponse({'code': 0, 'msg': f'成功导入 {count} 条数据'})
        except Exception as e:
            return JsonResponse({'code': 1, 'msg': f'导入失败: {str(e)}'})


def parse_salary(salary_str):
    """解析薪资字符串"""
    if not salary_str:
        return None, None
    text = str(salary_str).strip()
    if not text or text in ['面议', '暂无']:
        return None, None

    def to_k(value, unit):
        """统一转换为K/月"""
        val = float(value)
        if unit in ['k', 'K', '千', '千/月', 'k/月', 'K/月']:
            return val
        if unit in ['万', '万/月']:
            return val * 10
        if unit in ['元', '元/月']:
            return val / 1000
        if unit in ['万/年']:
            return (val * 10) / 12
        if unit in ['元/年']:
            return (val / 1000) / 12
        if unit in ['k/年', 'K/年', '千/年']:
            return val / 12
        return val

    # 统一单位标记
    unit = None
    if '万/年' in text:
        unit = '万/年'
    elif '元/年' in text:
        unit = '元/年'
    elif 'k/年' in text.lower() or '千/年' in text:
        unit = 'k/年'
    elif '万/月' in text:
        unit = '万/月'
    elif '元/月' in text:
        unit = '元/月'
    elif 'k/月' in text.lower() or '千/月' in text:
        unit = 'k/月'
    elif '万' in text:
        unit = '万'
    elif '元' in text:
        unit = '元'
    elif 'k' in text.lower() or '千' in text:
        unit = 'K'

    # 匹配区间（允许数字后跟单位字符，如 15k-25k、1.5万-2万）
    match = re.search(r'(\d+\.?\d*)\s*[^\d\s.-]*\s*[-~]\s*(\d+\.?\d*)', text)
    if match:
        min_val = match.group(1)
        max_val = match.group(2)
        min_k = to_k(min_val, unit or 'K')
        max_k = to_k(max_val, unit or 'K')
        return min_k, max_k

    # 匹配单个数字
    match = re.search(r'(\d+\.?\d*)', text)
    if match:
        val_k = to_k(match.group(1), unit or 'K')
        return val_k, val_k

    return None, None


def scheduler_status(request):
    """获取定时任务状态"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    try:
        from .scheduler import get_scheduler
        scheduler = get_scheduler()
        jobs_info = scheduler.get_jobs_info() if scheduler.is_running else []
        return JsonResponse({
            'code': 0,
            'running': scheduler.is_running,
            'jobs': jobs_info,
        })
    except Exception as e:
        return JsonResponse({'code': 0, 'running': False, 'jobs': [], 'error': str(e)})


def get_source_stats(request):
    """获取各来源数据量统计"""
    from jobs.models import JobData
    from django.db.models import Count
    stats = (JobData.objects
             .values('source')
             .annotate(count=Count('job_id'))
             .order_by('-count'))
    data = [{'source': row['source'] or '未知', 'count': row['count']} for row in stats]
    return JsonResponse({'code': 0, 'data': data})


def open_boss_browser(request):
    """
    一键启动 Chrome（带 CDP 调试端口）并打开 zhipin.com
    关键：用独立 --user-data-dir 强制新进程，避免复用已有 Chrome 忽略调试端口参数
    """
    if request.method != 'POST':
        return JsonResponse({'code': 1, 'msg': '请求方式错误'})

    import subprocess
    import os
    import tempfile

    from .browser_crawler import is_boss_available
    if is_boss_available():
        return JsonResponse({'code': 0, 'msg': 'BOSS 直聘已就绪'})

    # 9222 端口已有浏览器但没有 zhipin 标签页 → 用 CDP 开新标签
    try:
        import requests as req
        r = req.get('http://localhost:9222/json', timeout=2)
        tabs = r.json()
        if tabs:
            import websocket, json as _json
            ws_url = tabs[0]['webSocketDebuggerUrl']
            ws = websocket.create_connection(
                ws_url, timeout=10,
                origin='http://localhost:9222',
                header={'Host': 'localhost:9222'},
            )
            ws.send(_json.dumps({
                'id': 1, 'method': 'Target.createTarget',
                'params': {'url': 'https://www.zhipin.com/web/geek/job'}
            }))
            ws.recv()
            ws.close()
            return JsonResponse({'code': 0, 'msg': '已在浏览器中打开 BOSS 直聘'})
    except Exception:
        pass

    # 找 Chrome 路径（注册表优先）
    chrome_exe = None
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                key = winreg.OpenKey(hive, r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe')
                path, _ = winreg.QueryValueEx(key, '')
                if path and os.path.exists(path):
                    chrome_exe = path
                    break
            except Exception:
                pass
    except Exception:
        pass

    if not chrome_exe:
        for p in [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
        ]:
            if os.path.exists(p):
                chrome_exe = p
                break

    if not chrome_exe:
        return JsonResponse({'code': 1, 'msg': '未找到 Chrome，请手动打开浏览器访问 zhipin.com'})

    # 独立 profile 目录 → 强制启动新进程，不复用已有 Chrome
    debug_profile = os.path.join(tempfile.gettempdir(), 'chrome_cdp_debug')
    os.makedirs(debug_profile, exist_ok=True)

    # 如果 9222 端口有旧进程（没有 --remote-allow-origins），先杀掉
    try:
        import subprocess as _sp
        result = _sp.run(
            ['netstat', '-ano'],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if ':9222' in line and 'LISTENING' in line:
                parts = line.split()
                pid = parts[-1]
                if pid.isdigit():
                    _sp.run(['taskkill', '/F', '/PID', pid],
                            capture_output=True, timeout=5)
                    import time as _t; _t.sleep(0.8)
                    break
    except Exception:
        pass

    cmd = [
        chrome_exe,
        '--remote-debugging-port=9222',
        '--remote-debugging-address=127.0.0.1',
        '--remote-allow-origins=*',
        f'--user-data-dir={debug_profile}',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-background-networking',
        '--disable-sync',
        '--disable-translate',
        '--disable-extensions',
        '--disable-blink-features=AutomationControlled',   # 关键：隐藏自动化特征
        '--exclude-switches=enable-automation',
        '--window-size=1280,800',
        'https://www.zhipin.com/web/geek/job',
    ]
    try:
        flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        # 等待 Chrome 启动并开放 CDP
        import time as _t
        for _ in range(15):
            _t.sleep(1)
            try:
                import requests as _req
                _req.get('http://localhost:9222/json', timeout=1)
                break
            except Exception:
                pass
        # 注入完整 stealth 脚本（在 zhipin.com 加载前）
        try:
            import requests as _req, websocket as _ws, json as _json
            tabs = _req.get('http://localhost:9222/json', timeout=3).json()
            if tabs:
                ws_url = tabs[0]['webSocketDebuggerUrl']
                ws = _ws.create_connection(ws_url, timeout=8,
                    origin='http://localhost:9222', header={'Host': 'localhost:9222'})
                stealth = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']});
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}, app: {}};
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (p) => p.name === 'notifications'
  ? Promise.resolve({state: Notification.permission})
  : origQuery(p);
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
"""
                ws.send(_json.dumps({'id':1,'method':'Page.addScriptToEvaluateOnNewDocument','params':{'source':stealth}}))
                ws.recv()
                ws.close()
        except Exception:
            pass
        return JsonResponse({'code': 0, 'msg': '浏览器已启动，正在打开 BOSS 直聘'})
    except Exception as e:
        return JsonResponse({'code': 1, 'msg': f'启动失败: {e}'})


def start_boss_spider(request):
    """启动 BOSS 直聘爬虫"""
    if request.method != 'POST':
        return JsonResponse({'code': 1, 'msg': '请求方式错误'})

    spider_info = SpiderInfo.objects.first()
    if spider_info and spider_info.status == 1:
        return JsonResponse({'code': 1, 'msg': '爬虫正在运行中'})

    from .browser_crawler import is_boss_available
    if not is_boss_available():
        return JsonResponse({
            'code': 1,
            'msg': '❌ 未检测到 BOSS 直聘页面\n\n请先在 jshook 浏览器中打开 zhipin.com，然后再启动爬虫。'
        })

    # 支持随机模式
    keyword_raw = request.POST.get('keyword', '').strip()
    use_random = request.POST.get('use_random', 'false').lower() == 'true'
    random_count = int(request.POST.get('random_count', 5))
    
    if not keyword_raw or keyword_raw.lower() == 'random' or use_random:
        keywords = _get_random_keywords(random_count)
        mode_desc = f'随机模式（{len(keywords)}个关键词）'
    else:
        keywords = [k.strip() for k in keyword_raw.split(',') if k.strip()] or ['Python']
        mode_desc = f'指定关键词（{len(keywords)}个）'
    
    pages = int(request.POST.get('pages', 5))

    thread = threading.Thread(target=_run_boss_batch, args=(keywords, pages))
    thread.daemon = True
    thread.start()

    return JsonResponse({
        'code': 0, 
        'msg': f'BOSS 直聘爬虫已启动 - {mode_desc}', 
        'mode': 'jshook 浏览器',
        'keywords': keywords
    })


def _run_boss_batch(keywords, pages):
    """BOSS 直聘批量爬取"""
    from .browser_crawler import crawl_boss_via_browser
    from django.utils import timezone

    spider_info, _ = SpiderInfo.objects.get_or_create(pk=1, defaults={
        'spider_name': '前程无忧爬虫', 'target_site': '51job.com', 'status': 0,
        'total_count': 0, 'run_count': 0,
    })
    spider_info.status = 1
    spider_info.target_site = 'BOSS直聘'
    spider_info.save()

    total = 0
    try:
        import random as _random
        boss_blocked_count = 0  # 连续风控计数
        BOSS_MAX_BLOCKED = 2    # 连续2次 code=35 就放弃本批 BOSS 爬取

        for idx, keyword in enumerate(keywords):
            # 连续风控超限，放弃剩余关键词
            if boss_blocked_count >= BOSS_MAX_BLOCKED:
                print(f'[BOSS] 连续 {BOSS_MAX_BLOCKED} 次触发风控，IP 封禁中，跳过剩余关键词')
                break

            # 关键词之间随机等待，模拟人类行为，避免连续高频触发风控
            if idx > 0:
                wait = _random.uniform(10, 20)
                print(f'[BOSS] 关键词间隔等待 {wait:.1f}s...')
                time.sleep(wait)

            jobs = crawl_boss_via_browser(keyword, pages)
            print(f'[BOSS] {keyword} 获取 {len(jobs)} 条')

            if len(jobs) == 0:
                boss_blocked_count += 1
            else:
                boss_blocked_count = 0  # 成功则重置
            for job in jobs:
                name = job.get('name', '').strip()
                company = job.get('company', '').strip()
                city = job.get('city', '')
                if not name or not company:
                    continue
                # 优先用 href 去重，无 href 时回退到 (name, company, city)
                href_val = job.get('href', '') or ''
                if href_val:
                    if JobData.objects.filter(href=href_val).exists():
                        continue
                else:
                    if JobData.objects.filter(name=name, company=company, city=city).exists():
                        continue
                salary_str = job.get('salary', '') or '面议'
                salary_min, salary_max = parse_salary(salary_str)
                JobData.objects.create(
                    name=name, salary=salary_str,
                    salary_min=salary_min, salary_max=salary_max,
                    city=city, place=city,
                    education=job.get('edu', '不限') or '不限',
                    experience=job.get('exp', '不限') or '不限',
                    company=company,
                    industry=job.get('industry', ''),
                    scale=job.get('scale', ''),
                    label=job.get('skills', ''),
                    key_word=keyword,
                    source='BOSS直聘',
                    href=href_val,
                )
                total += 1
    except Exception as e:
        print(f'[BOSS] 出错: {e}')
    finally:
        spider_info.refresh_from_db()
        spider_info.status = 0
        spider_info.total_count += total
        spider_info.last_new_count = total
        spider_info.run_count += 1
        spider_info.last_run_time = timezone.now()
        spider_info.save()
        print(f'[BOSS] 完成，共 {total} 条')
