"""
邮件服务模块
用于发送职位推荐和提醒邮件
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from jobs.models import JobData, UserExpect, UserExpectItem
from users.models import UserList
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """邮件服务"""
    
    @staticmethod
    def send_job_recommendation(user, jobs):
        """发送职位推荐邮件"""
        if not user.email:
            logger.warning(f"用户 {user.user_name} 没有设置邮箱")
            return False
        
        try:
            subject = f'【招聘分析系统】为您推荐了 {len(jobs)} 个职位'
            
            # 构建邮件内容
            html_content = EmailService._build_job_email_html(user, jobs)
            text_content = EmailService._build_job_email_text(user, jobs)
            
            # 发送邮件
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            logger.info(f"成功发送推荐邮件给用户 {user.user_name}")
            return True
        except Exception as e:
            logger.error(f"发送邮件失败: {str(e)}")
            return False
    
    @staticmethod
    def _build_job_email_html(user, jobs):
        """构建HTML格式的职位推荐邮件"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .job-item {{ border: 1px solid #ddd; margin: 10px; padding: 15px; border-radius: 5px; }}
                .job-title {{ color: #2196F3; font-size: 18px; font-weight: bold; }}
                .job-company {{ color: #666; margin-top: 5px; }}
                .job-salary {{ color: #f44336; font-weight: bold; font-size: 16px; }}
                .job-info {{ color: #999; margin-top: 5px; font-size: 14px; }}
                .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>职位推荐</h1>
                <p>尊敬的 {user.username}，为您推荐以下职位</p>
            </div>
            <div style="padding: 20px;">
        """
        
        for job in jobs[:10]:  # 只发送前10个
            html += f"""
                <div class="job-item">
                    <div class="job-title">{job.name}</div>
                    <div class="job-company">{job.company}</div>
                    <div class="job-salary">薪资: {job.salary}</div>
                    <div class="job-info">
                        地点: {job.city} | 
                        学历: {job.education} | 
                        经验: {job.experience}
                    </div>
                </div>
            """
        
        html += """
            </div>
            <div class="footer">
                <p>此邮件由招聘分析系统自动发送，请勿回复</p>
                <p>如不想再收到此类邮件，请登录系统设置</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    @staticmethod
    def _build_job_email_text(user, jobs):
        """构建纯文本格式的职位推荐邮件"""
        text = f"尊敬的 {user.username}，\n\n"
        text += f"为您推荐以下 {len(jobs)} 个职位：\n\n"
        
        for idx, job in enumerate(jobs[:10], 1):
            text += f"{idx}. {job.name}\n"
            text += f"   公司: {job.company}\n"
            text += f"   薪资: {job.salary}\n"
            text += f"   地点: {job.city} | 学历: {job.education} | 经验: {job.experience}\n\n"
        
        text += "\n此邮件由招聘分析系统自动发送，请勿回复。\n"
        return text

    @staticmethod
    def send_weekly_report(user, report):
        """发送每周求职报告"""
        if not user.email:
            return False
        try:
            subject = '【招聘分析系统】本周求职报告'
            html = EmailService._build_weekly_report_html(user, report)
            text = EmailService._build_weekly_report_text(user, report)
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html, "text/html")
            msg.send()
            return True
        except Exception as e:
            logger.error(f"发送周报失败: {str(e)}")
            return False

    @staticmethod
    def _build_weekly_report_html(user, report):
        profile = report.get('profile', {})
        market = report.get('market_analysis', {})
        salary = report.get('salary_prediction', {})
        recs = report.get('recommendations', [])
        html = f"""
        <html><body>
        <h2>本周求职报告</h2>
        <p>尊敬的 {user.user_name}，以下是您的本周报告：</p>
        <h3>个人画像</h3>
        <ul>
            <li>技能：{', '.join(profile.get('skills', [])) or '未设置'}</li>
            <li>目标城市：{', '.join(profile.get('target_cities', [])) or '未设置'}</li>
            <li>期望薪资：{profile.get('salary_range', ['-', '-'])[0]}K - {profile.get('salary_range', ['-', '-'])[1]}K</li>
            <li>已投递职位：{profile.get('applied_jobs', 0)} 个</li>
        </ul>
        <h3>薪资预测</h3>
        <p>预测薪资：{salary.get('predicted', '-') }K；合理范围：{salary.get('lower', '-') }K - {salary.get('upper', '-') }K</p>
        <h3>市场分析</h3>
        <ul>
            <li>相关职位数：{market.get('total_jobs', 0)}</li>
            <li>平均薪资：{market.get('avg_salary', '-') }K</li>
            <li>热门城市：{', '.join(market.get('top_cities', [])) or '暂无'}</li>
        </ul>
        <h3>推荐职位（Top 5）</h3>
        <ul>
        """
        for item in recs[:5]:
            html += f"<li>{item.get('name', '')} - {item.get('company', '')}（{item.get('match_score', 0)}分）</li>"
        html += """
        </ul>
        <p style="color:#999">此邮件由系统自动发送，请勿回复。</p>
        </body></html>
        """
        return html

    @staticmethod
    def _build_weekly_report_text(user, report):
        profile = report.get('profile', {})
        market = report.get('market_analysis', {})
        salary = report.get('salary_prediction', {})
        recs = report.get('recommendations', [])
        text = f"本周求职报告 - {user.user_name}\n\n"
        text += f"技能：{', '.join(profile.get('skills', [])) or '未设置'}\n"
        text += f"目标城市：{', '.join(profile.get('target_cities', [])) or '未设置'}\n"
        text += f"期望薪资：{profile.get('salary_range', ['-', '-'])[0]}K - {profile.get('salary_range', ['-', '-'])[1]}K\n"
        text += f"预测薪资：{salary.get('predicted', '-') }K\n"
        text += f"市场职位数：{market.get('total_jobs', 0)}\n\n"
        text += "推荐职位：\n"
        for item in recs[:5]:
            text += f"- {item.get('name', '')} - {item.get('company', '')}（{item.get('match_score', 0)}分）\n"
        return text


def send_new_job_alerts():
    """发送新职位提醒（定时任务调用）"""
    logger.info("开始检查并发送新职位提醒...")
    
    # 检查邮件配置
    if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
        logger.warning("邮件服务未配置，跳过发送")
        return
    
    try:
        # 获取最近24小时内新增的职位
        yesterday = datetime.now() - timedelta(days=1)
        new_jobs = JobData.objects.filter(created_at__gte=yesterday)
        
        if not new_jobs or (hasattr(new_jobs, 'count') and new_jobs.count() == 0):
            logger.info("没有新职位，跳过发送")
            return
        
        # 获取所有有求职意向的用户
        user_ids = UserExpectItem.objects.values_list('user_id', flat=True).distinct()
        if not user_ids:
            user_ids = UserExpect.objects.values_list('user_id', flat=True).distinct()

        sent_count = 0
        for user_id in user_ids:
            try:
                user = UserList.objects.get(user_id=user_id)
                
                # 根据用户多条意向筛选职位
                matched_jobs = JobData.objects.none()
                expect_items = UserExpectItem.objects.filter(user_id=user_id)
                if not expect_items.exists():
                    legacy = UserExpect.objects.filter(user_id=user_id).first()
                    expect_items = [legacy] if legacy else []

                from django.db.models import Q
                for expect in expect_items:
                    if not expect:
                        continue
                    q = Q()
                    if expect.key_word:
                        q &= Q(name__icontains=expect.key_word) | Q(key_word__icontains=expect.key_word)
                    if expect.place:
                        q &= Q(city__icontains=expect.place) | Q(place__icontains=expect.place)
                    if expect.salary_min:
                        q &= Q(salary_max__gte=expect.salary_min)
                    if q:
                        matched_jobs = matched_jobs | new_jobs.filter(q)

                matched_jobs = list(matched_jobs.distinct()[:20])
                
                # 如果有匹配的职位，发送邮件
                if matched_jobs:
                    if EmailService.send_job_recommendation(user, matched_jobs):
                        sent_count += 1
            
            except UserList.DoesNotExist:
                logger.warning(f"用户 {user_id} 不存在")
                continue
            except Exception as e:
                logger.error(f"处理用户 {expect.user_id} 时出错: {str(e)}")
                continue
        
        logger.info(f"成功发送 {sent_count} 封职位提醒邮件")
    
    except Exception as e:
        logger.error(f"发送新职位提醒失败: {str(e)}")


def send_high_match_alerts(min_score=80, limit=5):
    """发送高匹配职位提醒（基于Agent推荐）"""
    logger.info("开始发送高匹配职位提醒...")
    if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
        logger.warning("邮件服务未配置，跳过发送")
        return
    try:
        from apps.agent.job_search_agent import get_agent
        users = UserList.objects.exclude(email__isnull=True).exclude(email='')
        sent_count = 0
        for user in users:
            try:
                agent = get_agent(user.user_id)
                recs = agent.recommend_jobs(limit=limit, min_score=min_score)
                jobs = [item['job'] for item in recs]
                if jobs:
                    if EmailService.send_job_recommendation(user, jobs):
                        sent_count += 1
            except Exception as e:
                logger.warning(f"用户 {user.user_id} 发送高匹配提醒失败: {str(e)}")
        logger.info(f"高匹配提醒发送完成，共 {sent_count} 封")
    except Exception as e:
        logger.error(f"高匹配提醒失败: {str(e)}")


def send_weekly_reports():
    """发送每周求职报告"""
    logger.info("开始发送每周求职报告...")
    if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
        logger.warning("邮件服务未配置，跳过发送")
        return
    try:
        from apps.agent.job_search_agent import get_agent
        users = UserList.objects.exclude(email__isnull=True).exclude(email='')
        sent_count = 0
        for user in users:
            try:
                agent = get_agent(user.user_id)
                report = agent.generate_report()
                if EmailService.send_weekly_report(user, report):
                    sent_count += 1
            except Exception as e:
                logger.warning(f"用户 {user.user_id} 发送周报失败: {str(e)}")
        logger.info(f"周报发送完成，共 {sent_count} 封")
    except Exception as e:
        logger.error(f"发送周报失败: {str(e)}")

