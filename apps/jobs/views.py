from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Q
from django.core.cache import cache
from .models import JobData, SendList, UserExpect, FavoriteJob, UserExpectItem


def index(request):
    """首页 - 重定向到职位列表"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    return redirect('job_list')


def job_list(request):
    """职位列表页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    return render(request, "jobs/job_list.html")


def get_job_list(request):
    """获取职位列表API"""
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 10))
    keyword = request.GET.get("keyword", "")
    edu = request.GET.get("edu", "")
    city = request.GET.get("city", "")
    price_min = request.GET.get("price_min", "")
    price_max = request.GET.get("price_max", "")
    industry = request.GET.get("industry", "")
    company_type = request.GET.get("company_type", "")
    scale = request.GET.get("scale", "")
    experience = request.GET.get("experience", "")
    only_favorite = request.GET.get("only_favorite", "")
    source = request.GET.get("source", "")
    
    cache_key = f"job_list:{request.session.get('user_id')}:{page}:{limit}:{keyword}:{edu}:{city}:{price_min}:{price_max}:{industry}:{company_type}:{scale}:{experience}:{only_favorite}:{source}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    queryset = JobData.objects.all()
    
    def parse_list(value):
        if not value:
            return []
        raw = value.replace('，', ',').replace('|', ',')
        parts = []
        for item in raw.split(','):
            item = item.strip()
            if item:
                parts.append(item)
        return parts

    if keyword:
        queryset = queryset.filter(Q(name__icontains=keyword) | Q(company__icontains=keyword))
    if edu:
        edu_list = parse_list(edu)
        if edu_list:
            edu_q = Q()
            for item in edu_list:
                edu_q |= Q(education__icontains=item)
            queryset = queryset.filter(edu_q)
    if city:
        city_list = parse_list(city)
        if city_list:
            city_q = Q()
            for item in city_list:
                city_q |= Q(place__icontains=item) | Q(city__icontains=item)
            queryset = queryset.filter(city_q)
    if price_min:
        try:
            queryset = queryset.filter(salary_min__gte=float(price_min))
        except:
            pass
    if price_max:
        try:
            queryset = queryset.filter(salary_max__lte=float(price_max))
        except:
            pass
    if industry:
        industry_list = parse_list(industry)
        if industry_list:
            industry_q = Q()
            for item in industry_list:
                industry_q |= Q(industry__icontains=item)
            queryset = queryset.filter(industry_q)
    if company_type:
        company_list = parse_list(company_type)
        if company_list:
            company_q = Q()
            for item in company_list:
                company_q |= Q(company_type__icontains=item)
            queryset = queryset.filter(company_q)
    if scale:
        scale_list = parse_list(scale)
        if scale_list:
            scale_q = Q()
            for item in scale_list:
                scale_q |= Q(scale__icontains=item)
            queryset = queryset.filter(scale_q)
    if experience:
        exp_list = parse_list(experience)
        if exp_list:
            exp_q = Q()
            for item in exp_list:
                exp_q |= Q(experience__icontains=item)
            queryset = queryset.filter(exp_q)
    if source:
        queryset = queryset.filter(source__icontains=source)
    
    job_data = []
    user_id = request.session.get('user_id')
    sent_jobs = set()
    favorite_jobs = set()
    if user_id:
        sent_jobs = set(SendList.objects.filter(user_id=user_id).values_list('job_id', flat=True))
        favorite_jobs = set(FavoriteJob.objects.filter(user_id=user_id).values_list('job_id', flat=True))
        if only_favorite in ['1', 'true', 'True']:
            queryset = queryset.filter(job_id__in=favorite_jobs)
    
    total = queryset.count()
    start = (page - 1) * limit
    end = page * limit
    jobs = queryset[start:end]
    
    for job in jobs:
        job_data.append({
            'job_id': job.job_id,
            'name': job.name,
            'salary': job.salary,
            'salary_min': float(job.salary_min) if job.salary_min else None,
            'salary_max': float(job.salary_max) if job.salary_max else None,
            'place': job.place,
            'city': job.city,
            'education': job.education,
            'experience': job.experience,
            'company': job.company,
            'company_type': job.company_type,
            'scale': job.scale,
            'industry': job.industry,
            'label': job.label,
            'description': (job.description or '')[:300],
            'href': job.href or '',
            'key_word': job.key_word,
            'source': job.source,
            'is_sent': job.job_id in sent_jobs,
            'is_favorited': job.job_id in favorite_jobs,
        })
    
    response = {"code": 0, "msg": "success", "count": total, "data": job_data}
    cache.set(cache_key, response, 60)
    return JsonResponse(response)


