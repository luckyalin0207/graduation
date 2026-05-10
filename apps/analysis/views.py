from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Count, Avg, Max, Min, Q
from jobs.models import JobData, SendList, FavoriteJob, UserExpect, UserExpectItem
from spider.models import SpiderInfo
from users.models import UserList


def welcome(request):
    """控制台/仪表盘 - 优化版：增加业务含义和用户价值"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    from django.utils import timezone
    from datetime import timedelta
    
    # 基础统计
    total_jobs = JobData.objects.count()
    total_users = UserList.objects.count()
    
    # 用户个人投递统计
    user_send_count = SendList.objects.filter(user_id=user_id).count()
    user_favorite_count = FavoriteJob.objects.filter(user_id=user_id).count()
    
    # 最近7天新增职位数（体现市场活跃度）
    seven_days_ago = timezone.now() - timedelta(days=7)
    new_jobs_week = JobData.objects.filter(created_at__gte=seven_days_ago).count()
    
    # 薪资统计
    jobs_with_salary = JobData.objects.exclude(salary_max__isnull=True)
    avg_salary = jobs_with_salary.aggregate(avg=Avg('salary_max'))['avg'] or 0
    median_salary = jobs_with_salary.aggregate(avg=Avg('salary_min'))['avg'] or 0
    
    # 获取用户期望职位的薪资TOP10（更有针对性）
    user_expects = UserExpectItem.objects.filter(user_id=user_id)
    if not user_expects.exists():
        # 兼容旧数据
        legacy = UserExpect.objects.filter(user_id=user_id).first()
        if legacy and legacy.key_word:
            user_expects = [legacy]
    
    top_jobs = []
    if user_expects:
        # 根据用户期望职位筛选TOP10
        q = Q()
        for expect in user_expects:
            if hasattr(expect, 'key_word') and expect.key_word:
                q |= Q(key_word__icontains=expect.key_word) | Q(name__icontains=expect.key_word)
        
        if q:
            top_jobs = list(jobs_with_salary.filter(q).order_by('-salary_max')[:10].values(
                'job_id', 'name', 'salary', 'salary_min', 'salary_max', 'company', 'place', 'key_word'
            ))
    
    # 如果没有用户期望或匹配结果少于5个，补充全局高薪职位
    if len(top_jobs) < 5:
        global_top = list(jobs_with_salary.exclude(
            job_id__in=[j['job_id'] for j in top_jobs]
        ).order_by('-salary_max')[:10 - len(top_jobs)].values(
            'job_id', 'name', 'salary', 'salary_min', 'salary_max', 'company', 'place', 'key_word'
        ))
        top_jobs.extend(global_top)
    
    # 热门职位类型（最近7天）
    hot_keywords = (JobData.objects
                    .filter(created_at__gte=seven_days_ago)
                    .exclude(key_word__isnull=True)
                    .values('key_word')
                    .annotate(count=Count('job_id'))
                    .order_by('-count')[:5])
    
    spider_info = SpiderInfo.objects.first()
    
    # 用户投递转化率
    conversion_rate = 0
    if user_send_count > 0:
        interview_count = SendList.objects.filter(user_id=user_id, status__in=[2, 4]).count()
        conversion_rate = round((interview_count / user_send_count) * 100, 1)
    
    context = {
        # 市场概况
        'total_jobs': total_jobs,
        'new_jobs_week': new_jobs_week,
        'total_users': total_users,
        
        # 用户个人数据
        'user_send_count': user_send_count,
        'user_favorite_count': user_favorite_count,
        'conversion_rate': conversion_rate,
        
        # 薪资洞察
        'avg_salary': round(avg_salary, 2),
        'median_salary': round(median_salary, 2),
        'top_jobs': top_jobs,
        'top_jobs_title': '您关注的高薪职位' if user_expects else '市场高薪职位TOP10',
        
        # 市场趋势
        'hot_keywords': list(hot_keywords),
        
        # 爬虫状态
        'spider_info': spider_info,
    }
    return render(request, "analysis/welcome.html", context)


def dashboard(request):
    """可视化大屏"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    return render(request, "analysis/dashboard.html")


def get_edu_data(request):
    """获取学历分布数据"""
    edu_list = ['博士', '硕士', '本科', '大专', '中专', '高中', '不限']
    edu_data = []
    for edu in edu_list:
        count = JobData.objects.filter(education__icontains=edu).count()
        if count > 0:
            edu_data.append({'name': edu, 'value': count})
    
    other_count = JobData.objects.exclude(
        education__icontains='博士'
    ).exclude(
        education__icontains='硕士'
    ).exclude(
        education__icontains='本科'
    ).exclude(
        education__icontains='大专'
    ).exclude(
        education__icontains='中专'
    ).exclude(
        education__icontains='高中'
    ).exclude(
        education__icontains='不限'
    ).count()
    if other_count > 0:
        edu_data.append({'name': '其他', 'value': other_count})
    
    return JsonResponse({'code': 0, 'data': edu_data})


