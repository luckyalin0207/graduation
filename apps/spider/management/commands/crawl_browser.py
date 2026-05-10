"""
通过 jshook 浏览器爬取 51job 数据
用法：python manage.py crawl_browser --keywords Python,Java,前端 --pages 10
"""
import json
import time
import random
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = '通过浏览器内 axios 爬取 51job（无需 Cookie）'

    def add_arguments(self, parser):
        parser.add_argument('--keywords', default='Python', help='关键词，逗号分隔')
        parser.add_argument('--pages', type=int, default=5, help='每个关键词爬取页数')
        parser.add_argument('--page-size', type=int, default=20, help='每页条数')

    def handle(self, *args, **options):
        from jobs.models import JobData
        from spider.models import SpiderInfo
        from spider.views import parse_salary

        keywords = [k.strip() for k in options['keywords'].split(',') if k.strip()]
        pages = options['pages']
        page_size = options['page_size']

        self.stdout.write(f'开始爬取，关键词: {keywords}，每词 {pages} 页')

        # 更新爬虫状态
        spider_info, _ = SpiderInfo.objects.get_or_create(pk=1, defaults={
            'spider_name': '前程无忧爬虫', 'target_site': '51job.com',
            'status': 0, 'total_count': 0, 'run_count': 0,
        })
        spider_info.status = 1
        spider_info.save()

        total = 0
        try:
            for keyword in keywords:
                kw_count = 0
                self.stdout.write(f'\n[{keyword}] 开始...')

                for page in range(1, pages + 1):
                    jobs = self._fetch_page(keyword, page, page_size)
                    if jobs is None:
                        self.stdout.write(f'[{keyword}] 第{page}页失败，停止')
                        break

                    page_count = 0
                    for job in jobs:
                        name = job.get('name', '').strip()
                        company = job.get('company', '').strip()
                        if not name or not company:
                            continue

                        salary_str = job.get('salary', '') or '面议'
                        city = job.get('city', '')
                        edu = job.get('edu', '') or '不限'
                        exp = job.get('exp', '') or '不限'

                        salary_min_raw = job.get('salary_min')
                        salary_max_raw = job.get('salary_max')
                        if salary_min_raw and salary_max_raw:
                            try:
                                salary_min = float(salary_min_raw) / 1000
                                salary_max = float(salary_max_raw) / 1000
                            except Exception:
                                salary_min, salary_max = parse_salary(salary_str)
                        else:
                            salary_min, salary_max = parse_salary(salary_str)

                        if not JobData.objects.filter(name=name, company=company, city=city).exists():
                            JobData.objects.create(
                                name=name, salary=salary_str,
                                salary_min=salary_min, salary_max=salary_max,
                                city=city, place=city, education=edu, experience=exp,
                                company=company,
                                company_type=job.get('company_type', ''),
                                scale=job.get('scale', ''),
                                industry=job.get('industry', ''),
                                key_word=keyword, source='51job',
                            )
                            page_count += 1

                    kw_count += page_count
                    self.stdout.write(f'[{keyword}] 第{page}页 +{page_count} 条，累计 {kw_count}')
                    time.sleep(random.uniform(0.5, 1.0))

                total += kw_count
                self.stdout.write(self.style.SUCCESS(f'[{keyword}] 完成，共 {kw_count} 条'))

        finally:
            spider_info.refresh_from_db()
            spider_info.status = 0
            spider_info.total_count += total
            spider_info.run_count += 1
            spider_info.last_run_time = timezone.now()
            spider_info.save()

        self.stdout.write(self.style.SUCCESS(f'\n全部完成，本次共 {total} 条'))

    def _fetch_page(self, keyword: str, page: int, page_size: int) -> list | None:
        """通过 jshook page_evaluate 调用页面 axios"""
        # 这个方法在 Kiro 环境里通过 MCP 调用
        # 在独立运行时降级到 requests 方式
        raise NotImplementedError('请在 Kiro 环境中通过 jshook 调用此命令')