def get_job_detail(request, job_id):
    """获取单个职位完整详情（用于投递弹窗）"""
    try:
        job = JobData.objects.get(job_id=job_id)
    except JobData.DoesNotExist:
        return JsonResponse({'code': 1, 'msg': '职位不存在'})

    return JsonResponse({'code': 0, 'data': {
        'job_id': job.job_id,
        'name': job.name,
        'salary': job.salary,
        'place': job.place,
        'city': job.city,
        'education': job.education,
        'experience': job.experience,
        'company': job.company,
        'company_type': job.company_type,
        'scale': job.scale,
        'industry': job.industry,
        'label': job.label,
        'description': job.description or '',
        'href': job.href or '',
        'source': job.source,
        'created_at': job.created_at.strftime('%Y-%m-%d') if job.created_at else '',
    }})


def send_job(request):
    """投递/取消投递"""
    if request.method == "POST":
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'code': 1, 'msg': '请先登录'})
        
        job_id = request.POST.get('job_id')
        action = request.POST.get('action', 'send')
        
        if not job_id:
            return JsonResponse({'code': 1, 'msg': '参数错误'})
        
        # 添加日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"投递请求 - 用户ID: {user_id}, 职位ID: {job_id}, 操作: {action}")
        
        try:
            job = JobData.objects.get(job_id=job_id)
        except JobData.DoesNotExist:
            logger.error(f"职位不存在: {job_id}")
            return JsonResponse({'code': 1, 'msg': '职位不存在'})
        
        # 获取用户对象
        from users.models import UserList
        try:
            user = UserList.objects.get(user_id=user_id)
        except UserList.DoesNotExist:
            logger.error(f"用户不存在: {user_id}")
            return JsonResponse({'code': 1, 'msg': '用户不存在'})
        
        if action == 'cancel':
            deleted_count = SendList.objects.filter(user=user, job=job).delete()[0]
            logger.info(f"取消投递 - 删除了 {deleted_count} 条记录")
            return JsonResponse({'code': 0, 'msg': '已取消投递'})
        else:
            try:
                obj, created = SendList.objects.get_or_create(
                    user=user,
                    job=job,
                    defaults={'status': 0}
                )
                if created:
                    logger.info(f"投递成功 - 创建记录ID: {obj.send_id}")
                    return JsonResponse({'code': 0, 'msg': '投递成功'})
                else:
                    logger.info(f"已投递过 - 记录ID: {obj.send_id}")
                    return JsonResponse({'code': 0, 'msg': '已投递过该职位'})
            except Exception as e:
                logger.error(f"投递失败: {str(e)}")
                return JsonResponse({'code': 1, 'msg': f'投递失败: {str(e)}'})
    
    return JsonResponse({'code': 1, 'msg': '请使用POST请求'})


def favorite_job(request):
    """收藏/取消收藏"""
    if request.method == "POST":
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'code': 1, 'msg': '请先登录'})

        job_id = request.POST.get('job_id')
        action = request.POST.get('action', 'favorite')

        if not job_id:
            return JsonResponse({'code': 1, 'msg': '参数错误'})

        try:
            job = JobData.objects.get(job_id=job_id)
        except JobData.DoesNotExist:
            return JsonResponse({'code': 1, 'msg': '职位不存在'})

        # 获取用户对象
        from users.models import UserList
        try:
            user = UserList.objects.get(user_id=user_id)
        except UserList.DoesNotExist:
            return JsonResponse({'code': 1, 'msg': '用户不存在'})

        if action == 'cancel':
            FavoriteJob.objects.filter(user=user, job=job).delete()
            return JsonResponse({'code': 0, 'msg': '已取消收藏'})
        else:
            _, created = FavoriteJob.objects.get_or_create(user=user, job=job)
            if created:
                return JsonResponse({'code': 0, 'msg': '收藏成功'})
            return JsonResponse({'code': 0, 'msg': '已收藏过该职位'})
    
    return JsonResponse({'code': 1, 'msg': '请使用POST请求'})


