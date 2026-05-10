"""
岗位需求趋势分析模块
=====================
数据源: 拉勾网招聘数据集 (data/Lagou_Data.csv, 2983 条, 2018-03-12 ~ 2018-04-12)

与旧版(Job-SDF)相比:
- 去掉硬编码的 KEYWORD_SKILL_GROUPS skill_id 段落映射
- 历史趋势直接查 HistoricalJobData (由 `python manage.py import_lagou --with-trend` 写入)
- 技能共现直接查 SkillCooccurrence (由 `--with-cooc` 写入)
"""
from __future__ import annotations

import numpy as np
from collections import defaultdict
from datetime import date

from django.db.models import Count, Avg, Q
from django.utils import timezone

from jobs.models import JobData
from analysis.models import HistoricalJobData, SkillCooccurrence


# 兼容旧接口:保留变量名,但值置为空字典,仅用于避免 import 崩溃。
# 任何依赖 KEYWORD_SKILL_GROUPS / DATASET_PATH 的历史代码,应改为查 HistoricalJobData。
KEYWORD_SKILL_GROUPS: dict[str, tuple[int, int]] = {}
DATASET_PATH = ''  # 不再使用 parquet 数据集

DATA_SOURCE_TAG = 'Lagou'
DATA_SOURCE_LABEL = '拉勾网招聘数据集(2018年3-4月,2983条)'


