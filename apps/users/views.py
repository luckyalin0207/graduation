from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import UserList
import os


def login(request):
    """用户登录"""
    if request.method == "POST":
        user_id = request.POST.get('user')
        password = request.POST.get('password')
        
        if not user_id or not password:
            return JsonResponse({'code': 1, 'msg': '请输入账号和密码！'})
        
        try:
            user = UserList.objects.get(user_id=user_id)
            if user.check_password(password):
                request.session['user_id'] = user_id
                request.session['user_name'] = user.user_name
                return JsonResponse({'code': 0, 'msg': '登录成功！'})
            return JsonResponse({'code': 1, 'msg': '密码错误！'})
        except UserList.DoesNotExist:
            return JsonResponse({'code': 1, 'msg': '账号不存在！'})
    
    return render(request, "users/login.html")


def register(request):
    """用户注册"""
    if request.method == "POST":
        user_id = request.POST.get('user')
        user_name = request.POST.get('user_name')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if not all([user_id, user_name, password, password2]):
            return JsonResponse({'code': 1, 'msg': '请填写完整信息！'})
        
        if password != password2:
            return JsonResponse({'code': 1, 'msg': '两次密码不一致！'})
        
        if UserList.objects.filter(user_id=user_id).exists():
            return JsonResponse({'code': 1, 'msg': '账号已存在！'})
        
        user = UserList(user_id=user_id, user_name=user_name)
        user.set_password(password)
        user.save()
        
        request.session['user_id'] = user_id
        request.session['user_name'] = user_name
        return JsonResponse({'code': 0, 'msg': '注册成功！'})
    
    return render(request, "users/register.html")


def logout(request):
    """用户登出"""
    request.session.flush()
    return redirect('login')