def get_salary_data(request):
    """获取薪资分布数据"""
    salary_ranges = [
        ('5K及以下', 0, 5),
        ('5-10K', 5, 10),
        ('10-15K', 10, 15),
        ('15-20K', 15, 20),
        ('20-30K', 20, 30),
        ('30-50K', 30, 50),
        ('50K以上', 50, 9999),
    ]
    salary_data = []
    for name, min_v, max_v in salary_ranges:
        count = JobData.objects.filter(salary_max__gte=min_v, salary_max__lt=max_v).count()
        if count > 0:
            salary_data.append({'name': name, 'value': count})
    
    return JsonResponse({'code': 0, 'data': salary_data})


def get_city_data(request):
    """获取城市分布数据"""
    city_counts = JobData.objects.values('city').annotate(
        count=Count('job_id')
    ).order_by('-count')[:15]
    
    city_data = [{'name': item['city'] or '未知', 'value': item['count']} 
                 for item in city_counts if item['city']]
    
    return JsonResponse({'code': 0, 'data': city_data})


def get_keyword_data(request):
    """获取关键词/岗位分布数据"""
    keyword_counts = JobData.objects.values('key_word').annotate(
        count=Count('job_id')
    ).order_by('-count')[:10]
    
    bar_x = [item['key_word'] for item in keyword_counts if item['key_word']]
    bar_y = [item['count'] for item in keyword_counts if item['key_word']]
    
    return JsonResponse({'code': 0, 'bar_x': bar_x, 'bar_y': bar_y})


def get_exp_salary_data(request):
    """获取经验-薪资关系数据"""
    exp_list = ['应届', '1年', '1-3年', '3-5年', '5-10年', '10年以上', '经验不限', '在校']
    exp_data = []
    for exp in exp_list:
        avg = JobData.objects.filter(experience__icontains=exp).exclude(
            salary_max__isnull=True
        ).aggregate(avg=Avg('salary_max'))['avg']
        if avg:
            exp_data.append({'exp': exp, 'salary': round(avg, 2)})
    
    # 计算总体平均薪资
    total_avg = JobData.objects.exclude(salary_max__isnull=True).aggregate(
        avg=Avg('salary_max')
    )['avg'] or 0
    
    return JsonResponse({'code': 0, 'data': exp_data, 'avg_salary': round(total_avg, 2)})


def get_company_type_data(request):
    """获取公司类型分布数据"""
    import ast
    
    type_counts = JobData.objects.values('company_type').annotate(
        count=Count('job_id')
    ).order_by('-count')[:10]
    
    data = []
    for item in type_counts:
        ct = item['company_type']
        if not ct:
            continue
        # 处理字典字符串格式 "{'name': '民营'}"
        if ct.startswith('{') and 'name' in ct:
            try:
                parsed = ast.literal_eval(ct)
                ct = parsed.get('name', ct)
            except:
                pass
        data.append({'name': ct, 'value': item['count']})
    
    return JsonResponse({'code': 0, 'data': data})


