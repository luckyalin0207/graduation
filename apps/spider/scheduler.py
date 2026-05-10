"""
定时任务调度模块
使用APScheduler实现定时爬虫和邮件提醒
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def start(self):
        """启动调度器"""
        if self.is_running:
            logger.info("调度器已在运行中")
            return
        
        try:
            # 添加定时任务
            self._add_jobs()
            
            # 启动调度器
            self.scheduler.start()
            self.is_running = True
            logger.info("定时任务调度器启动成功")
        except Exception as e:
            logger.error(f"调度器启动失败: {str(e)}")
    
    def stop(self):
        """停止调度器"""
        if not self.is_running:
            return
        
        try:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("定时任务调度器已停止")
        except Exception as e:
            logger.error(f"调度器停止失败: {str(e)}")
    
    def _add_jobs(self):
        """添加定时任务"""
        # 每天凌晨2点执行爬虫任务
        self.scheduler.add_job(
            func=self._run_spider_task,
            trigger=CronTrigger(hour=2, minute=0),
            id='daily_spider',
            name='每日爬虫任务',
            replace_existing=True
        )
        
        # 每天上午9点发送职位推荐邮件
        self.scheduler.add_job(
            func=self._send_job_alerts,
            trigger=CronTrigger(hour=9, minute=0),
            id='daily_job_alert',
            name='每日职位提醒',
            replace_existing=True
        )

        # 每天上午9点半发送高匹配职位提醒
        self.scheduler.add_job(
            func=self._send_high_match_alerts,
            trigger=CronTrigger(hour=9, minute=30),
            id='daily_high_match_alert',
            name='每日高匹配提醒',
            replace_existing=True
        )
        
        # 每天上午8点运行Agent智能推荐
        self.scheduler.add_job(
            func=self._run_agent_recommendations,
            trigger=CronTrigger(hour=8, minute=0),
            id='daily_agent_recommendations',
            name='每日Agent智能推荐',
            replace_existing=True
        )

        # 每天上午8点半检测新职位匹配通知
        self.scheduler.add_job(
            func=self._check_new_job_matches,
            trigger=CronTrigger(hour=8, minute=30),
            id='daily_job_match_notify',
            name='每日职位匹配通知',
            replace_existing=True
        )

        # 每周日晚上11点清理过期数据
        self.scheduler.add_job(
            func=self._cleanup_expired_data,
            trigger=CronTrigger(day_of_week='sun', hour=23, minute=0),
            id='weekly_cleanup',
            name='每周数据清理',
            replace_existing=True
        )

        # 每周日晚上11点半去重
        self.scheduler.add_job(
            func=self._dedup_and_mark_expired,
            trigger=CronTrigger(day_of_week='sun', hour=23, minute=30),
            id='weekly_dedup',
            name='每周职位去重',
            replace_existing=True
        )
        
        # 每周一上午10点训练ML模型
        self.scheduler.add_job(
            func=self._train_models,
            trigger=CronTrigger(day_of_week='mon', hour=10, minute=0),
            id='weekly_train_models',
            name='每周模型训练',
            replace_existing=True
        )

        # 每周一上午9点发送周报
        self.scheduler.add_job(
            func=self._send_weekly_reports,
            trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
            id='weekly_reports',
            name='每周求职报告',
            replace_existing=True
        )
        
        logger.info("已添加6个定时任务")
    
    def _run_spider_task(self):
        """执行每日定时爬虫任务 — 随机选取多样化关键词"""
        logger.info("开始执行定时爬虫任务...")
        try:
            from .models import SpiderInfo
            from .views import run_spider_batch, _get_random_keywords

            spider_info = SpiderInfo.objects.first()
            if spider_info and spider_info.status == 1:
                logger.warning("爬虫正在运行中，跳过定时任务")
                return

            # 随机选 5 个关键词，保证数据多样性
            keywords = _get_random_keywords(5)
            logger.info(f"定时爬虫随机关键词: {keywords}")

            # 在后台线程中运行，避免阻塞调度器
            import threading
            t = threading.Thread(
                target=run_spider_batch,
                args=(keywords, 3, '', 2),  # 每词3页，2个并行
                daemon=True
            )
            t.start()
            logger.info(f"定时爬虫已启动，关键词: {keywords}")

        except Exception as e:
            logger.error(f"定时爬虫任务执行失败: {str(e)}")
    
    def _send_job_alerts(self):
        """发送职位提醒邮件"""
        logger.info("开始发送职位提醒邮件...")
        try:
            from .email_service import send_new_job_alerts
            send_new_job_alerts()
        except Exception as e:
            logger.error(f"发送邮件失败: {str(e)}")

    def _send_high_match_alerts(self):
        """发送高匹配职位提醒"""
        logger.info("开始发送高匹配职位提醒...")
        try:
            from .email_service import send_high_match_alerts
            send_high_match_alerts()
        except Exception as e:
            logger.error(f"发送高匹配提醒失败: {str(e)}")

    def _send_weekly_reports(self):
        """发送每周求职报告"""
        logger.info("开始发送每周求职报告...")
        try:
            from .email_service import send_weekly_reports
            send_weekly_reports()
        except Exception as e:
            logger.error(f"发送周报失败: {str(e)}")
    
    def _run_agent_recommendations(self):
        """运行Agent智能推荐"""
        logger.info("开始运行Agent智能推荐...")
        try:
            from apps.agent.job_search_agent import AgentScheduler
            results = AgentScheduler.run_daily_recommendations()
            success_count = sum(1 for r in results if r.get('status') == 'success')
            logger.info(f"Agent推荐完成，成功为 {success_count} 个用户推荐职位")
        except Exception as e:
            logger.error(f"Agent推荐失败: {str(e)}")
    
    def _check_new_job_matches(self):
        """检测新职位是否匹配用户意向，生成通知"""
        logger.info("开始检测新职位匹配...")
        try:
            from jobs.models import JobData, UserExpectItem
            from agent.models import JobNotification
            from django.utils import timezone
            from datetime import timedelta
            from django.db.models import Q

            # 只检查最近24小时内爬取的职位
            since = timezone.now() - timedelta(hours=24)
            new_jobs = JobData.objects.filter(created_at__gte=since)
            if not new_jobs.exists():
                logger.info("无新职位，跳过匹配检测")
                return

            # 遍历所有有意向的用户
            user_expects = UserExpectItem.objects.values('user_id', 'key_word', 'place', 'salary_min').distinct()
            notify_count = 0
            for expect in user_expects:
                uid = expect['user_id']
                kw = expect.get('key_word', '') or ''
                place = expect.get('place', '') or ''
                salary_min = expect.get('salary_min') or 0

                if not kw:
                    continue

                # 筛选匹配职位
                q = Q()
                for k in kw.split(','):
                    k = k.strip()
                    if k:
                        q |= Q(name__icontains=k) | Q(key_word__icontains=k)
                matched = new_jobs.filter(q)
                if place:
                    matched = matched.filter(city__icontains=place.split(',')[0].strip())
                if salary_min:
                    matched = matched.filter(salary_max__gte=float(salary_min))

                for job in matched[:5]:
                    JobNotification.objects.get_or_create(
                        user_id=uid, job=job,
                        defaults={'match_score': 80}
                    )
                    notify_count += 1

            logger.info(f"职位匹配通知生成完成，共 {notify_count} 条")
        except Exception as e:
            logger.error(f"职位匹配检测失败: {str(e)}")

    def _cleanup_expired_data(self):
        """清理过期数据：30天前的对话历史、已读通知"""
        logger.info("开始清理过期数据...")
        try:
            from django.utils import timezone
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(days=30)

            from agent.models import ChatSession, JobNotification
            deleted_chat = ChatSession.objects.filter(created_at__lt=cutoff).delete()[0]
            deleted_notify = JobNotification.objects.filter(is_read=True, created_at__lt=cutoff).delete()[0]
            logger.info(f"清理完成：对话 {deleted_chat} 条，通知 {deleted_notify} 条")
        except Exception as e:
            logger.error(f"数据清理失败: {str(e)}")

    def _dedup_and_mark_expired(self):
        """去重并标记过期职位（每周执行）"""
        logger.info("开始职位去重...")
        try:
            from jobs.models import JobData
            from django.db.models import Min

            # 找出重复的 (name, company, city) 组合，保留最早的一条
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM jobs_jobdata
                    WHERE job_id NOT IN (
                        SELECT MIN(job_id)
                        FROM jobs_jobdata
                        GROUP BY name, company, city
                    )
                """)
                deleted = cursor.rowcount
            logger.info(f"去重完成，删除重复职位 {deleted} 条")
        except Exception as e:
            logger.error(f"职位去重失败: {str(e)}")

    def _train_models(self):
        """训练机器学习模型"""
        logger.info("开始训练机器学习模型...")
        try:
            # 训练薪资预测模型
            from apps.analysis.ml_predictor import get_predictor
            predictor = get_predictor()
            success, msg = predictor.train()
            logger.info(f"薪资预测模型训练结果: {msg}")
            
            # 构建职位匹配索引
            from apps.analysis.job_matcher import get_matcher
            matcher = get_matcher()
            success, msg = matcher.build_index()
            logger.info(f"职位匹配索引构建结果: {msg}")
        except Exception as e:
            logger.error(f"模型训练失败: {str(e)}")
    
    def get_jobs_info(self):
        """获取所有任务信息"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': str(job.next_run_time) if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs


# 全局调度器实例
_scheduler = None

def get_scheduler():
    """获取调度器单例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler


def start_scheduler():
    """启动调度器（在Django启动时调用）"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_scheduler():
    """停止调度器（在Django关闭时调用）"""
    scheduler = get_scheduler()
    scheduler.stop()
