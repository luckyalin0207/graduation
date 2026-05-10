"""
智能求职助手Agent - 视图层
"""
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from .job_search_agent import get_agent, AgentScheduler
from .models import AgentReport, UserFeedback
import json
import logging

logger = logging.getLogger(__name__)


def _is_admin_user(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return False
    from django.conf import settings
    admin_ids = getattr(settings, 'ADMIN_USER_IDS', ['admin'])
    return user_id in admin_ids


def agent_dashboard(request):
    """Agent控制台 - 主页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    return render(request, "agent/dashboard.html")


def agent_chat_page(request):
    """Agent 对话页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    return render(request, "agent/chat.html")


@require_http_methods(["GET"])
def get_recommendations(request):
    """获取职位推荐 - 使用纯传统算法，避免 LLM 批量调用超时"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    try:
        limit = int(request.GET.get('limit', 20))
        min_score = int(request.GET.get('min_score', 60))
        
        cache_key = f"agent_recs:{user_id}:{limit}:{min_score}"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse(cached)

        # 直接用传统算法，不走 LLM（避免超时）
        agent = get_agent(user_id)
        # 临时禁用 LLM，只用传统算法评分
        agent.llm_service = None
        
        recommendations = agent.recommend_jobs(limit=limit, min_score=min_score)
        
        data = [
            {
                'job_id': item['job'].job_id,
                'name': item['job'].name,
                'company': item['job'].company,
                'salary': item['job'].salary,
                'city': item['job'].city,
                'education': item['job'].education,
                'experience': item['job'].experience,
                'key_word': item['job'].key_word,
                'match_score': item['score'],
                'match_reasons': item['reasons'],
                'improvement_suggestions': item.get('improvement_suggestions', []),
                'llm_enhanced': False,
            }
            for item in recommendations
        ]
        
        response = {
            'code': 0,
            'msg': f'为您推荐了 {len(data)} 个职位',
            'data': data
        }
        cache.set(cache_key, response, 300)
        return JsonResponse(response)
    
    except Exception as e:
        logger.error(f"推荐失败: {str(e)}")
        return JsonResponse({'code': 1, 'msg': f'推荐失败: {str(e)}'})


@require_http_methods(["GET"])
def generate_report(request):
    """生成求职分析报告"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    try:
        agent = get_agent(user_id)
        # 禁用 LLM 批量评分，避免对500个职位逐个调用 LLM 导致超时
        agent.llm_service = None
        
        report = agent.generate_report()
        
        AgentReport.objects.create(
            user_id=user_id,
            report_data=report
        )
        
        return JsonResponse({
            'code': 0,
            'msg': '报告生成成功',
            'data': report
        })
    
    except Exception as e:
        logger.error(f"生成报告失败: {str(e)}", exc_info=True)
        return JsonResponse({'code': 1, 'msg': f'生成报告失败: {str(e)}'})


@require_http_methods(["GET"])
def get_apply_suggestions(request):
    """获取申请建议"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    try:
        # 创建Agent
        agent = get_agent(user_id)
        
        # 获取建议
        suggestions = agent.auto_apply_suggestions()
        
        return JsonResponse({
            'code': 0,
            'msg': f'为您生成了 {len(suggestions)} 条申请建议',
            'data': suggestions
        })
    
    except Exception as e:
        return JsonResponse({'code': 1, 'msg': f'生成建议失败: {str(e)}'})


@require_http_methods(["POST"])
def submit_feedback(request):
    """提交反馈"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    try:
        job_id = request.POST.get('job_id')
        feedback_type = request.POST.get('feedback_type')  # interested, not_interested, applied
        
        if not job_id or not feedback_type:
            return JsonResponse({'code': 1, 'msg': '参数不完整'})
        
        # 保存反馈
        UserFeedback.objects.create(
            user_id=user_id,
            job_id=job_id,
            feedback_type=feedback_type
        )
        
        return JsonResponse({'code': 0, 'msg': '反馈已提交，感谢您的参与！'})
    
    except Exception as e:
        return JsonResponse({'code': 1, 'msg': f'提交失败: {str(e)}'})


@require_http_methods(["GET"])
def get_salary_prediction(request):
    """获取薪资预测"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    try:
        # 创建Agent
        agent = get_agent(user_id)
        
        # 预测薪资
        prediction = agent.predict_salary_range()
        
        if prediction:
            return JsonResponse({
                'code': 0,
                'msg': '预测成功',
                'data': prediction
            })
        else:
            return JsonResponse({'code': 1, 'msg': '预测失败，请完善求职意向'})
    
    except Exception as e:
        return JsonResponse({'code': 1, 'msg': f'预测失败: {str(e)}'})


@require_http_methods(["GET"])
def get_report_history(request):
    """获取历史报告"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    try:
        reports = AgentReport.objects.filter(user_id=user_id)[:10]
        
        data = [
            {
                'id': report.id,
                'generated_at': report.generated_at.isoformat(),
                'recommendations_count': len(report.report_data.get('recommendations', [])),
                'salary_prediction': report.report_data.get('salary_prediction')
            }
            for report in reports
        ]
        
        return JsonResponse({
            'code': 0,
            'data': data
        })
    
    except Exception as e:
        return JsonResponse({'code': 1, 'msg': f'获取失败: {str(e)}'})


@require_http_methods(["GET", "POST"])
def llm_config(request):
    """大模型配置页面"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    # 移除管理员权限检查，允许所有登录用户访问
    
    from .models import LLMConfig
    
    if request.method == 'POST':
        try:
            config = LLMConfig.get_config()
            
            provider = request.POST.get('provider', 'none')
            api_key = request.POST.get('api_key', '').strip()
            secret_key = request.POST.get('secret_key', '').strip()
            model = request.POST.get('model', 'gpt-3.5-turbo').strip()
            base_url = request.POST.get('base_url', '').strip()
            enabled = request.POST.get('enabled') == 'on'
            
            # 验证配置
            if enabled and provider != 'none':
                if not api_key and not config.api_key:
                    return JsonResponse({'code': 1, 'msg': '请填写API Key'})
                
                if provider == 'wenxin' and not secret_key and not config.secret_key:
                    return JsonResponse({'code': 1, 'msg': '文心一言需要填写Secret Key'})
            
            # 保存配置
            config.provider = provider
            if api_key:
                config.api_key = api_key
            if secret_key:
                config.secret_key = secret_key
            config.model = model
            config.base_url = base_url if base_url else None
            config.enabled = enabled and provider != 'none'
            config.save()
            
            return JsonResponse({'code': 0, 'msg': '配置已保存！请刷新页面查看效果'})
        
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            return JsonResponse({'code': 1, 'msg': f'保存失败: {str(e)}'})
    
    # GET请求：显示配置页面
    config = LLMConfig.get_config()
    
    # 获取默认模型列表
    model_options = {
        'openai': [
            ('gpt-3.5-turbo', 'GPT-3.5 Turbo（推荐，便宜）'),
            ('gpt-4', 'GPT-4（更强大，更贵）'),
            ('gpt-4-turbo', 'GPT-4 Turbo'),
        ],
        'claude': [
            ('claude-3-sonnet-20240229', 'Claude 3 Sonnet（推荐）'),
            ('claude-3-opus-20240229', 'Claude 3 Opus（最强）'),
            ('claude-3-haiku-20240307', 'Claude 3 Haiku（最快）'),
        ],
        'wenxin': [
            ('ernie-bot-turbo', 'ERNIE-Bot-turbo（推荐）'),
            ('ernie-bot', 'ERNIE-Bot'),
            ('ernie-bot-4', 'ERNIE-Bot-4'),
        ],
    }
    
    context = {
        'config': config,
        'model_options': model_options,
    }
    
    return render(request, "agent/llm_config.html", context)


@require_http_methods(["POST"])
def test_llm_config(request):
    """测试大模型配置"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    # 移除管理员权限检查，允许所有登录用户测试

    try:
        from .models import LLMConfig
        from .llm_service import get_llm_service

        config = LLMConfig.get_config()
        
        if not config.enabled or config.provider == 'none':
            return JsonResponse({'code': 1, 'msg': '请先启用并配置大模型'})
        
        # 测试调用
        llm_service = get_llm_service()
        if not llm_service or not llm_service.enabled:
            return JsonResponse({'code': 1, 'msg': '大模型服务初始化失败，请检查配置'})
        
        # 简单测试
        test_prompt = "请回复'测试成功'"
        response = llm_service._call_api(test_prompt)
        
        if response:
            return JsonResponse({
                'code': 0,
                'msg': '测试成功！',
                'response': str(response)[:100]  # 只返回前100字符
            })
        else:
            return JsonResponse({'code': 1, 'msg': 'API调用失败，请检查API Key和网络连接'})
    
    except Exception as e:
        logger.error(f"测试配置失败: {str(e)}")
        return JsonResponse({'code': 1, 'msg': f'测试失败: {str(e)}'})


@require_http_methods(["GET"])
def run_daily_task(request):
    """手动触发每日推荐任务（管理员功能）"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    try:
        results = AgentScheduler.run_daily_recommendations()
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        
        return JsonResponse({
            'code': 0,
            'msg': f'任务执行完成，成功为 {success_count} 个用户推荐职位',
            'data': results
        })
    
    except Exception as e:
        return JsonResponse({'code': 1, 'msg': f'任务执行失败: {str(e)}'})


@require_http_methods(["GET"])
def debug_info(request):
    """调试信息 - 查看为什么没有推荐"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    try:
        from .job_search_agent import UserProfile
        from jobs.models import JobData
        
        profile = UserProfile(user_id)
        
        # 统计信息
        total_jobs = JobData.objects.count()
        sent_job_ids = profile.get_sent_job_ids()
        available_jobs = JobData.objects.exclude(job_id__in=sent_job_ids).count()
        
        # 用户画像信息
        profile_info = {
            'user_id': user_id,
            'has_expect': profile.expect is not None,
            'skills': profile.skills,
            'preferences': profile.preferences,
            'sent_jobs_count': len(profile.history)
        }
        
        # 如果设置了求职意向，统计匹配的职位数
        matched_count = 0
        if profile.expect:
            from django.db.models import Q
            jobs = JobData.objects.exclude(job_id__in=sent_job_ids)
            
            if profile.skills:
                q = Q()
                for skill in profile.skills:
                    q |= Q(name__icontains=skill) | Q(key_word__icontains=skill)
                jobs = jobs.filter(q)
                matched_count = jobs.count()
        
        return JsonResponse({
            'code': 0,
            'data': {
                'total_jobs_in_db': total_jobs,
                'available_jobs': available_jobs,
                'sent_jobs': len(sent_job_ids),
                'profile': profile_info,
                'matched_jobs_count': matched_count,
                'suggestions': []
            }
        })
    
    except Exception as e:
        return JsonResponse({'code': 1, 'msg': f'获取调试信息失败: {str(e)}'})



@require_http_methods(["POST"])
def chat(request):
    """
    对话式 Agent — 支持多轮记忆 + 自然语言指令
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})

    try:
        body = json.loads(request.body)
        message = body.get('message', '').strip()
    except Exception:
        message = request.POST.get('message', '').strip()

    if not message:
        return JsonResponse({'code': 1, 'msg': '请输入内容'})

    from .models import ChatSession

    # ── 读取最近10轮历史 ──────────────────────────────────
    history = list(ChatSession.objects.filter(user_id=user_id).order_by('-created_at')[:20])
    history.reverse()
    history_msgs = [{'role': h.role, 'content': h.content} for h in history]

    # ── 保存用户消息 ──────────────────────────────────────
    ChatSession.objects.create(user_id=user_id, role='user', content=message)

    # ── 优先使用LLM处理（类似Gemini的体验） ──────────────
    llm = get_llm_service()
    intent = 'chat'  # 默认意图
    
    # JD 对比意图（粘贴了较长文本）
    if len(message) > 100 and any(k in message for k in ['职位', '岗位', '要求', '负责', '技能', '经验', '任职', '工作职责']):
        intent = 'jd_compare'
        reply = _handle_jd_compare_with_llm(user_id, message, llm)
    # 如果LLM可用，优先用LLM处理所有问题
    elif llm and llm.enabled:
        intent = 'chat'
        reply = _handle_with_llm_first(user_id, message, history_msgs, llm)
    # LLM不可用时，使用意图识别+规则
    else:
        intent, params = _detect_intent(message)
        reply = _handle_intent(intent, params, user_id, message, history_msgs)

    # ── 保存 assistant 回复 ───────────────────────────────
    ChatSession.objects.create(
        user_id=user_id, role='assistant',
        content=reply.get('text', ''), intent=intent
    )

    # 只保留最近100条，避免无限增长
    old_ids = list(ChatSession.objects.filter(user_id=user_id)
                   .order_by('-created_at').values_list('id', flat=True)[100:])
    if old_ids:
        ChatSession.objects.filter(id__in=old_ids).delete()

    return JsonResponse({'code': 0, 'intent': intent, 'reply': reply})


@require_http_methods(["GET"])
def chat_history(request):
    """获取对话历史（用于页面刷新后恢复）"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    from .models import ChatSession
    msgs = list(ChatSession.objects.filter(user_id=user_id).order_by('created_at')
                .values('role', 'content', 'intent', 'created_at')[:50])
    for m in msgs:
        m['created_at'] = m['created_at'].strftime('%H:%M')
    return JsonResponse({'code': 0, 'data': msgs})


@require_http_methods(["POST"])
def clear_chat(request):
    """清空对话历史"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    from .models import ChatSession
    ChatSession.objects.filter(user_id=user_id).delete()
    return JsonResponse({'code': 0, 'msg': '对话已清空'})


def _detect_intent(text: str) -> tuple[str, dict]:
    """增强的意图识别 - 支持更多场景"""
    t = text.lower()

    # 面试准备
    if any(k in t for k in ['面试', '面经', '面试题', '面试准备', '怎么面', '面试技巧', '面试问题']):
        import re
        kw_match = re.search(r'([A-Za-z\u4e00-\u9fa5]{2,15})(?:工程师|开发|岗位|职位|的面试|面试)', text)
        kw = kw_match.group(1) if kw_match else ''
        return 'interview_prep', {'keyword': kw}

    # 职业规划
    if any(k in t for k in ['职业规划', '职业发展', '转行', '跳槽', '晋升', '发展方向', '职业路径', '未来发展']):
        return 'career_plan', {}

    # 公司评价
    if any(k in t for k in ['公司怎么样', '公司评价', '公司靠谱吗', '这家公司', '企业信息', '公司背景']):
        import re
        co_match = re.search(r'([A-Za-z\u4e00-\u9fa5]{2,20})(?:公司|企业|怎么样|靠谱)', text)
        co = co_match.group(1) if co_match else ''
        return 'company_review', {'company': co}

    # 技能学习建议
    if any(k in t for k in ['学什么', '学习路线', '怎么学', '技能提升', '需要掌握', '学习建议', '技术栈']):
        import re
        kw_match = re.search(r'([A-Za-z\u4e00-\u9fa5]{2,15})(?:工程师|开发|岗位|职位|需要|学习)', text)
        kw = kw_match.group(1) if kw_match else ''
        return 'skill_learning', {'keyword': kw}

    # 求职策略
    if any(k in t for k in ['求职策略', '找工作技巧', '投递策略', '怎么找工作', '求职建议', '投递建议']):
        return 'job_strategy', {}

    # 爬虫管理
    if any(k in t for k in ['爬虫', '爬取', '抓取', '启动爬虫', '开始爬', '采集数据']):
        import re
        kw_match = re.search(r'["\']?([A-Za-z\u4e00-\u9fa5]+)["\']?\s*(?:岗位|职位|工作|相关)?', text)
        kw = kw_match.group(1) if kw_match else 'Python'
        return 'spider', {'keyword': kw}

    # 简历优化
    if any(k in t for k in ['简历', '优化简历', '改进简历', '简历建议', '简历怎么写', '简历修改']):
        return 'resume_optimize', {}

    # 薪资查询
    if any(k in t for k in ['薪资', '工资', '薪水', '多少钱', '行情', '待遇', '收入']):
        import re
        kw_match = re.search(r'([A-Za-z\u4e00-\u9fa5]{2,15})(?:工程师|开发|岗位|职位|工作|的薪资|的工资|的待遇)', text)
        kw = kw_match.group(1) if kw_match else ''
        return 'salary_query', {'keyword': kw}

    # 职位推荐
    if any(k in t for k in ['推荐', '找工作', '职位', '岗位', '工作机会', '合适的工作', '适合我']):
        return 'job_recommend', {}

    # 数据统计
    if any(k in t for k in ['统计', '数据', '多少', '数量', '分析', '概览']):
        return 'stats', {}

    # 帮助
    if any(k in t for k in ['帮助', 'help', '能做什么', '功能', '怎么用', '使用说明']):
        return 'help', {}

    return 'chat', {}


def _handle_with_llm_first(user_id: str, message: str, history: list, llm) -> dict:
    """
    优先使用LLM处理所有问题（类似Gemini的体验）
    提供更智能、更灵活的对话能力
    """
    try:
        from users.models import UserWorkExperience, UserEducation
        from jobs.models import UserExpectItem, SendList
        
        # 构建用户上下文
        user_context = []
        
        # 获取用户背景
        expect = UserExpectItem.objects.filter(user_id=user_id).first()
        if expect:
            user_context.append(f"求职意向：{expect.key_word}")
            user_context.append(f"期望城市：{expect.city}")
            user_context.append(f"期望薪资：{expect.salary_min}-{expect.salary_max}K")
        
        works = list(UserWorkExperience.objects.filter(user_id=user_id).values('company', 'title', 'years')[:3])
        if works:
            total_years = sum(float(w.get('years', 0) or 0) for w in works)
            user_context.append(f"工作经验：{total_years:.1f}年")
            user_context.append(f"最近职位：{works[0]['title']} @ {works[0]['company']}")
        
        edu = UserEducation.objects.filter(user_id=user_id).first()
        if edu:
            user_context.append(f"学历：{edu.degree} {edu.major}")
        
        my_sends = SendList.objects.filter(user_id=user_id).count()
        if my_sends > 0:
            user_context.append(f"已投递：{my_sends}个职位")
        
        # 构建系统提示词
        system_prompt = """你是一个专业的求职顾问和职业规划师，专注于帮助求职者找到理想工作。

你的能力包括：
1. 分析职位JD，评估匹配度，提供面试建议
2. 提供职业规划和发展建议
3. 优化简历，提升竞争力
4. 分析薪资行情和市场趋势
5. 提供面试准备和技巧
6. 评估公司背景和风险
7. 推荐学习路线和技能提升方案
8. 提供求职策略和方法论

回答要求：
- 专业、实用、可操作
- 结构清晰，使用Markdown格式
- 针对用户背景提供个性化建议
- 如果是分析JD，必须包含：匹配度评估、优势分析、差距分析、面试建议
- 回答长度适中（200-500字），重点突出
"""
        
        # 添加用户上下文
        if user_context:
            system_prompt += f"\n\n用户背景：\n" + "\n".join(f"- {c}" for c in user_context)
        
        # 构建消息列表
        messages = [{'role': 'system', 'content': system_prompt}]
        
        # 加入最近5轮历史（提供上下文）
        if history:
            messages.extend(history[-10:])
        
        messages.append({'role': 'user', 'content': message})
        
        # 调用LLM
        import requests as _req
        headers = {
            'Authorization': f'Bearer {llm.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': llm.model,
            'messages': messages,
            'temperature': 0.7,
            'max_tokens': 1500  # 增加token限制，支持更长回复
        }
        
        r = _req.post(
            f'{llm.base_url}/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if r.status_code == 200:
            response = r.json()['choices'][0]['message']['content']
            return {'type': 'markdown', 'text': response}
        else:
            logger.warning(f'LLM API返回 {r.status_code}，使用规则兜底')
            # 降级到规则处理
            intent, params = _detect_intent(message)
            return _handle_intent(intent, params, user_id, message, history)
    
    except Exception as e:
        logger.error(f'LLM处理失败: {str(e)}，使用规则兜底')
        # 降级到规则处理
        intent, params = _detect_intent(message)
        return _handle_intent(intent, params, user_id, message, history)


def _handle_jd_compare_with_llm(user_id: str, jd_text: str, llm) -> dict:
    """
    使用LLM深度分析JD匹配度（支持所有类型岗位）
    """
    if not llm or not llm.enabled:
        # LLM不可用，使用规则兜底
        intent, params = _detect_intent(jd_text)
        return _handle_intent('jd_compare', params, user_id, jd_text, [])
    
    try:
        from users.models import UserWorkExperience, UserEducation
        from jobs.models import UserExpectItem
        
        # 构建用户简历摘要
        resume_parts = []
        
        expect = UserExpectItem.objects.filter(user_id=user_id).first()
        if expect:
            resume_parts.append(f"**求职意向**：{expect.key_word}")
            resume_parts.append(f"**期望城市**：{expect.city}")
            resume_parts.append(f"**期望薪资**：{expect.salary_min}-{expect.salary_max}K/月")
        
        works = list(UserWorkExperience.objects.filter(user_id=user_id).values('company', 'title', 'description', 'years')[:3])
        if works:
            resume_parts.append(f"\n**工作经历**：")
            for w in works:
                years = w.get('years', 0) or 0
                resume_parts.append(f"- {w['company']} | {w['title']} | {years}年")
                if w.get('description'):
                    resume_parts.append(f"  {w['description'][:100]}")
        
        edu = UserEducation.objects.filter(user_id=user_id).first()
        if edu:
            resume_parts.append(f"\n**教育背景**：{edu.school} | {edu.degree} | {edu.major}")
        
        resume_summary = "\n".join(resume_parts) if resume_parts else "暂无简历信息"
        
        # 构建LLM提示词
        prompt = f"""请作为专业的求职顾问，深度分析以下求职者与职位的匹配情况。

# 求职者简历

{resume_summary}

# 目标职位JD

{jd_text[:1500]}

# 分析要求

请从以下维度进行分析（使用Markdown格式）：

## 1. 整体匹配度评估
- 给出匹配度分数（0-100分）
- 说明评分依据

## 2. 优势分析
- 列出3-5个匹配的优势点
- 每条要具体，说明为什么匹配

## 3. 差距分析
- 列出3-5个需要提升的方面
- 每条要具体，说明如何弥补

## 4. 面试准备建议
- 提供3-5条具体的面试准备建议
- 包括：如何展示优势、如何回答可能的问题、需要准备的案例

## 5. 行动计划
- 如果匹配度高：如何提高面试成功率
- 如果匹配度低：如何快速提升竞争力

要求：
- 分析要深入、具体、可操作
- 针对该岗位的特点提供建议
- 考虑求职者的实际背景
- 语言专业但易懂
"""
        
        # 调用LLM
        import requests as _req
        headers = {
            'Authorization': f'Bearer {llm.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': llm.model,
            'messages': [
                {'role': 'system', 'content': '你是资深的求职顾问，擅长分析职位匹配度和提供面试建议。'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 2000  # JD分析需要更长的回复
        }
        
        r = _req.post(
            f'{llm.base_url}/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if r.status_code == 200:
            response = r.json()['choices'][0]['message']['content']
            return {'type': 'markdown', 'text': f'📋 **职位匹配度深度分析**\n\n{response}'}
        else:
            logger.warning(f'LLM API返回 {r.status_code}，使用规则兜底')
            # 降级到规则处理
            return _handle_intent('jd_compare', {}, user_id, jd_text, [])
    
    except Exception as e:
        logger.error(f'JD分析失败: {str(e)}，使用规则兜底')
        # 降级到规则处理
        return _handle_intent('jd_compare', {}, user_id, jd_text, [])


def _handle_intent(intent: str, params: dict, user_id: str, raw_message: str, history: list = None) -> dict:
    """根据意图执行对应操作"""

    # ── 面试准备 ──────────────────────────────────────────
    if intent == 'interview_prep':
        kw = params.get('keyword', '')
        if not kw:
            return {
                'type': 'markdown',
                'text': '''🎯 **面试准备指南**

请告诉我你要面试的岗位，例如：
- "Python工程师面试准备"
- "前端开发面试题"
- "数据分析师面试技巧"

我会为你提供：
✅ 常见面试题
✅ 技术要点
✅ 面试技巧
✅ 注意事项'''
            }

        # 尝试用LLM生成面试准备建议
        llm = get_llm_service()
        if llm and llm.enabled:
            try:
                prompt = f"""你是资深的技术面试官。请为"{kw}"岗位的求职者提供面试准备建议。

请包含以下内容（每部分3-5条，简洁实用）：
1. 高频面试题（列出具体题目）
2. 核心技术要点（需要重点准备的知识）
3. 面试技巧（回答问题的方法）
4. 注意事项（容易踩的坑）

用中文回答，使用Markdown格式，每条建议要具体可操作。"""
                response = llm._call_api(prompt)
                if response:
                    return {'type': 'markdown', 'text': f'🎯 **{kw} 面试准备**\n\n{response}'}
            except Exception:
                pass

        # 规则兜底
        return {
            'type': 'markdown',
            'text': f'''🎯 **{kw} 面试准备**

**📝 常见面试题**
1. 自我介绍（突出项目经验和技术亮点）
2. 项目经历（STAR法则：情境、任务、行动、结果）
3. 技术深度（核心技术栈的原理和应用）
4. 问题解决（遇到的技术难题及解决方案）
5. 职业规划（为什么选择这个岗位）

**💡 面试技巧**
- 提前了解公司业务和技术栈
- 准备3-5个项目案例，能深入讲解
- 回答问题要有逻辑：先总后分
- 不会的问题诚实说明，展示学习能力
- 准备2-3个有深度的问题问面试官

**⚠️ 注意事项**
- 简历上的每个技术点都要能讲清楚
- 不要夸大技术能力
- 注意时间管理，不要长篇大论
- 保持自信但不傲慢
- 面试后24小时内发感谢邮件

💪 祝你面试顺利！'''
        }

    # ── 职业规划 ──────────────────────────────────────────
    elif intent == 'career_plan':
        from users.models import UserWorkExperience, UserEducation
        from jobs.models import UserExpectItem

        works = list(UserWorkExperience.objects.filter(user_id=user_id).values('company', 'title', 'years'))
        edu = UserEducation.objects.filter(user_id=user_id).first()
        expect = UserExpectItem.objects.filter(user_id=user_id).first()

        # 构建用户背景
        background = []
        if edu:
            background.append(f"学历：{edu.degree} {edu.major}")
        if works:
            total_years = sum(float(w.get('years', 0) or 0) for w in works)
            background.append(f"工作经验：{total_years:.1f}年")
            background.append(f"当前/最近职位：{works[0]['title']}")
        if expect:
            background.append(f"期望方向：{expect.key_word}")

        if not background:
            return {
                'type': 'text',
                'text': '请先完善个人信息（学历、工作经历、求职意向），我才能给出更准确的职业规划建议。',
                'link': {'text': '去完善信息', 'url': '/user_info/'}
            }

        # 尝试用LLM生成职业规划
        llm = get_llm_service()
        if llm and llm.enabled:
            try:
                prompt = f"""你是资深的职业规划顾问。请为以下求职者提供职业发展建议。

求职者背景：
{chr(10).join(background)}

请提供：
1. 当前职业阶段分析（初级/中级/高级）
2. 短期发展建议（1-2年内）
3. 长期发展路径（3-5年）
4. 需要提升的技能
5. 具体行动建议

用中文回答，简洁实用，每条建议要具体可操作。"""
                response = llm._call_api(prompt)
                if response:
                    return {'type': 'markdown', 'text': f'🎯 **职业规划建议**\n\n{response}'}
            except Exception:
                pass

        # 规则兜底
        return {
            'type': 'markdown',
            'text': f'''🎯 **职业规划建议**

**📊 你的背景**
{chr(10).join(f"- {b}" for b in background)}

**🚀 发展建议**

**短期目标（1-2年）**
- 深化当前技术栈，成为领域专家
- 积累2-3个有影响力的项目经验
- 提升软技能：沟通、协作、项目管理
- 建立个人技术品牌（博客、开源贡献）

**中期目标（3-5年）**
- 向技术专家或技术管理方向发展
- 掌握架构设计和系统优化能力
- 培养团队协作和领导能力
- 扩展技术视野，了解新技术趋势

**💡 行动建议**
1. 每周学习新技术，保持技术敏感度
2. 参与技术社区，扩展人脉
3. 定期复盘项目，总结经验教训
4. 关注行业动态，把握发展机会
5. 投资自己，持续学习和成长

需要更具体的建议？告诉我你的具体情况！'''
        }

    # ── 公司评价 ──────────────────────────────────────────
    elif intent == 'company_review':
        company = params.get('company', '')
        if not company:
            return {'type': 'text', 'text': '请告诉我你想了解哪家公司，例如："阿里巴巴公司怎么样"'}

        from company.models import CompanyInfo
        from jobs.models import JobData
        from django.db.models import Avg, Count

        # 查询公司信息
        company_info = CompanyInfo.objects.filter(company_name__icontains=company).first()
        
        # 统计该公司的职位数据
        jobs = JobData.objects.filter(company__icontains=company)
        job_stats = jobs.aggregate(
            count=Count('job_id'),
            avg_salary=Avg('salary_max')
        )

        if company_info:
            status_emoji = '✅' if company_info.is_normal else '⚠️'
            risk_color = {'低': '🟢', '中': '🟡', '高': '🔴'}.get(company_info.risk_level, '⚪')
            
            text = f'''🏢 **{company_info.company_name}**

**基本信息**
- 企业状态：{status_emoji} {company_info.business_status or "正常"}
- 风险等级：{risk_color} {company_info.risk_level}风险
- 注册资本：{company_info.registered_capital or "未知"}
- 成立时间：{company_info.establishment_date or "未知"}
- 企业类型：{company_info.company_type or "未知"}
- 所属行业：{company_info.industry or "未知"}

**招聘信息**
- 在招职位：{job_stats['count']}个
- 平均薪资：{round(job_stats['avg_salary'] or 0, 1)}K/月

**风险提示**
{company_info.risk_summary or "暂无风险记录"}

💡 建议：面试前多了解公司文化和团队氛围'''
            
            return {'type': 'markdown', 'text': text}
        elif job_stats['count'] > 0:
            return {
                'type': 'markdown',
                'text': f'''🏢 **{company}**

**招聘信息**
- 在招职位：{job_stats['count']}个
- 平均薪资：{round(job_stats['avg_salary'] or 0, 1)}K/月

暂无详细企业信息，建议：
1. 在企查查/天眼查查询企业背景
2. 在脉脉/看准网查看员工评价
3. 面试时多问公司文化和团队情况

[验证企业信息](/company/verify/)'''
            }
        else:
            return {
                'type': 'text',
                'text': f'暂无 {company} 的信息。你可以：\n1. 在企查查/天眼查查询\n2. 让我爬取该公司的职位数据\n3. 在脉脉/看准网查看员工评价'
            }

    # ── 技能学习建议 ──────────────────────────────────────
    elif intent == 'skill_learning':
        kw = params.get('keyword', '')
        if not kw:
            return {
                'type': 'text',
                'text': '请告诉我你想学习哪个方向的技能，例如："Python工程师需要学什么"'
            }

        # 尝试用LLM生成学习路线
        llm = get_llm_service()
        if llm and llm.enabled:
            try:
                prompt = f"""你是资深的技术导师。请为想成为"{kw}"的学习者提供学习路线。

请包含：
1. 必备基础知识（3-5项）
2. 核心技能清单（按优先级排序）
3. 学习路径（从入门到精通）
4. 推荐学习资源（书籍、课程、网站）
5. 实践项目建议（3-5个由易到难的项目）

用中文回答，简洁实用，重点突出。"""
                response = llm._call_api(prompt)
                if response:
                    return {'type': 'markdown', 'text': f'📚 **{kw} 学习路线**\n\n{response}'}
            except Exception:
                pass

        # 规则兜底
        return {
            'type': 'markdown',
            'text': f'''📚 **{kw} 学习路线**

**🎯 学习阶段**

**第一阶段：基础入门（1-2个月）**
- 掌握编程语言基础语法
- 了解数据结构和算法
- 学习版本控制（Git）
- 熟悉开发工具和环境

**第二阶段：核心技能（3-6个月）**
- 深入学习核心框架和库
- 掌握数据库操作
- 学习Web开发基础
- 了解软件工程最佳实践

**第三阶段：项目实战（持续）**
- 完成3-5个实战项目
- 参与开源项目贡献
- 学习系统设计和架构
- 提升代码质量和性能优化

**💡 学习建议**
1. 理论与实践结合，多动手写代码
2. 每天坚持学习，保持连续性
3. 加入技术社区，多交流学习
4. 定期复盘总结，建立知识体系
5. 关注行业动态，持续更新技能

**📖 推荐资源**
- 官方文档（最权威）
- GitHub优秀项目（学习实战）
- 技术博客和教程
- 在线课程平台

需要更具体的学习计划？告诉我你的基础和目标！'''
        }

    # ── 求职策略 ──────────────────────────────────────────
    elif intent == 'job_strategy':
        from jobs.models import SendList
        my_sends = SendList.objects.filter(user_id=user_id).count()
        
        return {
            'type': 'markdown',
            'text': f'''🎯 **求职策略建议**

**📊 你的投递情况**
- 已投递：{my_sends}个职位

**💡 高效求职策略**

**1. 精准定位（最重要）**
- 明确目标岗位和行业
- 了解市场需求和薪资水平
- 评估自身竞争力，找准定位

**2. 简历优化**
- 针对目标岗位定制简历
- 突出项目成果和数据
- 使用关键词提高匹配度
- 保持简洁，1-2页为宜

**3. 投递策略**
- 每天投递5-10个精选职位
- 避免海投，提高针对性
- 优先投递近期发布的职位
- 关注公司规模和发展阶段

**4. 面试准备**
- 提前了解公司和岗位
- 准备常见面试题
- 模拟面试练习
- 准备问面试官的问题

**5. 跟进技巧**
- 面试后24小时内发感谢邮件
- 1周后可礼貌询问进度
- 保持多个机会并行
- 做好面试复盘总结

**⏰ 时间规划**
- 上午：投递职位（10-20个/周）
- 下午：准备面试、学习提升
- 晚上：复盘总结、优化简历

**🎯 目标设定**
- 第1周：投递20+职位，获得5+面试
- 第2周：完成面试，收到2+offer
- 第3周：选择最佳offer，准备入职

坚持下去，相信你一定能找到理想工作！💪'''
        }

    # ── 爬虫管理 ──────────────────────────────────────────
    if intent == 'spider':
        from spider.models import SpiderInfo
        info = SpiderInfo.objects.first()
        if info and info.status == 1:
            return {
                'type': 'text',
                'text': f'⚠️ 爬虫正在运行中，请稍后再试。\n当前已爬取 **{info.total_count}** 条数据。'
            }
        kw = params.get('keyword', 'Python')
        return {
            'type': 'action',
            'text': f'好的，我来帮你爬取 **{kw}** 相关职位数据。',
            'action': 'start_spider',
            'action_params': {'keyword': kw, 'pages': 3},
            'buttons': [
                {'label': f'启动爬取（{kw}，3页）', 'action': 'start_spider', 'params': {'keyword': kw, 'pages': 3}},
                {'label': '取消', 'action': 'cancel'},
            ]
        }

    # ── 简历优化 ──────────────────────────────────────────
    elif intent == 'resume_optimize':
        from users.models import UserWorkExperience, UserEducation
        from jobs.models import UserExpectItem

        works = list(UserWorkExperience.objects.filter(user_id=user_id).values('company', 'title', 'description'))
        edus = list(UserEducation.objects.filter(user_id=user_id).values('school', 'degree', 'major'))
        expect = UserExpectItem.objects.filter(user_id=user_id).first()
        skills = expect.key_word if expect else ''

        if not works and not edus and not skills:
            return {
                'type': 'text',
                'text': '📄 我还没有看到你的简历信息。\n\n请先前往 **个人信息页** 上传简历，我会自动解析并给出优化建议。',
                'link': {'text': '去上传简历', 'url': '/user_info/'}
            }

        # 构建简历摘要
        resume_summary = f"技能：{skills}\n"
        for w in works[:3]:
            resume_summary += f"工作：{w['company']} - {w['title']}\n"
        for e in edus[:2]:
            resume_summary += f"教育：{e['school']} {e['degree']} {e['major']}\n"

        # 尝试用 LLM 优化
        llm = get_llm_service()
        if llm and llm.enabled:
            try:
                prompt = f"""你是专业的简历优化顾问。请分析以下简历并给出具体改进建议。

简历信息：
{resume_summary}

请从以下方面给出建议（每条建议要具体可操作）：
1. 技能描述优化
2. 工作经历亮点提炼
3. 缺失的关键信息
4. 整体改进方向

用中文回答，简洁明了，每条建议不超过50字。"""
                response = llm._call_api(prompt)
                if response:
                    return {'type': 'markdown', 'text': f'📝 **简历优化建议**\n\n{response}'}
            except Exception:
                pass

        # 规则兜底
        suggestions = []
        if not skills:
            suggestions.append('💡 **补充技能关键词** — 在求职意向中添加你掌握的技术栈')
        if len(works) < 2:
            suggestions.append('💡 **丰富工作经历** — 添加实习或项目经历，突出成果数据')
        if not edus:
            suggestions.append('💡 **完善教育背景** — 添加学校、专业、学历信息')
        suggestions.append('💡 **量化成果** — 用数字描述工作成果，如"提升性能30%"')
        suggestions.append('💡 **关键词匹配** — 参考目标职位JD，在简历中加入相关关键词')

        return {
            'type': 'markdown',
            'text': '📝 **简历优化建议**\n\n' + '\n'.join(suggestions)
        }

    # ── 薪资查询 ──────────────────────────────────────────
    elif intent == 'salary_query':
        from jobs.models import JobData
        from django.db.models import Avg, Max, Min, Count
        kw = params.get('keyword', '')
        if not kw:
            return {'type': 'text', 'text': '请告诉我你想查询哪个岗位的薪资，例如：**Python工程师薪资行情**'}

        jobs = JobData.objects.filter(name__icontains=kw).exclude(salary_max__isnull=True)
        if not jobs.exists():
            jobs = JobData.objects.filter(key_word__icontains=kw).exclude(salary_max__isnull=True)

        if not jobs.exists():
            return {'type': 'text', 'text': f'暂无 **{kw}** 相关薪资数据，建议先爬取该岗位数据。'}

        stats = jobs.aggregate(avg=Avg('salary_max'), mx=Max('salary_max'), mn=Min('salary_min'), cnt=Count('job_id'))
        avg = round(stats['avg'] or 0, 1)
        mx = round(stats['mx'] or 0, 1)
        mn = round(stats['mn'] or 0, 1)
        cnt = stats['cnt']

        # 城市分布
        city_stats = jobs.values('city').annotate(avg=Avg('salary_max')).order_by('-avg')[:5]
        city_lines = '\n'.join(f"  - {c['city']}: {round(c['avg'],1)}K" for c in city_stats if c['city'])

        text = f"""💰 **{kw} 薪资行情**（基于 {cnt} 条数据）

| 指标 | 数值 |
|------|------|
| 平均薪资 | **{avg}K/月** |
| 最高薪资 | {mx}K/月 |
| 最低薪资 | {mn}K/月 |

**薪资最高城市 TOP5：**
{city_lines}"""
        return {'type': 'markdown', 'text': text}

    # ── 职位推荐 ──────────────────────────────────────────
    elif intent == 'job_recommend':
        try:
            agent = get_agent(user_id)
            agent.llm_service = None  # 禁用 LLM 批量评分，避免超时
            recs = agent.recommend_jobs(limit=5, min_score=50)
            if not recs:
                return {
                    'type': 'text',
                    'text': '暂无推荐职位，请先设置求职意向或上传简历。',
                    'link': {'text': '设置求职意向', 'url': '/job/expect/'}
                }
            lines = []
            for r in recs[:5]:
                job = r['job']
                lines.append(f"- **{job.name}** | {job.company} | {job.salary or '薪资面议'} | 匹配度 {r['score']}分")
            return {
                'type': 'markdown',
                'text': '🎯 **为你推荐的职位**\n\n' + '\n'.join(lines) + '\n\n[查看全部推荐](/agent/)',
            }
        except Exception as e:
            return {'type': 'text', 'text': f'推荐失败：{str(e)}'}

    # ── 数据统计 ──────────────────────────────────────────
    elif intent == 'stats':
        from jobs.models import JobData, SendList
        from django.db.models import Avg
        total = JobData.objects.count()
        avg_salary = JobData.objects.exclude(salary_max__isnull=True).aggregate(avg=Avg('salary_max'))['avg'] or 0
        my_sends = SendList.objects.filter(user_id=user_id).count()
        text = f"""📊 **数据概览**

- 职位总数：**{total}** 条
- 平均薪资：**{round(avg_salary, 1)}K/月**
- 我的投递：**{my_sends}** 个"""
        return {'type': 'markdown', 'text': text}

    # ── 帮助 ──────────────────────────────────────────────
    elif intent == 'help':
        return {
            'type': 'markdown',
            'text': """🤖 **我能帮你做这些事：**

**📝 简历与求职**
| 指令示例 | 功能 |
|---------|------|
| 优化我的简历 | 分析简历并给出改进建议 |
| 粘贴职位JD | 自动分析匹配度和差距 |
| 推荐适合我的职位 | 基于意向智能推荐 |
| 求职策略建议 | 提供高效求职方法 |

**💰 薪资与市场**
| 指令示例 | 功能 |
|---------|------|
| Python工程师薪资行情 | 查询岗位薪资统计 |
| 数据统计 | 查看平台数据概览 |
| 阿里巴巴公司怎么样 | 查询企业信息和评价 |

**🎯 面试与发展**
| 指令示例 | 功能 |
|---------|------|
| Python工程师面试准备 | 提供面试题和技巧 |
| 职业规划建议 | 分析发展路径 |
| Python工程师需要学什么 | 提供学习路线 |

**🕷️ 数据管理**
| 指令示例 | 功能 |
|---------|------|
| 帮我爬取Python职位 | 启动爬虫抓取数据 |

直接用自然语言告诉我你想做什么就好！"""
        }

    # ── JD 对比分析 ──────────────────────────────────────
    elif intent == 'jd_compare':
        from users.models import UserWorkExperience, UserEducation
        from jobs.models import UserExpectItem
        from apps.users.resume_parser import TECH_SKILLS

        expect = UserExpectItem.objects.filter(user_id=user_id).first()
        user_skills = set(s.strip().lower() for s in (expect.key_word or '').split(',') if s.strip())
        works = list(UserWorkExperience.objects.filter(user_id=user_id).values('company', 'title'))
        edu = UserEducation.objects.filter(user_id=user_id).first()

        # 从 JD 文本提取要求的技能
        jd_skills = set()
        for sk in TECH_SKILLS:
            if sk.lower() in raw_message.lower():
                jd_skills.add(sk.lower())

        matched = user_skills & jd_skills
        missing = jd_skills - user_skills

        # 尝试 LLM 深度分析
        llm = get_llm_service()
        if llm and llm.enabled:
            try:
                resume_summary = f"技能：{', '.join(user_skills)}\n"
                for w in works[:2]:
                    resume_summary += f"工作：{w['company']} {w['title']}\n"
                if edu:
                    resume_summary += f"学历：{edu.degree} {edu.school}\n"

                prompt = f"""你是专业的求职顾问。请对比以下简历和职位JD，给出匹配分析。

我的简历：
{resume_summary}

职位JD：
{raw_message[:800]}

请分析：
1. 匹配的技能和经验（列出具体项）
2. 缺失的关键要求（列出具体项）
3. 整体匹配度评估（0-100分）
4. 针对这个职位的3条具体建议

用中文回答，简洁明了。"""
                response = llm._call_api(prompt)
                if response:
                    return {'type': 'markdown', 'text': f'📋 **JD 匹配分析**\n\n{response}'}
            except Exception:
                pass

        # 规则兜底
        lines = [f'📋 **JD 匹配分析**\n']
        if matched:
            lines.append(f'✅ **已匹配技能**：{", ".join(matched)}')
        if missing:
            lines.append(f'❌ **缺失技能**：{", ".join(missing)}')
            lines.append(f'\n💡 建议补充：{", ".join(list(missing)[:3])} 相关经验')
        if not jd_skills:
            lines.append('未从 JD 中识别到具体技术要求，建议手动对比。')
        match_pct = int(len(matched) / max(len(jd_skills), 1) * 100) if jd_skills else 50
        lines.append(f'\n📊 **技能匹配度：{match_pct}%**')
        return {'type': 'markdown', 'text': '\n'.join(lines)}

    # ── 通用对话（LLM + 历史上下文） ─────────────────────
    else:
        llm = get_llm_service()
        if llm and llm.enabled:
            try:
                messages = [{'role': 'system', 'content': '你是招聘数据分析平台的智能助手，专注于求职、招聘、职业规划领域。回答简洁，不超过200字。'}]
                # 加入最近5轮历史
                if history:
                    messages.extend(history[-10:])
                messages.append({'role': 'user', 'content': raw_message})

                import requests as _req
                headers = {'Authorization': f'Bearer {llm.api_key}', 'Content-Type': 'application/json'}
                data = {'model': llm.model, 'messages': messages, 'max_tokens': 300}
                r = _req.post(f'{llm.base_url}/chat/completions', headers=headers, json=data, timeout=20)
                if r.status_code == 200:
                    response = r.json()['choices'][0]['message']['content']
                    return {'type': 'markdown', 'text': response}
            except Exception:
                pass
        return {
            'type': 'text',
            'text': '我主要专注于求职和招聘相关的帮助。\n\n你可以问我：**简历优化**、**薪资行情**、**职位推荐**、**爬取数据**，或者直接粘贴职位JD让我帮你分析匹配度。'
        }


def get_llm_service():
    """获取LLM服务（复用llm_service模块）"""
    from .llm_service import get_llm_service as _get
    return _get()


@require_http_methods(["GET"])
def get_notifications(request):
    """获取用户未读职位匹配通知"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    from .models import JobNotification
    notifs_qs = JobNotification.objects.filter(user_id=user_id, is_read=False)
    notifs = list(notifs_qs.select_related('job')[:10])
    data = [{
        'id': n.id,
        'job_id': n.job.job_id,
        'job_name': n.job.name,
        'company': n.job.company,
        'salary': n.job.salary,
        'city': n.job.city,
        'match_score': n.match_score,
        'created_at': n.created_at.strftime('%m-%d %H:%M'),
    } for n in notifs]
    # 标记为已读（用 id 列表，避免切片后 update 报错）
    if notifs:
        JobNotification.objects.filter(id__in=[n.id for n in notifs]).update(is_read=True)
    return JsonResponse({'code': 0, 'count': len(data), 'data': data})