def job_analysis(request):
    """岗位分类分析页面 - 支持多技能栈筛选"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    job_type = request.GET.get('type', 'python')
    
    # 支持多个关键词（逗号分隔）
    keywords = [k.strip() for k in job_type.split(',') if k.strip()]
    
    # 构建查询
    from django.db.models import Q
    q = Q()
    for keyword in keywords:
        q |= Q(key_word__icontains=keyword) | Q(name__icontains=keyword)
    
    jobs = JobData.objects.filter(q) if keywords else JobData.objects.all()
    total = jobs.count()
    
    # 完整薪资统计（包含最低、最高、平均）
    jobs_with_salary = jobs.exclude(salary_max__isnull=True, salary_min__isnull=True)
    avg_salary_max = jobs_with_salary.aggregate(avg=Avg('salary_max'))['avg'] or 0
    avg_salary_min = jobs_with_salary.aggregate(avg=Avg('salary_min'))['avg'] or 0
    avg_salary = (avg_salary_max + avg_salary_min) / 2 if avg_salary_max and avg_salary_min else avg_salary_max
    
    max_salary = jobs_with_salary.aggregate(max=Max('salary_max'))['max'] or 0
    # 过滤掉异常小值（小于1K视为脏数据）
    min_salary = jobs_with_salary.filter(salary_min__gte=1).aggregate(min=Min('salary_min'))['min'] or 0
    
    # 薪资中位数
    salary_values = list(jobs_with_salary.values_list('salary_max', flat=True))
    median_salary = 0
    if salary_values:
        salary_values.sort()
        mid = len(salary_values) // 2
        median_salary = salary_values[mid] if len(salary_values) % 2 == 1 else (salary_values[mid-1] + salary_values[mid]) / 2
    
    # 获取所有可用的职位类型（用于筛选器）
    all_keywords = (JobData.objects
                    .exclude(key_word__isnull=True)
                    .values('key_word')
                    .annotate(count=Count('job_id'))
                    .order_by('-count')[:20])
    
    context = {
        'job_type': job_type,
        'keywords': keywords,
        'total': total,
        'avg_salary': round(avg_salary, 2),
        'avg_salary_min': round(avg_salary_min, 2),
        'avg_salary_max': round(avg_salary_max, 2),
        'median_salary': round(median_salary, 2),
        'max_salary': max_salary,
        'min_salary': min_salary,
        'all_keywords': list(all_keywords),
    }
    return render(request, "analysis/job_analysis.html", context)


def get_job_type_edu(request):
    """获取指定岗位类型的学历分布"""
    job_type = request.GET.get('type', 'python')
    
    # 支持多个关键词（逗号分隔）
    keywords = [k.strip() for k in job_type.split(',') if k.strip()]
    
    # 构建查询
    from django.db.models import Q
    q = Q()
    for keyword in keywords:
        q |= Q(key_word__icontains=keyword) | Q(name__icontains=keyword)
    
    jobs = JobData.objects.filter(q) if keywords else JobData.objects.all()
    
    edu_list = ['博士', '硕士', '本科', '大专', '不限']
    edu_data = []
    for edu in edu_list:
        count = jobs.filter(education__icontains=edu).count()
        if count > 0:
            edu_data.append({'name': edu, 'value': count})
    
    return JsonResponse({'code': 0, 'data': edu_data})


def get_job_type_exp(request):
    """获取指定岗位类型的经验分布"""
    job_type = request.GET.get('type', 'python')
    
    # 支持多个关键词（逗号分隔）
    keywords = [k.strip() for k in job_type.split(',') if k.strip()]
    
    # 构建查询
    from django.db.models import Q
    q = Q()
    for keyword in keywords:
        q |= Q(key_word__icontains=keyword) | Q(name__icontains=keyword)
    
    jobs = JobData.objects.filter(q) if keywords else JobData.objects.all()
    
    exp_list = ['应届生', '1年以下', '1-3年', '3-5年', '5-10年', '10年以上', '不限']
    exp_data = []
    for exp in exp_list:
        count = jobs.filter(experience__icontains=exp).count()
        if count > 0:
            exp_data.append({'name': exp, 'value': count})
    
    return JsonResponse({'code': 0, 'data': exp_data})


def get_job_type_salary(request):
    """获取指定岗位类型的薪资分布"""
    job_type = request.GET.get('type', 'python')
    
    # 支持多个关键词（逗号分隔）
    keywords = [k.strip() for k in job_type.split(',') if k.strip()]
    
    # 构建查询
    from django.db.models import Q
    q = Q()
    for keyword in keywords:
        q |= Q(key_word__icontains=keyword) | Q(name__icontains=keyword)
    
    jobs = JobData.objects.filter(q) if keywords else JobData.objects.all()
    
    salary_ranges = [
        ('5K以下', 0, 5), ('5-10K', 5, 10), ('10-15K', 10, 15),
        ('15-20K', 15, 20), ('20-30K', 20, 30), ('30-50K', 30, 50), ('50K以上', 50, 9999),
    ]
    salary_data = []
    for name, min_v, max_v in salary_ranges:
        count = jobs.filter(salary_max__gte=min_v, salary_max__lt=max_v).count()
        if count > 0:
            salary_data.append({'name': name, 'value': count})
    
    return JsonResponse({'code': 0, 'data': salary_data})


def get_job_type_city(request):
    """获取指定岗位类型的城市分布"""
    job_type = request.GET.get('type', 'python')
    
    # 支持多个关键词（逗号分隔）
    keywords = [k.strip() for k in job_type.split(',') if k.strip()]
    
    # 构建查询
    from django.db.models import Q
    q = Q()
    for keyword in keywords:
        q |= Q(key_word__icontains=keyword) | Q(name__icontains=keyword)
    
    jobs = JobData.objects.filter(q) if keywords else JobData.objects.all()
    
    city_counts = jobs.values('city').annotate(count=Count('job_id')).order_by('-count')[:10]
    data = [{'name': item['city'] or '未知', 'value': item['count']} for item in city_counts if item['city']]
    
    return JsonResponse({'code': 0, 'data': data})


def salary_map(request):
    """薪资热力图页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    return render(request, "analysis/salary_map.html")


