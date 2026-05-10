"""
python manage.py fix_job_hrefs

给现有无链接的职位数据补全跳转链接：
- 51job  → 用职位名称构建 51job 搜索链接
- BOSS直聘 → 用职位名称构建 BOSS直聘 搜索链接
- 其他来源 → 用职位名称构建通用搜索链接

这是一次性补全操作，后续新爬取的数据会直接保存精确链接。
"""
from urllib.parse import quote
from django.core.management.base import BaseCommand
from django.db.models import Q


class Command(BaseCommand):
    help = '批量补全职位原始链接（搜索链接）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-no-href',
            action='store_true',
            help='删除无链接数据而不是补全（谨慎使用）',
        )
        parser.add_argument(
            '--source',
            default='',
            help='只处理指定来源，如 51job 或 BOSS直聘，默认处理全部',
        )

    def handle(self, *args, **options):
        from jobs.models import JobData

        qs = JobData.objects.filter(Q(href='') | Q(href__isnull=True))
        if options['source']:
            qs = qs.filter(source__icontains=options['source'])

        total = qs.count()
        self.stdout.write(f'找到 {total} 条无链接职位')

        if total == 0:
            self.stdout.write(self.style.SUCCESS('无需处理'))
            return

        # ── 删除模式 ──────────────────────────────────────────
        if options['delete_no_href']:
            confirm = input(f'确认删除 {total} 条无链接职位？(yes/no): ')
            if confirm.strip().lower() != 'yes':
                self.stdout.write('已取消')
                return
            deleted, _ = qs.delete()
            self.stdout.write(self.style.SUCCESS(f'已删除 {deleted} 条'))
            return

        # ── 补全模式 ──────────────────────────────────────────
        batch = []
        done = 0

        for job in qs.iterator(chunk_size=500):
            name_enc = quote(job.name or '', safe='')
            company_enc = quote(job.company or '', safe='')
            src = (job.source or '').lower()

            if '51job' in src or '前程' in src:
                # 51job 搜索：职位名 + 公司名
                job.href = (
                    f'https://we.51job.com/pc/search?keyword={name_enc}'
                    f'&searchType=2&sortType=0'
                )
            elif 'boss' in src or '直聘' in src:
                # BOSS直聘 搜索
                job.href = (
                    f'https://www.zhipin.com/web/geek/job?query={name_enc}'
                    f'&city=100010000'
                )
            else:
                # 通用：BOSS直聘 搜索
                job.href = (
                    f'https://www.zhipin.com/web/geek/job?query={name_enc}'
                    f'&city=100010000'
                )

            batch.append(job)
            done += 1

            # 每 500 条批量写入
            if len(batch) >= 500:
                JobData.objects.bulk_update(batch, ['href'])
                batch.clear()
                self.stdout.write(f'  已处理 {done}/{total}...')

        # 写入剩余
        if batch:
            JobData.objects.bulk_update(batch, ['href'])

        self.stdout.write(self.style.SUCCESS(f'完成！共补全 {done} 条职位链接'))
        self.stdout.write('注意：这些是搜索链接，不是精确职位页。重新爬取后会自动覆盖为精确链接。')
