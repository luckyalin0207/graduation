"""
Django 管理命令:导入拉勾网招聘数据集

数据来源: https://github.com/weizhuang1113/Lagou_Spider_And_Data_Analysis
默认文件: data/Lagou_Data.csv (GB18030 编码)

用法:
    python manage.py import_lagou                      # 默认导入 data/Lagou_Data.csv
    python manage.py import_lagou --path 路径          # 指定其它 CSV
    python manage.py import_lagou --limit 500          # 限量导入(快速测试)
    python manage.py import_lagou --with-trend         # 同时写历史时间序列表
    python manage.py import_lagou --flush              # 导入前清空旧数据
"""
from __future__ import annotations

import ast
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, date
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone


# ─────────── 字段清洗辅助 ───────────

def _clean_labels(raw) -> list[str]:
    """把 '{Python,Django,SQL}' 或 'Python,Django' 这类字段转成 ['Python','Django','SQL']"""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    s = str(raw).strip()
    if not s or s in ('{}', '[]', 'nan'):
        return []
    # 尝试用 ast 解析 {a,b,c} 或 [a,b,c]
    try:
        fixed = s.replace('{', '[').replace('}', ']')
        val = ast.literal_eval(fixed)
        if isinstance(val, (list, tuple, set)):
            return [str(x).strip() for x in val if str(x).strip()]
    except (ValueError, SyntaxError):
        pass
    # 兜底:直接按分隔符切分
    cleaned = re.sub(r'[{}\[\]\'"]', '', s)
    return [p.strip() for p in re.split(r'[，,;；/、]', cleaned) if p.strip()]


def _safe_date(raw):
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    try:
        dt = pd.to_datetime(raw, errors='coerce')
        if pd.isna(dt):
            return None
        # Django USE_TZ=True,需要 aware datetime
        return timezone.make_aware(dt.to_pydatetime()) if timezone.is_naive(dt.to_pydatetime()) else dt.to_pydatetime()
    except Exception:
        return None


def _safe_num(raw):
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    try:
        val = float(raw)
        if pd.isna(val):
            return None
        return round(val, 2)
    except (TypeError, ValueError):
        return None


def _first_non_empty(*values) -> str:
    for v in values:
        if v is None:
            continue
        if isinstance(v, float) and pd.isna(v):
            continue
        s = str(v).strip()
        if s and s.lower() != 'nan':
            return s
    return ''


def _normalize_key_word(first_type, second_type, position_name) -> str:
    """合并 firstType / secondType / positionName 的关键信息,作为统一关键词"""
    second = _first_non_empty(second_type)
    if second:
        return second
    first = _first_non_empty(first_type)
    if first:
        return first
    name = _first_non_empty(position_name)
    return name[:50]


# ─────────── Command ───────────