def get_salary_map_data(request):
    """
    获取薪资热力图数据 - 优化版
    使用加权算法：样本数量少的城市降低权重，避免单个高薪职位导致的数据失真
    """
    job_type = request.GET.get('type', '')
    min_sample_size = int(request.GET.get('min_samples', 5))  # 最小样本数阈值
    
    jobs = JobData.objects.all()
    if job_type:
        jobs = jobs.filter(key_word__icontains=job_type)
    
    # 按城市统计平均薪资和样本数
    city_salary = jobs.exclude(salary_max__isnull=True).values('city').annotate(
        avg_salary=Avg('salary_max'),
        count=Count('job_id')
    ).order_by('-avg_salary')
    
    # 计算全局平均薪资（用于加权）
    global_avg = jobs.exclude(salary_max__isnull=True).aggregate(avg=Avg('salary_max'))['avg'] or 0
    
    # 加权算法：样本数少的城市向全局平均回归
    data = []
    for item in city_salary:
        if not item['city']:
            continue
        
        count = item['count']
        raw_avg = item['avg_salary']
        
        # 过滤样本数过少的城市
        if count < min_sample_size:
            continue
        
        # 加权公式：weighted_salary = (count * raw_avg + k * global_avg) / (count + k)
        # k 是平滑参数，样本越少，越接近全局平均
        k = 10  # 平滑参数，可调整
        weighted_salary = (count * raw_avg + k * global_avg) / (count + k)
        
        # 置信度：样本数越多，置信度越高
        confidence = min(100, int((count / 50) * 100))  # 50个样本为100%置信度
        
        data.append({
            'name': item['city'],
            'value': round(weighted_salary, 2),
            'raw_value': round(raw_avg, 2),
            'count': count,
            'confidence': confidence
        })
    
    # 按加权后的薪资重新排序
    data.sort(key=lambda x: x['value'], reverse=True)
    
    return JsonResponse({
        'code': 0,
        'data': data,
        'global_avg': round(global_avg, 2),
        'min_sample_size': min_sample_size,
        'note': f'已过滤样本数少于{min_sample_size}的城市，并对小样本城市进行加权平滑'
    })