def user_info(request):
    """用户个人信息"""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    try:
        user = UserList.objects.get(user_id=user_id)
    except UserList.DoesNotExist:
        return redirect('login')
    
    if request.method == "POST":
        user_name = request.POST.get('user_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        
        if user_name:
            user.user_name = user_name
            request.session['user_name'] = user_name
        if email:
            user.email = email
        if phone:
            user.phone = phone
        user.save()
        return JsonResponse({'code': 0, 'msg': '更新成功！'})
    
    return render(request, "users/user_info.html", {'user': user})


def upload_resume(request):
    """上传并解析简历"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    if request.method != 'POST':
        return JsonResponse({'code': 1, 'msg': '请使用POST方法'})
    
    if 'resume' not in request.FILES:
        return JsonResponse({'code': 1, 'msg': '请选择简历文件'})
    
    resume_file = request.FILES['resume']
    filename = resume_file.name
    
    if not filename.lower().endswith(('.pdf', '.docx', '.doc')):
        return JsonResponse({'code': 1, 'msg': '只支持PDF和Word格式的简历'})
    
    if resume_file.size > 5 * 1024 * 1024:
        return JsonResponse({'code': 1, 'msg': '文件大小不能超过5MB'})
    
    from .resume_parser import ResumeParser
    result = ResumeParser.parse_resume(resume_file, filename)
    
    if not result['success']:
        return JsonResponse({'code': 1, 'msg': result.get('error', '解析失败')})
    
    try:
        from django.utils import timezone
        user = UserList.objects.get(user_id=user_id)
        
        # ── 1. 更新用户基本信息 ──────────────────────────────
        if result.get('name'):
            user.user_name = result['name']
            request.session['user_name'] = result['name']
        if result.get('email'):
            user.email = result['email']
        if result.get('phone'):
            user.phone = result['phone']
        
        # ── 2. 保存简历文件 ──────────────────────────────────
        # 先删旧文件
        if user.resume_file:
            try:
                user.resume_file.delete(save=False)
            except Exception:
                pass
        # 重置文件指针后保存
        resume_file.seek(0)
        user.resume_file = resume_file
        user.resume_name = filename
        user.resume_updated_at = timezone.now()
        user.save()
        
        # ── 3. 保存工作经历 ──────────────────────────────────
        from .models import UserWorkExperience, UserEducation
        UserWorkExperience.objects.filter(user_id=user_id).delete()
        for w in result.get('work_experience', []):
            if w.get('company') or w.get('title'):
                UserWorkExperience.objects.create(
                    user_id=user_id,
                    company=w.get('company', ''),
                    title=w.get('title', ''),
                    start_date=w.get('start', ''),
                    end_date=w.get('end', ''),
                    description=w.get('description', '')[:500],
                )
        
        # ── 4. 保存教育经历 ──────────────────────────────────
        UserEducation.objects.filter(user_id=user_id).delete()
        for e in result.get('education_list', []):
            if e.get('school') or e.get('degree'):
                UserEducation.objects.create(
                    user_id=user_id,
                    school=e.get('school', ''),
                    degree=e.get('degree', ''),
                    major=e.get('major', ''),
                    start_date=e.get('start', ''),
                    end_date=e.get('end', ''),
                )
        
        # ── 5. 填充求职意向（仅在没有意向时）────────────────
        from jobs.models import UserExpect, UserExpectItem
        expect, _ = UserExpect.objects.get_or_create(user_id=user_id)
        if result.get('skills') and not expect.key_word:
            expect.key_word = ', '.join(result['skills'][:5])
        exp_years = result.get('experience_years')
        if exp_years is not None and not expect.salary_min:
            if exp_years == 0:
                expect.salary_min, expect.salary_max = 3, 8
            elif exp_years <= 3:
                expect.salary_min, expect.salary_max = 8, 15
            elif exp_years <= 5:
                expect.salary_min, expect.salary_max = 15, 25
            else:
                expect.salary_min, expect.salary_max = 25, 50
        expect.save()
        
        auto_filled = False
        if not UserExpectItem.objects.filter(user_id=user_id).exists():
            item = UserExpectItem(
                user_id=user_id,
                key_word=', '.join(result['skills'][:5]) if result.get('skills') else '',
            )
            if exp_years is not None:
                if exp_years == 0:
                    item.salary_min, item.salary_max = 3, 8
                elif exp_years <= 3:
                    item.salary_min, item.salary_max = 8, 15
                elif exp_years <= 5:
                    item.salary_min, item.salary_max = 15, 25
                else:
                    item.salary_min, item.salary_max = 25, 50
            item.save()
            auto_filled = True
        
        return JsonResponse({
            'code': 0,
            'msg': '简历解析成功' + ('，已自动填充求职意向' if auto_filled else ''),
            'data': {
                'name': result.get('name'),
                'email': result.get('email'),
                'phone': result.get('phone'),
                'education': result.get('education'),
                'experience_years': result.get('experience_years'),
                'skills': result.get('skills', []),
                'work_experience': result.get('work_experience', []),
                'education_list': result.get('education_list', []),
                'projects': result.get('projects', []),
                'summary': result.get('summary', ''),
                'auto_filled': auto_filled,
                'resume_saved': True,
                'work_count': len(result.get('work_experience', [])),
                'edu_count': len(result.get('education_list', [])),
            }
        })
    
    except Exception as e:
        return JsonResponse({'code': 1, 'msg': f'处理失败: {str(e)}'})


def get_resume_info(request):
    """获取用户已保存的简历信息"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})
    
    from .models import UserWorkExperience, UserEducation
    
    user = UserList.objects.get(user_id=user_id)
    work_list = list(UserWorkExperience.objects.filter(user_id=user_id).values(
        'company', 'title', 'start_date', 'end_date', 'description'
    ))
    edu_list = list(UserEducation.objects.filter(user_id=user_id).values(
        'school', 'degree', 'major', 'start_date', 'end_date'
    ))
    
    return JsonResponse({
        'code': 0,
        'data': {
            'resume_name': user.resume_name,
            'resume_updated_at': user.resume_updated_at.strftime('%Y-%m-%d %H:%M') if user.resume_updated_at else None,
            'work_experience': work_list,
            'education_list': edu_list,
        }
    })


def resume_match_jobs(request):
    """简历匹配职位 — 用简历技能/学历/经验匹配最合适的职位"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})

    from .models import UserEducation
    from jobs.models import UserExpectItem
    from apps.analysis.job_matcher import get_matcher

    expect = UserExpectItem.objects.filter(user_id=user_id).first()
    skills = expect.key_word if expect and expect.key_word else ''
    city = expect.place if expect and expect.place else ''
    salary_min = float(expect.salary_min) if expect and expect.salary_min else 0
    edu = UserEducation.objects.filter(user_id=user_id).first()
    education = edu.degree if edu else ''

    # 没有技能关键词时提示先上传简历
    if not skills:
        return JsonResponse({'code': 1, 'msg': '请先上传简历或设置求职意向，系统才能为你匹配职位'})

    matcher = get_matcher()
    jobs = matcher.match_jobs(
        skills=skills, city=city,
        salary_min=salary_min, education=education,
        top_k=int(request.GET.get('limit', 10))
    )

    if not jobs:
        return JsonResponse({'code': 1, 'msg': '暂无匹配职位，请先爬取更多数据'})

    return JsonResponse({'code': 0, 'data': jobs, 'skills': skills})


def resume_score(request):
    """简历评分 — 对比职位要求给简历打分"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})

    from .models import UserWorkExperience, UserEducation
    from jobs.models import UserExpectItem, JobData
    from django.db.models import Avg

    # 用户画像
    expect = UserExpectItem.objects.filter(user_id=user_id).first()
    skills_str = expect.key_word if expect and expect.key_word else ''
    user_skills = set(s.strip().lower() for s in skills_str.split(',') if s.strip())
    user_edu = UserEducation.objects.filter(user_id=user_id).first()
    user_degree = user_edu.degree if user_edu else ''
    work_count = UserWorkExperience.objects.filter(user_id=user_id).count()

    # 目标职位（用技能关键词搜索）
    if skills_str:
        from django.db.models import Q
        kw = skills_str.split(',')[0].strip()
        target_jobs = JobData.objects.filter(
            Q(name__icontains=kw) | Q(key_word__icontains=kw)
        )[:200]
    else:
        target_jobs = JobData.objects.all()[:200]

    if not target_jobs:
        return JsonResponse({'code': 1, 'msg': '暂无可对比的职位数据'})

    # 统计市场要求
    edu_counter = {}
    exp_counter = {}
    skill_counter = {}
    from apps.users.resume_parser import TECH_SKILLS
    for job in target_jobs:
        if job.education:
            edu_counter[job.education] = edu_counter.get(job.education, 0) + 1
        if job.experience:
            exp_counter[job.experience] = exp_counter.get(job.experience, 0) + 1
        for sk in TECH_SKILLS:
            if job.name and sk.lower() in job.name.lower():
                skill_counter[sk] = skill_counter.get(sk, 0) + 1
            if job.key_word and sk.lower() in job.key_word.lower():
                skill_counter[sk] = skill_counter.get(sk, 0) + 1

    total = len(target_jobs)
    # 最常见的市场技能 top10
    top_market_skills = sorted(skill_counter.items(), key=lambda x: -x[1])[:10]
    market_skill_names = set(s[0].lower() for s in top_market_skills)
    # 用于前端展示的原始大小写版本
    top_market_skills_display = [s[0] for s in top_market_skills]

    # 评分维度
    scores = {}
    suggestions = []

    # 1. 技能匹配（40分）
    if market_skill_names:
        matched = user_skills & market_skill_names
        skill_score = int(len(matched) / len(market_skill_names) * 40)
        scores['技能匹配'] = {'score': skill_score, 'max': 40,
                              'detail': f'匹配 {len(matched)}/{len(market_skill_names)} 个市场热门技能'}
        missing = market_skill_names - user_skills
        if missing:
            suggestions.append(f'建议补充技能：{", ".join(list(missing)[:3])}')
    else:
        scores['技能匹配'] = {'score': 20, 'max': 40, 'detail': '暂无技能数据'}

    # 2. 学历匹配（25分）
    edu_order = {'博士': 5, '硕士': 4, '本科': 3, '大专': 2, '专科': 2, '高中': 1}
    # 市场最常见学历要求
    top_edu = max(edu_counter, key=edu_counter.get) if edu_counter else '本科'
    user_edu_level = edu_order.get(user_degree, 0)
    market_edu_level = edu_order.get(top_edu, 3)
    if user_edu_level >= market_edu_level:
        edu_score = 25
    elif user_edu_level == market_edu_level - 1:
        edu_score = 18
        suggestions.append(f'市场主流要求{top_edu}，你的学历略低，可考虑提升学历或突出技能')
    else:
        edu_score = 10
        suggestions.append(f'市场主流要求{top_edu}，建议在技能和经验上多下功夫')
    scores['学历匹配'] = {'score': edu_score, 'max': 25, 'detail': f'市场主流要求：{top_edu}，你的学历：{user_degree or "未填写"}'}

    # 3. 工作经历（20分）
    if work_count >= 3:
        exp_score = 20
    elif work_count == 2:
        exp_score = 15
    elif work_count == 1:
        exp_score = 10
        suggestions.append('工作经历较少，建议补充实习/项目经历')
    else:
        exp_score = 5
        suggestions.append('未检测到工作经历，建议上传包含工作经历的简历')
    scores['工作经历'] = {'score': exp_score, 'max': 20, 'detail': f'检测到 {work_count} 段工作经历'}

    # 4. 简历完整度（15分）
    user = UserList.objects.get(user_id=user_id)
    completeness = sum([
        bool(user.user_name), bool(user.email), bool(user.phone),
        bool(user.resume_file), bool(user_degree), bool(skills_str)
    ])
    complete_score = int(completeness / 6 * 15)
    scores['简历完整度'] = {'score': complete_score, 'max': 15,
                            'detail': f'已填写 {completeness}/6 项基本信息'}
    if not user.email:
        suggestions.append('建议填写邮箱，方便HR联系')
    if not skills_str:
        suggestions.append('建议上传简历或手动填写技能关键词')

    total_score = sum(v['score'] for v in scores.values())
    level = '优秀' if total_score >= 80 else '良好' if total_score >= 60 else '待提升'

    return JsonResponse({
        'code': 0,
        'data': {
            'total_score': total_score,
            'level': level,
            'scores': scores,
            'suggestions': suggestions,
            'top_market_skills': top_market_skills_display,
            'user_skills': list(user_skills),
        }
    })


def resume_download(request):
    """下载已保存的简历文件"""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})

    user = UserList.objects.get(user_id=user_id)
    if not user.resume_file:
        return JsonResponse({'code': 1, 'msg': '未上传简历，请先上传'})

    from django.http import FileResponse
    import mimetypes
    try:
        file_path = user.resume_file.path
    except Exception:
        return JsonResponse({'code': 1, 'msg': '文件路径异常'})

    if not os.path.exists(file_path):
        return JsonResponse({'code': 1, 'msg': '文件已丢失，请重新上传'})

    mime, _ = mimetypes.guess_type(file_path)
    response = FileResponse(open(file_path, 'rb'), content_type=mime or 'application/octet-stream')
    fname = user.resume_name or 'resume'
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    return response