class Command(BaseCommand):
    help = '导入拉勾网招聘数据集(Lagou_Data.csv)到 JobData / HistoricalJobData / SkillCooccurrence'

    DEFAULT_PATH = 'data/Lagou_Data.csv'

    def add_arguments(self, parser):
        parser.add_argument('--path', default=self.DEFAULT_PATH,
                            help=f'CSV 文件路径,默认 {self.DEFAULT_PATH}')
        parser.add_argument('--encoding', default='gb18030',
                            help='CSV 编码,默认 gb18030')
        parser.add_argument('--limit', type=int, default=None,
                            help='仅导入前 N 条(快速测试用)')
        parser.add_argument('--flush', action='store_true',
                            help='导入前清空旧数据(JobData source=拉勾网 / HistoricalJobData source=Lagou / SkillCooccurrence)')
        parser.add_argument('--with-trend', action='store_true',
                            help='同时写入 HistoricalJobData(按日期聚合,供趋势分析使用)')
        parser.add_argument('--with-cooc', action='store_true',
                            help='同时写入 SkillCooccurrence(技能共现表,供技能推荐使用)')

    # ---- 核心逻辑 ----

    def handle(self, *args, **options):
        csv_path = Path(options['path'])
        if not csv_path.is_absolute():
            csv_path = Path(settings.BASE_DIR) / csv_path

        if not csv_path.exists():
            raise CommandError(f'找不到数据文件: {csv_path}')

        self.stdout.write(self.style.MIGRATE_HEADING(f'读取 {csv_path}'))
        df = pd.read_csv(csv_path, encoding=options['encoding'])

        if options['limit']:
            df = df.head(options['limit'])

        self.stdout.write(f'  总记录数: {len(df)}')
        self.stdout.write(f'  列: {", ".join(df.columns)}')

        # 惰性导入,避免 Django app 还没 ready
        from jobs.models import JobData
        from analysis.models import HistoricalJobData, SkillCooccurrence, SkillMapping

        if options['flush']:
            self._flush(JobData, HistoricalJobData, SkillCooccurrence, SkillMapping)

        # 1) 写 JobData
        jobdata_count = self._import_jobdata(df, JobData)

        # 2) 写 HistoricalJobData(时间序列)
        hist_count = 0
        if options['with_trend']:
            hist_count = self._import_trend(df, HistoricalJobData)

        # 3) 写 SkillCooccurrence(技能共现)
        cooc_count = 0
        if options['with_cooc']:
            cooc_count = self._import_cooc(df, SkillCooccurrence, SkillMapping)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ 导入完成'))
        self.stdout.write(f'   JobData                 新增 {jobdata_count} 条')
        if options['with_trend']:
            self.stdout.write(f'   HistoricalJobData       新增 {hist_count} 条')
        if options['with_cooc']:
            self.stdout.write(f'   SkillCooccurrence       新增 {cooc_count} 条')

    # ---- 各步骤 ----

    def _flush(self, JobData, HistoricalJobData, SkillCooccurrence, SkillMapping):
        self.stdout.write(self.style.WARNING('清空旧数据...'))
        JobData.objects.filter(source='拉勾网').delete()
        HistoricalJobData.objects.filter(data_source='Lagou').delete()
        SkillCooccurrence.objects.all().delete()
        SkillMapping.objects.filter(is_manual=False).delete()

    def _import_jobdata(self, df: pd.DataFrame, JobData) -> int:
        self.stdout.write(self.style.MIGRATE_HEADING('[1/3] 写入 JobData'))

        # 预取已存在的 (name, company, city) 三元组用于去重
        existing = set(
            JobData.objects.filter(source='拉勾网')
            .values_list('name', 'company', 'city')
        )

        to_create = []
        skipped = 0
        for _, row in df.iterrows():
            name = _first_non_empty(row.get('positionName'))
            company = _first_non_empty(row.get('companyFullName'), row.get('companyShortName'))
            city = _first_non_empty(row.get('city'))
            if not name:
                skipped += 1
                continue
            key = (name, company, city)
            if key in existing:
                skipped += 1
                continue
            existing.add(key)

            labels = _clean_labels(row.get('positionLables'))
            label_text = ','.join(labels) if labels else ''

            to_create.append(JobData(
                name=name[:255],
                salary=_first_non_empty(row.get('salary'))[:100] or None,
                salary_min=_safe_num(row.get('bottomSalary')),
                salary_max=_safe_num(row.get('topSalary')),
                place=_first_non_empty(row.get('city'), row.get('district'))[:100] or None,
                city=city[:50] or None,
                education=_first_non_empty(row.get('education'))[:50] or None,
                experience=_first_non_empty(row.get('workYear'))[:100] or None,
                company=company[:255] or None,
                company_type=_first_non_empty(row.get('financeStage'))[:100] or None,
                scale=_first_non_empty(row.get('companySize'))[:100] or None,
                industry=_first_non_empty(row.get('industryField'))[:100] or None,
                label=label_text[:500] or None,
                description=_first_non_empty(row.get('content'))[:4000] or None,
                href=None,
                key_word=_normalize_key_word(
                    row.get('firstType'), row.get('secondType'), row.get('positionName')
                )[:100],
                source='拉勾网',
            ))

        created = 0
        if to_create:
            with transaction.atomic():
                created_objs = JobData.objects.bulk_create(to_create, batch_size=500)
                created = len(created_objs)

        # 对于拉勾数据,把 createTime 回填到 created_at(bulk_create 后再 update)
        # 分批,否则逐行 save 会很慢
        self._backfill_created_at(df, JobData)

        self.stdout.write(f'  新增 {created},跳过 {skipped}')
        return created

    def _backfill_created_at(self, df: pd.DataFrame, JobData):
        """将 JobData.created_at 回填为 CSV 里的 createTime,这样时间序列分析才有意义"""
        # 构建 (name, company, city) -> createTime 的映射
        idx = {}
        for _, row in df.iterrows():
            name = _first_non_empty(row.get('positionName'))
            if not name:
                continue
            company = _first_non_empty(row.get('companyFullName'), row.get('companyShortName'))
            city = _first_non_empty(row.get('city'))
            dt = _safe_date(row.get('createTime'))
            if dt:
                idx[(name, company, city)] = dt

        updated = 0
        BATCH = 500
        queryset = JobData.objects.filter(source='拉勾网')
        pending = []
        for job in queryset.iterator(chunk_size=BATCH):
            key = (job.name, job.company or '', job.city or '')
            dt = idx.get(key)
            if not dt:
                continue
            if job.created_at and abs((job.created_at - dt).total_seconds()) < 3600:
                continue  # 已一致
            job.created_at = dt
            pending.append(job)
            if len(pending) >= BATCH:
                JobData.objects.bulk_update(pending, ['created_at'])
                updated += len(pending)
                pending = []
        if pending:
            JobData.objects.bulk_update(pending, ['created_at'])
            updated += len(pending)

        if updated:
            self.stdout.write(f'  已回填 createTime -> created_at 共 {updated} 条')

    def _import_trend(self, df: pd.DataFrame, HistoricalJobData) -> int:
        """按 (key_word, 日期) 聚合岗位数量,写入 HistoricalJobData"""
        self.stdout.write(self.style.MIGRATE_HEADING('[2/3] 写入 HistoricalJobData(日度时间序列)'))

        # 聚合
        # (key_word, year, month, day) -> count
        buckets: dict[tuple[str, int, int, int], int] = defaultdict(int)
        for _, row in df.iterrows():
            dt = _safe_date(row.get('createTime'))
            if not dt:
                continue
            kw = _normalize_key_word(
                row.get('firstType'), row.get('secondType'), row.get('positionName')
            )
            if not kw:
                continue
            buckets[(kw, dt.year, dt.month, dt.day)] += 1

        to_create = []
        # HistoricalJobData 的 unique_together = (skill_id, year, month, occupation_l2, company, region)
        # 我们把 kw 哈希为 skill_id,occupation_l2 放 kw 本身
        for (kw, year, month, day), count in buckets.items():
            skill_id = abs(hash(kw)) % 10_000_000  # 稳定的小整数
            to_create.append(HistoricalJobData(
                skill_name=kw,
                skill_id=skill_id,
                year=year,
                month=month,
                date=date(year, month, day),
                demand_count=count,
                occupation_l2=kw,
                data_source='Lagou',
            ))

        created = 0
        if to_create:
            with transaction.atomic():
                HistoricalJobData.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=True)
                created = len(to_create)

        self.stdout.write(f'  聚合后写入 {created} 条日度记录,覆盖 {len({b[0] for b in buckets})} 个关键词')
        return created

    def _import_cooc(self, df: pd.DataFrame, SkillCooccurrence, SkillMapping) -> int:
        """基于 positionLables 构建技能共现"""
        self.stdout.write(self.style.MIGRATE_HEADING('[3/3] 写入 SkillCooccurrence(技能共现)'))

        # 1) 收集全部技能,分配 id
        label_counter: Counter[str] = Counter()
        rows_labels: list[list[str]] = []
        for _, row in df.iterrows():
            labels = _clean_labels(row.get('positionLables'))
            if labels:
                rows_labels.append(labels)
                label_counter.update(labels)

        skill_to_id: dict[str, int] = {}
        mappings = []
        for idx, (skill, _cnt) in enumerate(label_counter.most_common()):
            skill_to_id[skill] = idx + 1
            mappings.append(SkillMapping(
                skill_id=idx + 1,
                skill_name=skill,
                local_keyword=skill,
                confidence=1.0,
                is_manual=False,
            ))

        with transaction.atomic():
            SkillMapping.objects.filter(is_manual=False).delete()
            SkillMapping.objects.bulk_create(mappings, batch_size=500, ignore_conflicts=True)

        # 2) 共现计数
        pair_counter: Counter[tuple[int, int]] = Counter()
        for labels in rows_labels:
            uniq = sorted({skill_to_id[s] for s in labels if s in skill_to_id})
            for i in range(len(uniq)):
                for j in range(i + 1, len(uniq)):
                    pair_counter[(uniq[i], uniq[j])] += 1

        to_create = []
        id_to_skill = {v: k for k, v in skill_to_id.items()}
        for (s1, s2), freq in pair_counter.items():
            if freq < 2:  # 过滤噪音
                continue
            to_create.append(SkillCooccurrence(
                skill_1_id=s1,
                skill_1_name=id_to_skill[s1],
                skill_2_id=s2,
                skill_2_name=id_to_skill[s2],
                frequency=freq,
            ))

        created = 0
        if to_create:
            with transaction.atomic():
                SkillCooccurrence.objects.all().delete()
                SkillCooccurrence.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=True)
                created = len(to_create)

        self.stdout.write(f'  技能总数 {len(skill_to_id)},共现关系 {created} 条')
        return created