def salary_predict(request):
    """薪资推测页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    # 获取所有可用的城市、学历、经验、岗位类型
    cities = (JobData.objects
              .exclude(city__isnull=True)
              .exclude(city='')
              .values('city')
              .annotate(count=Count('job_id'))
              .order_by('-count')[:20])
    
    educations = ['博士', '硕士', '本科', '大专', '高中', '初中', '不限']
    
    experiences = ['应届生', '1年以下', '1-3年', '3-5年', '5-10年', '10年以上', '不限']
    
    job_types = (JobData.objects
                 .exclude(key_word__isnull=True)
                 .exclude(key_word='')
                 .values('key_word')
                 .annotate(count=Count('job_id'))
                 .order_by('-count')[:30])
    
    context = {
        'cities': [c['city'] for c in cities if c['city']],
        'educations': educations,
        'experiences': experiences,
        'job_types': [jt['key_word'] for jt in job_types if jt['key_word']],
    }
    
    return render(request, "analysis/salary_predict.html", context)


def do_salary_predict(request):
    """执行薪资推测（使用机器学习模型）"""
    from .ml_predictor import get_predictor
    
    city = request.GET.get('city', '')
    education = request.GET.get('education', '')
    experience = request.GET.get('experience', '')
    job_type = request.GET.get('job_type', '')
    
    # 使用机器学习模型预测
    predictor = get_predictor()
    predicted_salary, msg = predictor.predict(city, education, experience, job_type)
    
    if predicted_salary is None:
        # 如果ML预测失败，回退到统计方法
        jobs = JobData.objects.exclude(salary_max__isnull=True)
        
        if city:
            jobs = jobs.filter(city__icontains=city)
        if education:
            jobs = jobs.filter(education__icontains=education)
        if experience:
            jobs = jobs.filter(experience__icontains=experience)
        if job_type:
            jobs = jobs.filter(key_word__icontains=job_type)
        
        if jobs.count() == 0:
            return JsonResponse({'code': 1, 'msg': '没有找到匹配的数据，且模型预测失败'})
        
        predicted_salary = jobs.aggregate(avg=Avg('salary_max'))['avg'] or 0
        max_salary = jobs.aggregate(max=Max('salary_max'))['max'] or 0
        min_salary = jobs.aggregate(min=Min('salary_min'))['min'] or 0
        method = 'statistical'
    else:
        # ML预测成功，获取置信区间
        lower, upper = predictor.get_confidence_interval(city, education, experience, job_type)
        if lower and upper:
            min_salary = lower
            max_salary = upper
        else:
            min_salary = predicted_salary * 0.7
            max_salary = predicted_salary * 1.3
        method = 'ml'
    
    # 获取匹配的职位数量和薪资分布（用于参考）
    jobs = JobData.objects.exclude(salary_max__isnull=True)
    if city:
        jobs = jobs.filter(city__icontains=city)
    if education:
        jobs = jobs.filter(education__icontains=education)
    if experience:
        jobs = jobs.filter(experience__icontains=experience)
    if job_type:
        jobs = jobs.filter(key_word__icontains=job_type)
    
    count = jobs.count()
    
    # 薪资分布
    salary_dist = []
    for name, min_v, max_v in [('5K以下', 0, 5), ('5-10K', 5, 10), ('10-15K', 10, 15), ('15-20K', 15, 20), ('20-30K', 20, 30), ('30K以上', 30, 9999)]:
        c = jobs.filter(salary_max__gte=min_v, salary_max__lt=max_v).count()
        if c > 0:
            salary_dist.append({'name': name, 'value': c})
    
    return JsonResponse({
        'code': 0,
        'data': {
            'avg_salary': round(predicted_salary, 2),
            'max_salary': round(max_salary, 2),
            'min_salary': round(min_salary, 2),
            'count': count,
            'salary_dist': salary_dist,
            'method': method,  # 'ml' 或 'statistical'
            'note': '预测薪资由AI模型生成' if method == 'ml' else '基于历史数据统计'
        }
    })


def job_match(request):
    """岗位匹配页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    return render(request, "analysis/job_match.html")


def do_job_match(request):
    """执行岗位匹配（使用TF-IDF文本相似度）"""
    from .job_matcher import get_matcher
    
    skills = request.GET.get('skills', '')
    city = request.GET.get('city', '')
    salary_min = request.GET.get('salary_min', 0)
    education = request.GET.get('education', '')
    experience = request.GET.get('experience', '')
    
    # 使用智能匹配器
    matcher = get_matcher()
    try:
        results = matcher.match_jobs(
            skills=skills,
            city=city,
            salary_min=int(salary_min) if salary_min else 0,
            education=education,
            experience=experience,
            top_k=20
        )
        
        if not results:
            # 如果智能匹配失败，回退到传统方法
            jobs = JobData.objects.exclude(salary_max__isnull=True)
            
            if city:
                jobs = jobs.filter(city__icontains=city)
            if salary_min:
                jobs = jobs.filter(salary_max__gte=int(salary_min))
            
            if skills:
                skill_list = [s.strip() for s in skills.split(',') if s.strip()]
                from django.db.models import Q
                q = Q()
                for skill in skill_list:
                    q |= Q(name__icontains=skill) | Q(key_word__icontains=skill)
                jobs = jobs.filter(q)
            
            results = []
            for job in jobs.order_by('-salary_max')[:20]:
                results.append({
                    'job_id': job.job_id,
                    'name': job.name,
                    'company': job.company,
                    'salary': job.salary,
                    'city': job.city,
                    'education': job.education,
                    'experience': job.experience,
                    'match_score': 75
                })
        
        return JsonResponse({'code': 0, 'data': results, 'method': 'tfidf'})
    
    except Exception as e:
        return JsonResponse({'code': 1, 'msg': f'匹配失败: {str(e)}'})