def reset_password(request):
    """密码重置 — 通过账号+手机号验证身份后重置"""
    if request.method == 'GET':
        return render(request, 'users/reset_password.html')

    user_id = request.POST.get('user_id', '').strip()
    phone = request.POST.get('phone', '').strip()
    new_password = request.POST.get('new_password', '')
    confirm_password = request.POST.get('confirm_password', '')

    if not all([user_id, phone, new_password, confirm_password]):
        return JsonResponse({'code': 1, 'msg': '请填写完整信息'})
    if new_password != confirm_password:
        return JsonResponse({'code': 1, 'msg': '两次密码不一致'})
    if len(new_password) < 6:
        return JsonResponse({'code': 1, 'msg': '密码长度至少6位'})

    try:
        user = UserList.objects.get(user_id=user_id)
    except UserList.DoesNotExist:
        return JsonResponse({'code': 1, 'msg': '账号不存在'})

    if not user.phone:
        return JsonResponse({'code': 1, 'msg': '该账号未绑定手机号，无法重置密码'})
    if user.phone != phone:
        return JsonResponse({'code': 1, 'msg': '手机号验证失败'})

    user.set_password(new_password)
    user.save()
    return JsonResponse({'code': 0, 'msg': '密码重置成功，请重新登录'})


def get_resume_summary(request):
    """
    获取当前用户的简历摘要，用于投递确认弹窗展示。
    返回：姓名、联系方式、学历、技能关键词、工作经历条数、简历文件名
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'code': 1, 'msg': '请先登录'})

    try:
        user = UserList.objects.get(user_id=user_id)
    except UserList.DoesNotExist:
        return JsonResponse({'code': 1, 'msg': '用户不存在'})

    from .models import UserWorkExperience, UserEducation
    from jobs.models import UserExpectItem

    work_count = UserWorkExperience.objects.filter(user_id=user_id).count()
    edu = UserEducation.objects.filter(user_id=user_id).first()
    expect = UserExpectItem.objects.filter(user_id=user_id).first()

    return JsonResponse({'code': 0, 'data': {
        'user_name': user.user_name,
        'email': user.email or '',
        'phone': user.phone or '',
        'degree': edu.degree if edu else '',
        'school': edu.school if edu else '',
        'skills': expect.key_word if expect else '',
        'work_count': work_count,
        'resume_name': user.resume_name or '',
        'has_resume': bool(user.resume_file),
    }})
