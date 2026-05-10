from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Q, Subquery
from django.core.cache import cache
from math import sqrt
from jobs.models import JobData, SendList, UserExpect, FavoriteJob, UserExpectItem
from agent.models import UserFeedback
import random


def recommend_page(request):
    """推荐页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    return render(request, "recommend/recommend.html")


def get_recommend_list(request):
    """获取推荐列表API - 支持换一批功能"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    k = int(request.GET.get('limit', 9))
    refresh = request.GET.get('refresh', 'false').lower() == 'true'  # 是否换一批
    
    # 换一批时不使用缓存
    cache_key = f"recommend_list:{user_id}:{k}"
    if not refresh:
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse(cached)
    
    recommend_jobs = recommend_by_item(user_id, k, refresh=refresh)
    favorite_ids = set(FavoriteJob.objects.filter(user_id=user_id).values_list('job_id', flat=True))
    for job in recommend_jobs:
        job['is_favorited'] = job.get('job_id') in favorite_ids
    
    response = {
        'code': 0,
        'msg': 'success',
        'count': len(recommend_jobs),
        'data': recommend_jobs
    }
    
    # 只有非刷新请求才缓存
    if not refresh:
        cache.set(cache_key, response, 300)
    
    return JsonResponse(response)


def calculate_similarity(job1_id, job2_id):
    """计算两个职位的相似度（基于余弦相似度）"""
    job1_users = SendList.objects.filter(job_id=job1_id)
    job1_count = job1_users.count()
    job2_count = SendList.objects.filter(job_id=job2_id).count()
    
    if job1_count == 0 or job2_count == 0:
        return 0
    
    common = SendList.objects.filter(
        user__in=Subquery(job1_users.values('user')),
        job_id=job2_id
    ).count()
    
    if common == 0:
        return 0
    
    return common / sqrt(job1_count * job2_count)


def recommend_by_item(user_id, k=9, refresh=False):
    """基于物品的协同过滤推荐，refresh=True 时换一批"""
    sent_jobs = list(SendList.objects.filter(user_id=user_id).values_list('job_id', flat=True))
    favorite_jobs = list(FavoriteJob.objects.filter(user_id=user_id).values_list('job_id', flat=True))
    positive_feedback = list(UserFeedback.objects.filter(
        user_id=user_id, feedback_type__in=['interested', 'applied']
    ).values_list('job_id', flat=True))
    negative_feedback = list(UserFeedback.objects.filter(
        user_id=user_id, feedback_type='not_interested'
    ).values_list('job_id', flat=True))

    seed_jobs = list(set(sent_jobs + favorite_jobs + positive_feedback))
    exclude_jobs = set(sent_jobs + favorite_jobs + negative_feedback)

    # 换一批：把已推荐过的也排除掉
    if refresh:
        history_key = f"recommend_history:{user_id}"
        history = cache.get(history_key) or set()
        exclude_jobs = exclude_jobs.union(history)

    if not seed_jobs:
        queryset = JobData.objects.all()
        expect_items = list(UserExpectItem.objects.filter(user_id=user_id))
        if not expect_items:
            legacy = UserExpect.objects.filter(user_id=user_id).first()
            expect_items = [legacy] if legacy else []

        if expect_items:
            q = Q()
            for expect in expect_items:
                if not expect:
                    continue
                item_q = Q()
                if expect.key_word:
                    item_q &= Q(name__icontains=expect.key_word) | Q(key_word__icontains=expect.key_word)
                if expect.place:
                    item_q &= Q(place__icontains=expect.place) | Q(city__icontains=expect.place)
                if expect.salary_min:
                    item_q &= Q(salary_max__gte=expect.salary_min)
                if expect.salary_max:
                    item_q &= Q(salary_min__lte=expect.salary_max)
                if item_q:
                    q |= item_q
            if q:
                queryset = queryset.filter(q)

            jobs = list(queryset.exclude(job_id__in=exclude_jobs).order_by('-salary_max')[:200])
            if len(jobs) > k:
                jobs = random.sample(jobs, k)
        else:
            jobs = list(
                JobData.objects.exclude(job_id__in=exclude_jobs)
                .order_by('-salary_max')[:k]
            )

        if refresh:
            _save_recommend_history(user_id, [j.job_id for j in jobs])
        return [format_job(job) for job in jobs]

    keyword_list = list(JobData.objects.filter(job_id__in=seed_jobs).values_list('key_word', flat=True))
    keyword_counts = {}
    for kw in keyword_list:
        if kw:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

    top_keywords = [kw[0] for kw in sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:3]]

    if not top_keywords:
        jobs = list(JobData.objects.exclude(job_id__in=exclude_jobs).order_by('?')[:k])
        if refresh:
            _save_recommend_history(user_id, [j.job_id for j in jobs])
        return [format_job(job) for job in jobs]

    unsent_jobs = list(JobData.objects.filter(
        key_word__in=top_keywords
    ).exclude(
        job_id__in=exclude_jobs
    ).order_by('?')[:200])

    if not unsent_jobs:
        jobs = list(JobData.objects.exclude(job_id__in=exclude_jobs).order_by('?')[:k])
        if refresh:
            _save_recommend_history(user_id, [j.job_id for j in jobs])
        return [format_job(job) for job in jobs]

    sent_job_objs = list(JobData.objects.filter(job_id__in=seed_jobs[:10]))

    distances = []
    for unsent_job in unsent_jobs:
        max_sim = 0
        for sent_job in sent_job_objs:
            sim = calculate_similarity(unsent_job.job_id, sent_job.job_id)
            if sim > max_sim:
                max_sim = sim
        if max_sim == 0 and unsent_job.key_word in top_keywords:
            max_sim = 0.1
        if unsent_job.key_word in top_keywords:
            max_sim += 0.05
        if refresh:
            max_sim += random.uniform(-0.03, 0.03)  # 增加随机性
        distances.append((max_sim, unsent_job))

    distances.sort(key=lambda x: x[0], reverse=True)

    recommend_list = []
    for sim, job in distances[:k]:
        recommend_list.append(format_job(job))

    if len(recommend_list) < k:
        extra_jobs = list(JobData.objects.exclude(
            job_id__in=list(exclude_jobs) + [j['job_id'] for j in recommend_list]
        ).order_by('?')[:k - len(recommend_list)])
        for job in extra_jobs:
            recommend_list.append(format_job(job))

    if refresh:
        _save_recommend_history(user_id, [j['job_id'] for j in recommend_list])

    return recommend_list


def _save_recommend_history(user_id, job_ids):
    """记录已推荐的职位，用于换一批时排除"""
    history_key = f"recommend_history:{user_id}"
    history = cache.get(history_key) or set()
    history = history.union(set(job_ids))
    # 最多记录200个，防止无限增长
    if len(history) > 200:
        history = set(list(history)[-200:])
    cache.set(history_key, history, 3600)


def format_job(job):
    """格式化职位数据"""
    return {
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
        'key_word': job.key_word,
        'source': job.source or '',
        'href': job.href or '',
    }