def get_map_data(request):
    """获取中国地图各省份数据"""
    from django.db.models import Q
    
    # 省份城市映射（使用 GeoJSON 中的全称作为 key）
    province_cities = {
        '北京市': ['北京'],
        '上海市': ['上海'],
        '天津市': ['天津'],
        '重庆市': ['重庆'],
        '广东省': ['广州', '深圳', '东莞', '佛山', '珠海', '惠州', '中山'],
        '江苏省': ['南京', '苏州', '无锡', '常州', '南通'],
        '浙江省': ['杭州', '宁波', '温州', '嘉兴', '绍兴'],
        '四川省': ['成都', '绵阳', '德阳'],
        '湖北省': ['武汉', '宜昌', '襄阳'],
        '湖南省': ['长沙', '株洲', '湘潭'],
        '河南省': ['郑州', '洛阳', '开封'],
        '河北省': ['石家庄', '唐山', '保定'],
        '山东省': ['济南', '青岛', '烟台', '威海'],
        '陕西省': ['西安', '咸阳', '宝鸡'],
        '福建省': ['福州', '厦门', '泉州'],
        '辽宁省': ['沈阳', '大连', '鞍山'],
        '安徽省': ['合肥', '芜湖', '蚌埠'],
        '江西省': ['南昌', '九江', '赣州'],
        '山西省': ['太原', '大同', '阳泉'],
        '吉林省': ['长春', '吉林市'],
        '黑龙江省': ['哈尔滨', '齐齐哈尔', '大庆'],
        '云南省': ['昆明', '大理', '丽江'],
        '贵州省': ['贵阳', '遵义', '六盘水'],
        '广西壮族自治区': ['南宁', '柳州', '桂林'],
        '海南省': ['海口', '三亚'],
        '甘肃省': ['兰州', '天水'],
        '青海省': ['西宁'],
        '内蒙古自治区': ['呼和浩特', '包头', '鄂尔多斯'],
        '宁夏回族自治区': ['银川'],
        '新疆维吾尔自治区': ['乌鲁木齐', '克拉玛依'],
        '西藏自治区': ['拉萨'],
        '香港特别行政区': ['香港'],
        '澳门特别行政区': ['澳门'],
        '台湾省': ['台北', '高雄'],
    }
    
    result = []
    for province, cities in province_cities.items():
        q = Q()
        for city in cities:
            q |= Q(city__icontains=city) | Q(place__icontains=city)
        
        jobs = JobData.objects.filter(q)
        count = jobs.count()
        avg_salary = jobs.exclude(salary_max__isnull=True).aggregate(avg=Avg('salary_max'))['avg'] or 0
        
        if count > 0:
            result.append({
                'name': province,
                'value': round(avg_salary, 2),
                'count': count
            })
    
    # 按薪资排序
    result.sort(key=lambda x: x['value'], reverse=True)
    
    return JsonResponse({'code': 0, 'data': result})


def get_experience_data(request):
    """获取经验分布数据"""
    exp_list = ['应届', '1年', '1-3年', '3-5年', '5-10年', '10年以上', '经验不限']
    exp_data = []
    for exp in exp_list:
        count = JobData.objects.filter(experience__icontains=exp).count()
        if count > 0:
            exp_data.append({'name': exp, 'value': count})
    
    return JsonResponse({'code': 0, 'data': exp_data})


def get_scale_data(request):
    """获取公司规模数据"""
    scale_list = ['少于50人', '50-150人', '150-500人', '500-1000人', '1000-5000人', '5000-10000人', '10000人以上']
    scale_data = []
    for scale in scale_list:
        count = JobData.objects.filter(scale__icontains=scale).count()
        if count > 0:
            scale_data.append({'name': scale, 'value': count})
    
    return JsonResponse({'code': 0, 'data': scale_data})


def train_salary_model(request):
    """训练薪资预测模型（管理员功能）"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    from .ml_predictor import get_predictor
    
    predictor = get_predictor()
    success, msg = predictor.train()
    
    if success:
        return JsonResponse({'code': 0, 'msg': msg})
    else:
        return JsonResponse({'code': 1, 'msg': msg})


def build_job_index(request):
    """构建职位匹配索引（管理员功能）"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    from .job_matcher import get_matcher
    
    matcher = get_matcher()
    success, msg = matcher.build_index()
    
    if success:
        return JsonResponse({'code': 0, 'msg': msg})
    else:
        return JsonResponse({'code': 1, 'msg': msg})


def export_analysis_data(request):
    """导出分析数据为Excel"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    from .exporter import DataExporter
    
    job_type = request.GET.get('type', '')
    
    try:
        return DataExporter.export_to_response(job_type)
    except Exception as e:
        return JsonResponse({'code': 1, 'msg': f'导出失败: {str(e)}'})


def get_trend_data(request):
    """职位数量趋势 — 按天统计最近30天爬取量"""
    from django.utils import timezone
    from datetime import timedelta
    days = int(request.GET.get('days', 30))
    keyword = request.GET.get('keyword', '')
    end = timezone.now().date()
    start = end - timedelta(days=days - 1)

    qs = JobData.objects.filter(created_at__date__gte=start)
    if keyword:
        qs = qs.filter(key_word__icontains=keyword)

    counts = (qs.extra(select={'day': "date(created_at)"})
               .values('day')
               .annotate(n=Count('job_id'))
               .order_by('day'))

    # 补全每天（没数据的天填0）
    day_map = {str(row['day']): row['n'] for row in counts}
    labels, values = [], []
    for i in range(days):
        d = str(start + timedelta(days=i))
        labels.append(d[5:])   # 只显示 MM-DD
        values.append(day_map.get(d, 0))

    return JsonResponse({'code': 0, 'labels': labels, 'values': values})


def job_trend_predict(request):
    """岗位需求趋势预测页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    return render(request, "analysis/job_trend_predict.html")