class JobTrendAnalyzer:
    """岗位趋势分析器 - 基于拉勾数据集 + 实时爬取数据"""

    def __init__(self):
        self.trend_indicators = [
            '需求稳定性', '薪资增长潜力', '技能要求变化',
            '行业分布广度', '公司规模分布'
        ]

    # ──────────────────────────── 主入口 ────────────────────────────

    def analyze_job_trend(self, keyword: str, months: int = 12) -> dict:
        jobs = JobData.objects.filter(
            Q(key_word__icontains=keyword) | Q(name__icontains=keyword)
        )
        if jobs.count() < 10:
            return {
                'success': False,
                'message': f'数据量不足(当前{jobs.count()}条,建议至少100条)',
                'suggestion': '请先通过爬虫或 `python manage.py import_lagou` 导入更多数据',
            }

        demand_stability = self._analyze_demand_stability(jobs)
        salary_analysis = self._analyze_salary_trend(jobs)
        skill_analysis = self._analyze_skill_requirements(jobs)
        industry_analysis = self._analyze_industry_distribution(jobs)
        company_analysis = self._analyze_company_scale(jobs)

        overall_score = self._calculate_overall_score(
            demand_stability, salary_analysis, skill_analysis,
            industry_analysis, company_analysis,
        )
        career_advice = self._generate_career_advice(
            keyword, overall_score, demand_stability, salary_analysis, skill_analysis
        )
        historical_trend = self._analyze_historical_trend(keyword)
        skill_recommendations = self._get_skill_recommendations(keyword)

        return {
            'success': True,
            'keyword': keyword,
            'data_count': jobs.count(),
            'demand_stability': demand_stability,
            'salary_analysis': salary_analysis,
            'skill_analysis': skill_analysis,
            'industry_analysis': industry_analysis,
            'company_analysis': company_analysis,
            'overall_score': overall_score,
            'career_advice': career_advice,
            'historical_trend': historical_trend,
            'skill_recommendations': skill_recommendations,
            'last_updated': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

    # ──────────────────────────── 多维度打分 ────────────────────────────

    def _analyze_demand_stability(self, jobs):
        total_count = jobs.count()
        source_diversity = jobs.values('source').distinct().count()
        city_dist = list(jobs.values('city').annotate(count=Count('job_id')).order_by('-count')[:10])
        city_diversity = len(city_dist)

        count_score = min(100, total_count / 10)
        source_score = min(100, source_diversity * 50)
        city_score = min(100, city_diversity * 10)
        stability_score = count_score * 0.4 + source_score * 0.3 + city_score * 0.3

        if stability_score >= 80:
            level, desc = '非常稳定', '该岗位需求量大,分布广泛,市场需求非常稳定'
        elif stability_score >= 60:
            level, desc = '较为稳定', '该岗位有一定需求量,市场需求较为稳定'
        elif stability_score >= 40:
            level, desc = '一般', '该岗位需求量一般,市场需求波动较大'
        else:
            level, desc = '不稳定', '该岗位需求量较少,市场需求不稳定'

        return {
            'score': round(stability_score, 1),
            'level': level,
            'description': desc,
            'total_count': total_count,
            'source_diversity': source_diversity,
            'city_diversity': city_diversity,
            'top_cities': [{'city': c['city'], 'count': c['count']} for c in city_dist if c['city']],
        }

    def _analyze_salary_trend(self, jobs):
        valid = jobs.exclude(salary_max__isnull=True).exclude(salary_max=0)
        if valid.count() < 10:
            return {
                'score': 50, 'level': '数据不足', 'description': '薪资数据不足,无法准确分析',
                'avg_salary': 0, 'min_salary': 0, 'salary_distribution': {}, 'high_salary_ratio': 0,
            }

        avg_salary = float(valid.aggregate(avg=Avg('salary_max'))['avg'] or 0)
        min_salary = float(valid.aggregate(avg=Avg('salary_min'))['avg'] or 0)

        ranges = {
            '5k以下': valid.filter(salary_max__lt=5).count(),
            '5-10k': valid.filter(salary_max__gte=5, salary_max__lt=10).count(),
            '10-20k': valid.filter(salary_max__gte=10, salary_max__lt=20).count(),
            '20-30k': valid.filter(salary_max__gte=20, salary_max__lt=30).count(),
            '30k以上': valid.filter(salary_max__gte=30).count(),
        }
        avg_score = min(100, (avg_salary / 50) * 100) if avg_salary else 0
        high_ratio = (ranges['20-30k'] + ranges['30k以上']) / valid.count()
        salary_score = avg_score * 0.6 + high_ratio * 100 * 0.4

        if salary_score >= 80:
            level = '优秀'
        elif salary_score >= 60:
            level = '良好'
        elif salary_score >= 40:
            level = '一般'
        else:
            level = '较低'
        desc = f'该岗位平均薪资{avg_salary:.1f}k,薪资水平{level}'

        return {
            'score': round(salary_score, 1),
            'level': level, 'description': desc,
            'avg_salary': round(avg_salary, 1),
            'min_salary': round(min_salary, 1),
            'salary_distribution': ranges,
            'high_salary_ratio': round(high_ratio * 100, 1),
        }

    def _analyze_skill_requirements(self, jobs):
        total = jobs.count()
        edu_dist = list(jobs.values('education').annotate(count=Count('job_id')).order_by('-count'))
        exp_dist = list(jobs.values('experience').annotate(count=Count('job_id')).order_by('-count'))

        low_edu = jobs.filter(
            Q(education__icontains='不限') | Q(education__icontains='大专') | Q(education__isnull=True)
        ).count()
        low_exp = jobs.filter(
            Q(experience__icontains='不限') | Q(experience__icontains='1年') |
            Q(experience__icontains='应届') | Q(experience__isnull=True)
        ).count()
        edu_acc = (low_edu / total * 100) if total else 0
        exp_acc = (low_exp / total * 100) if total else 0
        accessibility = (edu_acc + exp_acc) / 2

        if accessibility >= 60:
            level, desc = '门槛较低', '该岗位对学历和经验要求相对宽松,适合新人入行'
        elif accessibility >= 40:
            level, desc = '门槛适中', '该岗位有一定学历和经验要求,需要一定积累'
        else:
            level, desc = '门槛较高', '该岗位对学历和经验要求较高,需要充分准备'

        return {
            'score': round(accessibility, 1),
            'level': level, 'description': desc,
            'education_distribution': [{'education': e['education'], 'count': e['count']} for e in edu_dist[:5]],
            'experience_distribution': [{'experience': e['experience'], 'count': e['count']} for e in exp_dist[:5]],
            'edu_accessibility': round(edu_acc, 1),
            'exp_accessibility': round(exp_acc, 1),
        }

    def _analyze_industry_distribution(self, jobs):
        industry_dist = list(
            jobs.exclude(industry__isnull=True).exclude(industry='')
            .values('industry').annotate(count=Count('job_id')).order_by('-count')[:10]
        )
        diversity = len(industry_dist)
        score = min(100, diversity * 10)
        if score >= 70:
            level, desc = '分布广泛', '该岗位在多个行业都有需求,选择空间大'
        elif score >= 40:
            level, desc = '分布适中', '该岗位在部分行业有需求'
        else:
            level, desc = '分布集中', '该岗位主要集中在特定行业'
        return {
            'score': round(score, 1),
            'level': level, 'description': desc,
            'industry_count': diversity,
            'top_industries': [{'industry': i['industry'], 'count': i['count']} for i in industry_dist],
        }

    def _analyze_company_scale(self, jobs):
        scale_dist = list(
            jobs.exclude(scale__isnull=True).exclude(scale='')
            .values('scale').annotate(count=Count('job_id')).order_by('-count')
        )
        total = jobs.count()
        large = jobs.filter(
            Q(scale__icontains='500') | Q(scale__icontains='1000') | Q(scale__icontains='10000')
        ).count()
        large_ratio = (large / total * 100) if total else 0
        diversity_score = min(100, len(scale_dist) * 20)
        score = large_ratio * 0.6 + diversity_score * 0.4

        if score >= 60:
            level, desc = '优质', '该岗位在各类规模公司都有需求,大公司机会多'
        elif score >= 40:
            level, desc = '良好', '该岗位在不同规模公司都有一定需求'
        else:
            level, desc = '一般', '该岗位主要集中在特定规模的公司'
        return {
            'score': round(score, 1),
            'level': level, 'description': desc,
            'large_company_ratio': round(large_ratio, 1),
            'scale_distribution': [{'scale': s['scale'], 'count': s['count']} for s in scale_dist],
        }

    def _calculate_overall_score(self, demand, salary, skill, industry, company):
        weights = {'demand': 0.30, 'salary': 0.25, 'skill': 0.15, 'industry': 0.15, 'company': 0.15}
        total = (
            demand['score'] * weights['demand']
            + salary['score'] * weights['salary']
            + skill['score'] * weights['skill']
            + industry['score'] * weights['industry']
            + company['score'] * weights['company']
        )
        if total >= 80:
            rating, level, desc, color = 'S', '优秀', '该岗位发展前景优秀,强烈推荐长期发展', '#52c41a'
        elif total >= 70:
            rating, level, desc, color = 'A', '良好', '该岗位发展前景良好,推荐考虑', '#1890ff'
        elif total >= 60:
            rating, level, desc, color = 'B', '中等', '该岗位发展前景中等,可以考虑', '#faad14'
        elif total >= 50:
            rating, level, desc, color = 'C', '一般', '该岗位发展前景一般,需谨慎考虑', '#fa8c16'
        else:
            rating, level, desc, color = 'D', '较差', '该岗位发展前景较差,不建议长期发展', '#f5222d'
        return {
            'total_score': round(total, 1),
            'rating': rating, 'level': level, 'description': desc, 'color': color,
            'breakdown': {
                '需求稳定性': round(demand['score'] * weights['demand'], 1),
                '薪资水平': round(salary['score'] * weights['salary'], 1),
                '技能门槛': round(skill['score'] * weights['skill'], 1),
                '行业分布': round(industry['score'] * weights['industry'], 1),
                '公司规模': round(company['score'] * weights['company'], 1),
            },
        }

    def _generate_career_advice(self, keyword, overall, demand, salary, skill):
        out = []
        if overall['total_score'] >= 70:
            out.append({'type': 'positive', 'title': '发展前景',
                        'content': f'{keyword}岗位发展前景{overall["level"]},值得长期投入'})
        else:
            out.append({'type': 'warning', 'title': '发展前景',
                        'content': f'{keyword}岗位发展前景{overall["level"]},建议谨慎选择或作为过渡'})
        tag = 'positive' if demand['score'] >= 70 else 'warning'
        out.append({'type': tag, 'title': '市场需求',
                    'content': f'市场需求{demand["level"]}'})
        if salary['score'] >= 70:
            out.append({'type': 'positive', 'title': '薪资待遇',
                        'content': f'薪资水平{salary["level"]},平均{salary["avg_salary"]}k'})
        elif salary['score'] >= 50:
            out.append({'type': 'info', 'title': '薪资待遇',
                        'content': f'薪资水平{salary["level"]},平均{salary["avg_salary"]}k,有提升空间'})
        else:
            out.append({'type': 'warning', 'title': '薪资待遇',
                        'content': f'薪资水平{salary["level"]},平均{salary["avg_salary"]}k,建议提升技能以获得更高薪资'})
        tag = 'positive' if skill['score'] >= 60 else 'info'
        out.append({'type': tag, 'title': '入行难度', 'content': f'该岗位{skill["level"]}'})

        if overall['total_score'] >= 70:
            summary = (f'{keyword}是一个发展前景良好的职业方向,市场需求稳定,薪资待遇优秀。'
                       f'建议:1) 持续学习相关技能;2) 关注行业动态;3) 积累项目经验;4) 建立职业人脉。')
        elif overall['total_score'] >= 50:
            summary = (f'{keyword}是一个发展前景中等的职业方向,有一定市场需求。'
                       f'建议:1) 评估个人兴趣和优势;2) 考虑结合其他技能;3) 关注细分领域机会;4) 保持学习和成长。')
        else:
            summary = (f'{keyword}当前发展前景一般,建议谨慎选择。'
                       f'建议:1) 考虑相关但更有前景的方向;2) 作为技能补充而非主要方向;'
                       f'3) 关注行业变化趋势;4) 保持职业灵活性。')
        out.append({'type': 'summary', 'title': '综合建议', 'content': summary})
        return out

    # ──────────────────────────── 历史趋势(基于 HistoricalJobData) ────────────────────────────

    def _analyze_historical_trend(self, keyword: str) -> dict:
        """
        从 HistoricalJobData 按日期聚合,得到该关键词的历史趋势曲线。
        兼容两种数据来源:'Lagou'(导入的拉勾) 与 '爬虫'(JobData 实时聚合)。
        """
        qs = HistoricalJobData.objects.filter(
            Q(skill_name__icontains=keyword) | Q(occupation_l2__icontains=keyword)
        ).order_by('date')

        if not qs.exists():
            # 兜底:从 JobData.created_at 当场聚合(不依赖导入历史表)
            return self._fallback_trend_from_jobdata(keyword)

        # 按日期聚合(多关键词桶可能共存,累加)
        by_date: dict[date, int] = defaultdict(int)
        for row in qs.values('date', 'demand_count'):
            by_date[row['date']] += row['demand_count']

        if len(by_date) < 3:
            return self._fallback_trend_from_jobdata(keyword)

        sorted_dates = sorted(by_date.keys())
        values = [by_date[d] for d in sorted_dates]
        date_labels = [d.strftime('%Y-%m-%d') for d in sorted_dates]

        return self._pack_trend(keyword, date_labels, values,
                                source_label=DATA_SOURCE_LABEL + ' (按日聚合)')

    def _fallback_trend_from_jobdata(self, keyword: str) -> dict:
        """HistoricalJobData 没命中时,从 JobData.created_at 直接按日聚合"""
        qs = (JobData.objects
              .filter(Q(key_word__icontains=keyword) | Q(name__icontains=keyword))
              .exclude(created_at__isnull=True))
        if not qs.exists():
            return {'has_historical_data': False, 'message': f'"{keyword}" 暂无历史趋势数据'}

        by_date: dict[str, int] = defaultdict(int)
        for created_at in qs.values_list('created_at', flat=True):
            by_date[created_at.date().strftime('%Y-%m-%d')] += 1

        if len(by_date) < 3:
            return {'has_historical_data': False, 'message': '历史数据点不足(少于3天)'}

        labels = sorted(by_date.keys())
        values = [by_date[d] for d in labels]
        return self._pack_trend(keyword, labels, values,
                                source_label='JobData.created_at 实时聚合')

    @staticmethod
    def _pack_trend(keyword: str, labels: list[str], values: list[int], source_label: str) -> dict:
        # 归一化为相对指数(首日=100)
        base = values[0] if values[0] > 0 else max(values[0:3] + [1])
        index_series = [round(v / base * 100, 1) for v in values]

        growth = ((values[-1] - values[0]) / values[0] * 100) if values[0] > 0 else 0
        if growth > 15:
            trend, desc, icon, color = 'up', '上升趋势', '📈', '#52c41a'
        elif growth < -15:
            trend, desc, icon, color = 'down', '下降趋势', '📉', '#f5222d'
        else:
            trend, desc, icon, color = 'stable', '稳定趋势', '➡️', '#1890ff'

        std_dev = float(np.std(values))
        avg_val = float(np.mean(values))
        volatility = (std_dev / avg_val * 100) if avg_val else 0
        if volatility < 20:
            vol_desc = '波动较小,需求稳定'
        elif volatility < 40:
            vol_desc = '波动适中,需求有一定变化'
        else:
            vol_desc = '波动较大,需求变化明显'

        return {
            'has_historical_data': True,
            'time_range': f'{labels[0]} 至 {labels[-1]}',
            'data_points': len(labels),
            'dates': labels,
            'demands': index_series,   # 相对指数
            'raw_demands': values,     # 原始岗位数
            'growth_rate': round(growth, 1),
            'trend': trend,
            'trend_desc': desc,
            'trend_icon': icon,
            'trend_color': color,
            'avg_demand': round(avg_val, 1),
            'max_demand': round(max(values), 1),
            'min_demand': round(min(values), 1),
            'volatility': round(volatility, 1),
            'volatility_desc': vol_desc,
            'data_source': source_label,
            'note': '纵轴为需求相对指数(首日=100),原始岗位数见 raw_demands',
        }

    # ──────────────────────────── 技能共现 ────────────────────────────

    def _get_skill_recommendations(self, keyword: str) -> dict:
        """从 SkillCooccurrence 查与 keyword 共现频率最高的其他技能"""
        hits = SkillCooccurrence.objects.filter(
            Q(skill_1_name__icontains=keyword) | Q(skill_2_name__icontains=keyword)
        ).order_by('-frequency')[:50]

        if not hits.exists():
            return {'has_recommendations': False, 'message': '暂无相关技能推荐'}

        seen = {keyword.lower()}
        recs = []
        for row in hits:
            other = row.skill_2_name if keyword.lower() in row.skill_1_name.lower() else row.skill_1_name
            if other.lower() in seen:
                continue
            seen.add(other.lower())
            freq = row.frequency
            if freq >= 20:
                relevance, stars = '高', '⭐⭐⭐'
            elif freq >= 10:
                relevance, stars = '中', '⭐⭐'
            else:
                relevance, stars = '一般', '⭐'
            recs.append({
                'skill_name': other,
                'local_keyword': other,
                'frequency': freq,
                'relevance': relevance,
                'stars': stars,
            })
            if len(recs) >= 8:
                break

        if not recs:
            return {'has_recommendations': False, 'message': '暂无相关技能推荐'}

        return {
            'has_recommendations': True,
            'recommendations': recs,
            'total_count': len(recs),
            'message': f'基于 SkillCooccurrence 找到 {len(recs)} 个相关技能',
        }

    # ──────────────────────────── 对比 ────────────────────────────

    def compare_jobs(self, keywords: list[str]) -> dict:
        results, failed = [], []
        for kw in keywords:
            try:
                a = self.analyze_job_trend(kw)
                if a.get('success'):
                    results.append({
                        'keyword': kw,
                        'score': a['overall_score']['total_score'],
                        'rating': a['overall_score']['rating'],
                        'demand_score': a['demand_stability']['score'],
                        'salary_score': a['salary_analysis']['score'],
                        'avg_salary': a['salary_analysis']['avg_salary'],
                    })
                else:
                    failed.append(kw)
            except Exception:
                failed.append(kw)
        results.sort(key=lambda x: x['score'], reverse=True)
        resp = {
            'success': bool(results),
            'comparison': results,
            'best_choice': results[0] if results else None,
        }
        if failed:
            resp['failed_keywords'] = failed
            resp['message'] = f'部分岗位数据不足: {", ".join(failed)}'
        if not results:
            resp['message'] = '所有岗位都没有足够的数据,请先导入或爬取数据'
        return resp


# ──────────────────────────── 单例 ────────────────────────────

_analyzer: JobTrendAnalyzer | None = None


def get_analyzer() -> JobTrendAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = JobTrendAnalyzer()
    return _analyzer
