"""
[LEGACY] Django 管理命令:导入 Job-SDF 数据集。

本项目已切换到拉勾网招聘数据集,请改用:
    python manage.py import_lagou

本命令仅为兼容旧仓库而保留,默认直接报错并给出迁移提示。
如仍需使用 Job-SDF,请加 --force 参数。
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = '[LEGACY] 旧的 Job-SDF 导入命令,已被 import_lagou 取代'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, default='')
        parser.add_argument('--granularity', type=str, default='l2',
                            choices=['l1', 'l2', 'company', 'region'])
        parser.add_argument('--limit', type=int, default=None)
        parser.add_argument('--force', action='store_true',
                            help='强制执行旧的 Job-SDF 导入(不推荐)')

    def handle(self, *args, **options):
        if not options.get('force'):
            raise CommandError(
                '本项目已切换到拉勾网招聘数据集,请改用:\n'
                '    python manage.py import_lagou --with-trend --with-cooc\n\n'
                '如仍需使用 Job-SDF,请加 --force 参数。'
            )
        try:
            from analysis.import_job_sdf import run_import
        except Exception as exc:
            raise CommandError(f'Job-SDF 旧逻辑已迁移,加载失败: {exc}')
        run_import(options['path'], options['granularity'], options['limit'])