def get_sdf_skill_trend(request):
    """
    历史技能需求趋势 API (路径沿用旧命名 /api/sdf/skill-trend/)
    数据源: 拉勾网数据集 (HistoricalJobData.data_source='Lagou') + 实时爬取的 JobData
    返回指定关键词的按日需求相对指数 (首日=100)
    """
    from collections import defaultdict
    from .job_trend_analyzer import DATA_SOURCE_LABEL
    from analysis.models import HistoricalJobData

    keywords_str = request.GET.get('keywords', 'Python,Java,前端')
    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()][:6]

    series_list = []
    all_date_set: set = set()
    for kw in keywords:
        qs = HistoricalJobData.objects.filter(
            Q(skill_name__icontains=kw) | Q(occupation_l2__icontains=kw)
        ).order_by('date').values('date', 'demand_count')

        by_date = defaultdict(int)
        for row in qs:
            by_date[row['date']] += row['demand_count']

        # HistoricalJobData 没命中 -> 用 JobData.created_at 兜底
        if not by_date:
            jobs_qs = (JobData.objects
                       .filter(Q(key_word__icontains=kw) | Q(name__icontains=kw))
                       .exclude(created_at__isnull=True)
                       .values_list('created_at', flat=True))
            for ts in jobs_qs:
                by_date[ts.date()] += 1

        if len(by_date) < 3:
            continue

        sorted_dates = sorted(by_date.keys())
        values = [by_date[d] for d in sorted_dates]
        base = values[0] if values[0] > 0 else 1
        index_series = [round(v / base * 100, 1) for v in values]
        date_labels = [d.strftime('%Y-%m-%d') for d in sorted_dates]
        all_date_set.update(date_labels)
        series_list.append({'name': kw, 'data': index_series, 'dates': date_labels, 'raw': values})

    if not series_list:
        return JsonResponse({'code': 1, 'msg': '所选关键词暂无历史数据,请先运行 `python manage.py import_lagou --with-trend`'})

    all_dates = sorted(all_date_set)
    return JsonResponse({
        'code': 0,
        'dates': all_dates,
        'series': series_list,
        'note': '纵轴为需求相对指数(以各自首日=100),原始岗位数见 series[].raw',
        'source': DATA_SOURCE_LABEL,
    })


def get_sdf_hot_skills(request):
    """
    热门关键词排行 API (路径沿用旧命名 /api/sdf/hot-skills/)
    返回当前 JobData 各关键词的总岗位数 + 增长率(首尾 3 日平均对比)
    数据源: 拉勾网数据集 + 实时爬取
    """
    from collections import defaultdict
    from analysis.models import HistoricalJobData
    from .job_trend_analyzer import DATA_SOURCE_LABEL

    # 总量排行
    totals = list(
        JobData.objects.exclude(key_word__isnull=True).exclude(key_word='')
        .values('key_word').annotate(total=Count('job_id')).order_by('-total')[:30]
    )

    # 每个关键词拉一下日度序列,算增长率
    result = []
    for row in totals:
        kw = row['key_word']
        daily = (
            HistoricalJobData.objects
            .filter(Q(skill_name__icontains=kw) | Q(occupation_l2__icontains=kw))
            .values('date').order_by('date')
            .annotate(n=Count('hist_id'))
        )
        series = [(r['date'], r['n']) for r in daily]

        growth = 0.0
        if len(series) >= 6:
            early_avg = sum(v for _, v in series[:3]) / 3.0
            late_avg = sum(v for _, v in series[-3:]) / 3.0
            growth = round((late_avg - early_avg) / (early_avg + 1) * 100, 1)

        result.append({'name': kw, 'total': row['total'], 'growth': growth})

    result.sort(key=lambda x: x['total'], reverse=True)
    return JsonResponse({'code': 0, 'data': result[:15], 'source': DATA_SOURCE_LABEL})