def my_send_list(request):
    """我的投递记录"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    return render(request, "jobs/my_send.html")


def get_my_send_list(request):
    """获取我的投递记录API"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 10))
    
    queryset = SendList.objects.filter(user_id=user_id).select_related('job')
    total = queryset.count()
    start = (page - 1) * limit
    end = page * limit
    
    data = []
    for send in queryset[start:end]:
        data.append({
            'send_id': send.send_id,
            'job_id': send.job.job_id,
            'name': send.job.name,
            'salary': send.job.salary,
            'place': send.job.place,
            'company': send.job.company,
            'education': send.job.education,
            'status_value': send.status,
            'status': send.get_status_display(),
            'created_at': send.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    
    return JsonResponse({"code": 0, "msg": "success", "count": total, "data": data})


def update_send_status(request):
    """更新投递状态"""
    if request.method == "POST":
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'code': 1, 'msg': '请先登录'})

        send_id = request.POST.get('send_id')
        status = request.POST.get('status')

        if not send_id or status is None:
            return JsonResponse({'code': 1, 'msg': '参数错误'})

        try:
            status = int(status)
        except ValueError:
            return JsonResponse({'code': 1, 'msg': '状态值错误'})

        if status not in [0, 1, 2, 3, 4]:
            return JsonResponse({'code': 1, 'msg': '状态不合法'})

        updated = SendList.objects.filter(send_id=send_id, user_id=user_id).update(status=status)
        if updated:
            return JsonResponse({'code': 0, 'msg': '状态已更新'})
        return JsonResponse({'code': 1, 'msg': '记录不存在'})

    return JsonResponse({'code': 1, 'msg': '请使用POST请求'})


