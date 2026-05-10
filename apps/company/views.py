import os
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from .models import CompanyVerification
from .company_service import verify_company


def company_verify_page(request):
    """企业信息验证页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    return render(request, 'company/verify.html')


def api_verify_company(request):
    """
    POST /company/api/verify/
    Body: { "company_name": "xxx", "force_refresh": false }
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})

    if request.method != 'POST':
        return JsonResponse({'code': 1, 'msg': '请使用 POST 请求'})

    try:
        body = json.loads(request.body)
    except Exception:
        body = request.POST

    company_name = (body.get('company_name') or '').strip()
    force_refresh = body.get('force_refresh', False)

    if not company_name:
        return JsonResponse({'code': 1, 'msg': '请输入公司名称'})

    if len(company_name) > 100:
        return JsonResponse({'code': 1, 'msg': '公司名称过长'})

    result = verify_company(company_name, force_refresh=bool(force_refresh))

    if result.get('status') == 'verified':
        return JsonResponse({'code': 0, 'msg': '查询成功', 'data': result})
    elif result.get('status') == 'not_found':
        return JsonResponse({'code': 0, 'msg': '未找到该企业信息', 'data': result})
    else:
        return JsonResponse({
            'code': 0,
            'msg': result.get('message', '查询失败，请稍后重试'),
            'data': result,
        })


def api_batch_verify(request):
    """
    POST /company/api/batch/
    批量验证多个公司（最多20个）
    Body: { "companies": ["公司A", "公司B", ...] }
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})

    if request.method != 'POST':
        return JsonResponse({'code': 1, 'msg': '请使用 POST 请求'})

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'code': 1, 'msg': '请求格式错误'})

    companies = body.get('companies', [])
    if not companies:
        return JsonResponse({'code': 1, 'msg': '请提供公司列表'})

    if len(companies) > 20:
        return JsonResponse({'code': 1, 'msg': '单次最多验证20家公司'})

    results = {}
    for name in companies:
        name = str(name).strip()
        if name:
            results[name] = verify_company(name)

    return JsonResponse({'code': 0, 'msg': 'success', 'data': results})


def api_get_cached(request):
    """
    GET /company/api/cached/?company_name=xxx
    获取已缓存的企业信息（不触发新查询）
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})

    company_name = request.GET.get('company_name', '').strip()
    if not company_name:
        return JsonResponse({'code': 1, 'msg': '请提供公司名称'})

    try:
        obj = CompanyVerification.objects.get(company_name=company_name)
        from .company_service import _model_to_dict
        return JsonResponse({'code': 0, 'data': _model_to_dict(obj)})
    except CompanyVerification.DoesNotExist:
        return JsonResponse({'code': 0, 'data': None, 'msg': '暂无缓存数据'})


def company_list_page(request):
    """已验证企业列表页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    keyword = request.GET.get('keyword', '')
    status = request.GET.get('status', '')
    risk_level = request.GET.get('risk_level', '')

    queryset = CompanyVerification.objects.all()
    if keyword:
        queryset = queryset.filter(
            Q(company_name__icontains=keyword) |
            Q(unified_code__icontains=keyword) |
            Q(legal_person__icontains=keyword)
        )
    if status:
        queryset = queryset.filter(status=status)
    if risk_level:
        queryset = queryset.filter(risk_level=risk_level)

    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'company/list.html', {
        'page_obj': page_obj,
        'keyword': keyword,
        'status': status,
        'risk_level': risk_level,
        'total': queryset.count(),
    })


def api_company_list(request):
    """企业列表 JSON API"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})

    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    keyword = request.GET.get('keyword', '')
    status_filter = request.GET.get('status', '')
    risk_level = request.GET.get('risk_level', '')

    queryset = CompanyVerification.objects.all()
    if keyword:
        queryset = queryset.filter(
            Q(company_name__icontains=keyword) |
            Q(unified_code__icontains=keyword)
        )
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if risk_level:
        queryset = queryset.filter(risk_level=risk_level)

    total = queryset.count()
    start = (page - 1) * limit
    items = queryset[start:start + limit]

    data = []
    for obj in items:
        data.append({
            'id': obj.pk,
            'company_name': obj.company_name,
            'unified_code': obj.unified_code,
            'legal_person': obj.legal_person,
            'registered_capital': obj.registered_capital,
            'establishment_date': obj.establishment_date,
            'business_status': obj.business_status,
            'risk_level': obj.risk_level,
            'risk_summary': obj.risk_summary,
            'is_normal': obj.is_normal,
            'source': obj.source,
            'status': obj.status,
            'verified_at': obj.verified_at.strftime('%Y-%m-%d %H:%M') if obj.verified_at else '',
        })

    return JsonResponse({'code': 0, 'count': total, 'data': data})


def api_config_status(request):
    """返回当前已配置的 API Key 状态（不暴露 Key 值）"""
    return JsonResponse({
        'qichacha': bool(os.getenv('QICHACHA_KEY')),
        'tianyancha': bool(os.getenv('TIANYANCHA_TOKEN')),
    })