def get_sdf_cooccurrence(request):
    """
    技能共现推荐 API (路径沿用旧命名 /api/sdf/cooccurrence/)
    数据源: 由 `python manage.py import_lagou --with-cooc` 写入的 SkillCooccurrence
    """
    from analysis.models import SkillCooccurrence
    from .job_trend_analyzer import DATA_SOURCE_LABEL

    keyword = request.GET.get('keyword', 'Python').strip()
    if not keyword:
        return JsonResponse({'code': 1, 'msg': '请提供关键词'})

    hits = SkillCooccurrence.objects.filter(
        Q(skill_1_name__icontains=keyword) | Q(skill_2_name__icontains=keyword)
    ).order_by('-frequency')[:50]

    if not hits.exists():
        return JsonResponse({'code': 1, 'msg': f'未找到关键词 "{keyword}" 的共现技能,请确认已运行 import_lagou --with-cooc'})

    seen = {keyword.lower()}
    recs = []
    for row in hits:
        other = row.skill_2_name if keyword.lower() in row.skill_1_name.lower() else row.skill_1_name
        if other.lower() in seen:
            continue
        seen.add(other.lower())
        recs.append({'skill': other, 'frequency': row.frequency})
        if len(recs) >= 8:
            break

    return JsonResponse({'code': 0, 'keyword': keyword, 'data': recs, 'source': DATA_SOURCE_LABEL})


def get_sdf_salary_reference(request):
    """
    历史薪资参考 API (路径沿用旧命名 /api/sdf/salary-reference/)
    返回关键词的历史需求趋势(按日聚合)+ 当前爬取薪资统计
    """
    from collections import defaultdict
    from analysis.models import HistoricalJobData
    from .job_trend_analyzer import DATA_SOURCE_LABEL

    keyword = request.GET.get('keyword', '').strip()
    if not keyword:
        return JsonResponse({'code': 1, 'msg': '请提供关键词'})

    # 当前岗位薪资统计
    jobs = JobData.objects.filter(
        Q(key_word__icontains=keyword) | Q(name__icontains=keyword)
    ).exclude(salary_max__isnull=True)

    salary_stats = {
        'avg': round(float(jobs.aggregate(avg=Avg('salary_max'))['avg'] or 0), 2),
        'max': float(jobs.aggregate(max=Max('salary_max'))['max'] or 0),
        'min': float(jobs.filter(salary_min__gte=1).aggregate(min=Min('salary_min'))['min'] or 0),
        'count': jobs.count(),
    }

    # 历史需求趋势
    by_date = defaultdict(int)
    hist_qs = (
        HistoricalJobData.objects
        .filter(Q(skill_name__icontains=keyword) | Q(occupation_l2__icontains=keyword))
        .values('date', 'demand_count').order_by('date')
    )
    for row in hist_qs:
        by_date[row['date']] += row['demand_count']

    historical = {'has_data': False}
    if len(by_date) >= 3:
        sorted_dates = sorted(by_date.keys())
        values = [by_date[d] for d in sorted_dates]
        base = values[0] or 1
        index_series = [round(v / base * 100, 1) for v in values]
        historical = {
            'has_data': True,
            'dates': [d.strftime('%Y-%m-%d') for d in sorted_dates],
            'values': index_series,
            'raw': values,
            'growth_rate': round((index_series[-1] - index_series[0]) / index_series[0] * 100, 1)
                if index_series[0] else 0,
        }

    return JsonResponse({
        'code': 0,
        'keyword': keyword,
        'salary_stats': salary_stats,
        'historical_demand': historical,
        'source': DATA_SOURCE_LABEL,
    })


def get_trend_predict_data(request):
    """
    岗位需求趋势预测 API - 重新设计
    提供长期职业发展趋势分析，而不是简单的短期数量预测
    """
    try:
        from .job_trend_analyzer import get_analyzer
        
        keyword = request.GET.get('keyword', 'Python')
        action = request.GET.get('action', 'analyze')  # analyze 或 compare
        
        analyzer = get_analyzer()
        
        if action == 'compare':
            # 对比多个岗位
            keywords_str = request.GET.get('keywords', 'Python,Java,前端')
            keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
            result = analyzer.compare_jobs(keywords[:5])  # 最多对比5个
        else:
            # 分析单个岗位
            result = analyzer.analyze_job_trend(keyword)
        
        return JsonResponse(result)
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"趋势分析错误: {error_msg}")
        print(error_trace)
        
        return JsonResponse({
            'success': False,
            'message': f'分析失败: {error_msg}',
            'error': error_trace
        })