def my_favorite_list(request):
    """我的收藏页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    return render(request, "jobs/my_favorite.html")


def get_my_favorite_list(request):
    """获取我的收藏列表API"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})

    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 10))

    queryset = FavoriteJob.objects.filter(user_id=user_id).select_related('job')
    total = queryset.count()
    start = (page - 1) * limit
    end = page * limit

    data = []
    for fav in queryset[start:end]:
        data.append({
            'favorite_id': fav.favorite_id,
            'job_id': fav.job.job_id,
            'name': fav.job.name,
            'salary': fav.job.salary,
            'place': fav.job.place,
            'company': fav.job.company,
            'education': fav.job.education,
            'created_at': fav.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    
    return JsonResponse({"code": 0, "msg": "success", "count": total, "data": data})


def job_expect(request):
    """求职意向页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    # 兼容旧数据：如果没有意向项，尝试从UserExpect迁移
    items = list(UserExpectItem.objects.filter(user_id=user_id).order_by('-updated_at'))
    if not items:
        legacy = UserExpect.objects.filter(user_id=user_id).first()
        if legacy:
            items = [UserExpectItem.objects.create(
                user_id=user_id,
                key_word=legacy.key_word,
                place=legacy.place,
                salary_min=legacy.salary_min,
                salary_max=legacy.salary_max
            )]

    if request.method == "POST":
        key_words = request.POST.getlist('key_word')
        places = request.POST.getlist('place')
        salary_mins = request.POST.getlist('salary_min')
        salary_maxs = request.POST.getlist('salary_max')

        # 清理旧数据
        UserExpectItem.objects.filter(user_id=user_id).delete()

        created = 0
        for idx in range(max(len(key_words), len(places), len(salary_mins), len(salary_maxs))):
            key_word = key_words[idx] if idx < len(key_words) else ''
            place = places[idx] if idx < len(places) else ''
            salary_min = salary_mins[idx] if idx < len(salary_mins) else ''
            salary_max = salary_maxs[idx] if idx < len(salary_maxs) else ''

            if not any([key_word, place, salary_min, salary_max]):
                continue

            item = UserExpectItem(user_id=user_id, key_word=key_word, place=place)
            if salary_min:
                try:
                    item.salary_min = float(salary_min)
                except:
                    pass
            if salary_max:
                try:
                    item.salary_max = float(salary_max)
                except:
                    pass
            item.save()
            created += 1

        if created == 0:
            return JsonResponse({'code': 1, 'msg': '至少填写一条求职意向'})
        return JsonResponse({'code': 0, 'msg': '保存成功'})

    if not items:
        items = [UserExpectItem(user_id=user_id)]

    return render(request, "jobs/job_expect.html", {'items': items})


def compare_jobs(request):
    """职位对比 API — 最多4个职位并排比较"""
    ids = request.GET.get('ids', '')
    if not ids:
        return JsonResponse({'code': 1, 'msg': '请传入职位ID'})
    id_list = [i.strip() for i in ids.split(',') if i.strip()][:4]
    jobs = JobData.objects.filter(job_id__in=id_list)
    data = []
    for job in jobs:
        data.append({
            'job_id': job.job_id,
            'name': job.name,
            'company': job.company,
            'salary': job.salary,
            'salary_min': float(job.salary_min) if job.salary_min else None,
            'salary_max': float(job.salary_max) if job.salary_max else None,
            'city': job.city,
            'education': job.education,
            'experience': job.experience,
            'company_type': job.company_type,
            'scale': job.scale,
            'industry': job.industry,
            'key_word': job.key_word,
            'source': job.source,
        })
    return JsonResponse({'code': 0, 'data': data})


def send_funnel(request):
    """投递漏斗数据 — 各状态数量"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    from django.db.models import Count
    counts = (SendList.objects
              .filter(user_id=user_id)
              .values('status')
              .annotate(n=Count('send_id')))
    status_map = {0: '已投递', 1: '已查看', 2: '邀请面试', 3: '不合适', 4: '已Offer'}
    result = {v: 0 for v in status_map.values()}
    for row in counts:
        label = status_map.get(row['status'], '未知')
        result[label] = row['n']
    total = sum(result.values())
    return JsonResponse({'code': 0, 'total': total, 'data': result})


def kanban(request):
    """求职进度看板页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    return render(request, 'jobs/kanban.html')


def get_kanban_data(request):
    """获取看板数据 — 按状态分组"""
    user_id = request.session.get('user_id')
    
    # 调试信息
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"看板请求 - 用户ID: {user_id}")
    
    if not user_id:
        logger.warning("看板请求失败 - 未登录")
        return JsonResponse({'code': 1, 'msg': '请先登录'})

    sends = SendList.objects.filter(user_id=user_id).select_related('job').order_by('-created_at')
    logger.info(f"找到 {sends.count()} 条投递记录")
    
    columns = {0: [], 1: [], 2: [], 4: [], 3: []}  # 按看板顺序
    for s in sends:
        col = columns.get(s.status, columns[0])
        card_data = {
            'send_id': s.send_id,
            'job_id': s.job.job_id,
            'name': s.job.name,
            'company': s.job.company,
            'salary': s.job.salary or '薪资面议',
            'city': s.job.city or '',
            'status': s.status,
            'created_at': s.created_at.strftime('%m-%d'),
        }
        col.append(card_data)
        logger.debug(f"添加卡片: {card_data['name']} 到状态 {s.status}")

    status_labels = {0: '已投递', 1: '已查看', 2: '邀请面试', 4: '已Offer', 3: '不合适'}
    status_colors = {0: 'primary', 1: 'info', 2: 'warning', 4: 'success', 3: 'secondary'}
    result = [
        {'status': k, 'label': status_labels[k], 'color': status_colors[k], 'cards': v}
        for k, v in columns.items()
    ]
    
    logger.info(f"返回 {len(result)} 列数据")
    return JsonResponse({'code': 0, 'data': result})


def move_kanban_card(request):
    """拖拽移动看板卡片 — 更新投递状态"""
    if request.method != 'POST':
        return JsonResponse({'code': 1, 'msg': '请使用POST'})
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})

    import json as _json
    try:
        body = _json.loads(request.body)
        send_id = body.get('send_id')
        new_status = int(body.get('status', 0))
    except Exception:
        send_id = request.POST.get('send_id')
        new_status = int(request.POST.get('status', 0))

    if new_status not in [0, 1, 2, 3, 4]:
        return JsonResponse({'code': 1, 'msg': '状态不合法'})

    updated = SendList.objects.filter(send_id=send_id, user_id=user_id).update(status=new_status)
    if updated:
        return JsonResponse({'code': 0, 'msg': '状态已更新'})
    return JsonResponse({'code': 1, 'msg': '记录不存在'})
