"""
Django管理命令：导入Job-SDF数据集
"""
from django.core.management.base import BaseCommand
from analysis.import_job_sdf import run_import


class Command(BaseCommand):
    help = '导入Job-SDF数据集到数据库'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            required=True,
            help='Job-SDF数据集路径（benchmark/dataset目录）'
        )
        parser.add_argument(
            '--granularity',
            type=str,
            default='l2',
            choices=['l1', 'l2', 'company', 'region'],
            help='数据粒度级别（默认: l2）'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='限制导入的技能数量（用于测试，默认: 全部导入）'
        )
    
    def handle(self, *args, **options):
        dataset_path = options['path']
        granularity = options['granularity']
        limit_skills = options['limit']
        
        self.stdout.write(self.style.SUCCESS(
            '=' * 60
        ))
        self.stdout.write(self.style.SUCCESS(
            '开始导入Job-SDF数据集'
        ))
        self.stdout.write(self.style.SUCCESS(
            '=' * 60
        ))
        self.stdout.write(f'数据集路径: {dataset_path}')
        self.stdout.write(f'数据粒度: {granularity}')
        if limit_skills:
            self.stdout.write(f'技能数量限制: {limit_skills}')
        self.stdout.write('')
        
        try:
            run_import(dataset_path, granularity, limit_skills)
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(
                '=' * 60
            ))
            self.stdout.write(self.style.SUCCESS(
                '✅ 数据导入成功！'
            ))
            self.stdout.write(self.style.SUCCESS(
                '=' * 60
            ))
            
            # 显示统计信息
            from analysis.models import HistoricalJobData, SkillMapping, SkillCooccurrence
            
            self.stdout.write('')
            self.stdout.write('数据统计:')
            self.stdout.write(f'  - 技能映射: {SkillMapping.objects.count()} 条')
            self.stdout.write(f'  - 历史数据: {HistoricalJobData.objects.count()} 条')
            self.stdout.write(f'  - 共现关系: {SkillCooccurrence.objects.count()} 条')
            
        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(
                '=' * 60
            ))
            self.stdout.write(self.style.ERROR(
                f'❌ 导入失败: {str(e)}'
            ))
            self.stdout.write(self.style.ERROR(
                '=' * 60
            ))
            
            import traceback
            self.stdout.write(traceback.format_exc())
