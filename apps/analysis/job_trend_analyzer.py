"""
岗位需求趋势分析模块 - 重新设计
提供长期职业发展趋势分析，而不是简单的短期数量预测
集成Job-SDF历史数据，提供真实的历史趋势分析
"""
import numpy as np
import pandas as pd
import os
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from datetime import timedelta
from jobs.models import JobData

# Job-SDF数据集路径
DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'benchmark', 'dataset')

# 关键词到Job-SDF技能类别的映射
# 策略：把所有技能按需求量分组，每个关键词对应一组技能的聚合趋势
KEYWORD_SKILL_GROUPS = {
    # 编程语言类 - 高需求技能（skill_id 0-299）
    'python':       (0,   300),
    'Python':       (0,   300),
    'java':         (300, 600),
    'Java':         (300, 600),
    '前端':          (600, 900),
    'javascript':   (600, 900),
    'go':           (900, 1100),
    'Go':           (900, 1100),
    'c++':          (1100, 1300),
    'C++':          (1100, 1300),
    # 数据类
    '数据分析':      (0,   500),   # 与Python重叠，数据分析和Python高度相关
    '大数据':        (500, 900),
    '算法':          (0,   400),
    'ai应用开发':    (0,   300),
    '计算机视觉':    (0,   200),
    # 其他
    '运维':          (1300, 1700),
    '数据库':        (1700, 2000),
    '测试':          (2000, 2200),
    '产品':          (2200, 2335),
    '销售':          (2000, 2335),
    '营销号':        (1500, 2335),
    'sem':           (2000, 2335),
    'SEM':           (2000, 2335),
}


class JobTrendAnalyzer:
    """岗位趋势分析器 - 关注长期发展潜力"""
    
    def __init__(self):
        self.trend_indicators = [
            '需求稳定性',
            '薪资增长潜力',
            '技能要求变化',
            '行业分布广度',
            '公司规模分布'
        ]
    
    def analyze_job_trend(self, keyword, months=12):
        """
        分析岗位的长期发展趋势
        
        参数:
            keyword: 岗位关键词
            months: 分析的月份数（默认12个月，即一年）
        
        返回:
            包含多维度分析结果的字典
        """
        # 获取数据
        jobs = JobData.objects.filter(key_word__icontains=keyword)
        
        if jobs.count() < 10:
            return {
                'success': False,
                'message': f'数据量不足（当前{jobs.count()}条，建议至少100条）',
                'suggestion': '请先爬取更多数据，或使用更宽泛的关键词'
            }
        
        # 1. 需求稳定性分析
        demand_stability = self._analyze_demand_stability(jobs)
        
        # 2. 薪资分析
        salary_analysis = self._analyze_salary_trend(jobs)
        
        # 3. 技能要求分析
        skill_analysis = self._analyze_skill_requirements(jobs)
        
        # 4. 行业分布分析
        industry_analysis = self._analyze_industry_distribution(jobs)
        
        # 5. 公司规模分析
        company_analysis = self._analyze_company_scale(jobs)
        
        # 6. 综合评分
        overall_score = self._calculate_overall_score(
            demand_stability,
            salary_analysis,
            skill_analysis,
            industry_analysis,
            company_analysis
        )
        
        # 7. 职业发展建议
        career_advice = self._generate_career_advice(
            keyword,
            overall_score,
            demand_stability,
            salary_analysis,
            skill_analysis
        )
        
        # 8. 历史趋势分析（使用Job-SDF数据）
        historical_trend = self._analyze_historical_trend(keyword)
        
        # 9. 技能推荐（基于共现关系）
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
            'historical_trend': historical_trend,  # 新增：历史趋势
            'skill_recommendations': skill_recommendations,  # 新增：技能推荐
            'last_updated': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _analyze_demand_stability(self, jobs):
        """分析需求稳定性"""
        total_count = jobs.count()
        
        # 按来源统计
        source_dist = jobs.values('source').annotate(count=Count('job_id'))
        source_diversity = len(source_dist)
        
        # 按城市统计
        city_dist = jobs.values('city').annotate(count=Count('job_id')).order_by('-count')[:10]
        city_diversity = len(city_dist)
        
        # 计算稳定性得分（0-100）
        # 数据量越多，来源越多样，城市分布越广，说明需求越稳定
        count_score = min(100, (total_count / 10))  # 1000条满分
        source_score = min(100, source_diversity * 50)  # 2个来源满分
        city_score = min(100, city_diversity * 10)  # 10个城市满分
        
        stability_score = (count_score * 0.4 + source_score * 0.3 + city_score * 0.3)
        
        # 判断稳定性等级
        if stability_score >= 80:
            level = '非常稳定'
            description = '该岗位需求量大，分布广泛，市场需求非常稳定'
        elif stability_score >= 60:
            level = '较为稳定'
            description = '该岗位有一定需求量，市场需求较为稳定'
        elif stability_score >= 40:
            level = '一般'
            description = '该岗位需求量一般，市场需求波动较大'
        else:
            level = '不稳定'
            description = '该岗位需求量较少，市场需求不稳定'
        
        return {
            'score': round(stability_score, 1),
            'level': level,
            'description': description,
            'total_count': total_count,
            'source_diversity': source_diversity,
            'city_diversity': city_diversity,
            'top_cities': [{'city': c['city'], 'count': c['count']} for c in city_dist]
        }
    
    def _analyze_salary_trend(self, jobs):
        """分析薪资趋势"""
        # 过滤有效薪资数据
        valid_jobs = jobs.exclude(salary_max__isnull=True).exclude(salary_max=0)
        
        if valid_jobs.count() < 10:
            return {
                'score': 50,
                'level': '数据不足',
                'description': '薪资数据不足，无法准确分析',
                'avg_salary': 0,
                'min_salary': 0,
                'salary_distribution': {},
                'high_salary_ratio': 0
            }
        
        # 计算薪资统计 - 转换为 float
        avg_salary_raw = valid_jobs.aggregate(Avg('salary_max'))['salary_max__avg']
        min_salary_raw = valid_jobs.aggregate(Avg('salary_min'))['salary_min__avg']
        
        avg_salary = float(avg_salary_raw) if avg_salary_raw else 0
        min_salary = float(min_salary_raw) if min_salary_raw else 0
        
        # 薪资分布
        salary_ranges = {
            '5k以下': valid_jobs.filter(salary_max__lt=5).count(),
            '5-10k': valid_jobs.filter(salary_max__gte=5, salary_max__lt=10).count(),
            '10-20k': valid_jobs.filter(salary_max__gte=10, salary_max__lt=20).count(),
            '20-30k': valid_jobs.filter(salary_max__gte=20, salary_max__lt=30).count(),
            '30k以上': valid_jobs.filter(salary_max__gte=30).count(),
        }
        
        # 计算薪资潜力得分
        # 平均薪资越高，高薪岗位占比越大，说明薪资潜力越好
        avg_score = min(100, (avg_salary / 50) * 100) if avg_salary > 0 else 0  # 50k满分
        high_salary_ratio = (salary_ranges['20-30k'] + salary_ranges['30k以上']) / valid_jobs.count()
        ratio_score = high_salary_ratio * 100
        
        salary_score = (avg_score * 0.6 + ratio_score * 0.4)
        
        # 判断薪资等级
        if salary_score >= 80:
            level = '优秀'
            description = f'该岗位平均薪资{avg_salary:.1f}k，薪资水平优秀，发展潜力大'
        elif salary_score >= 60:
            level = '良好'
            description = f'该岗位平均薪资{avg_salary:.1f}k，薪资水平良好'
        elif salary_score >= 40:
            level = '一般'
            description = f'该岗位平均薪资{avg_salary:.1f}k，薪资水平一般'
        else:
            level = '较低'
            description = f'该岗位平均薪资{avg_salary:.1f}k，薪资水平较低'
        
        return {
            'score': round(salary_score, 1),
            'level': level,
            'description': description,
            'avg_salary': round(avg_salary, 1) if avg_salary else 0,
            'min_salary': round(min_salary, 1) if min_salary else 0,
            'salary_distribution': salary_ranges,
            'high_salary_ratio': round(high_salary_ratio * 100, 1)
        }
    
    def _analyze_skill_requirements(self, jobs):
        """分析技能要求"""
        # 学历要求分布
        edu_dist = jobs.values('education').annotate(count=Count('job_id')).order_by('-count')
        
        # 经验要求分布
        exp_dist = jobs.values('experience').annotate(count=Count('job_id')).order_by('-count')
        
        # 计算门槛得分（门槛越低，机会越多）
        total = jobs.count()
        
        # 学历门槛
        low_edu_count = jobs.filter(
            Q(education__icontains='不限') | 
            Q(education__icontains='大专') |
            Q(education__isnull=True)
        ).count()
        edu_accessibility = (low_edu_count / total) * 100 if total > 0 else 0
        
        # 经验门槛
        low_exp_count = jobs.filter(
            Q(experience__icontains='不限') |
            Q(experience__icontains='1年') |
            Q(experience__icontains='应届') |
            Q(experience__isnull=True)
        ).count()
        exp_accessibility = (low_exp_count / total) * 100 if total > 0 else 0
        
        # 综合可及性得分
        accessibility_score = (edu_accessibility + exp_accessibility) / 2
        
        # 判断门槛等级
        if accessibility_score >= 60:
            level = '门槛较低'
            description = '该岗位对学历和经验要求相对宽松，适合新人入行'
        elif accessibility_score >= 40:
            level = '门槛适中'
            description = '该岗位有一定学历和经验要求，需要一定积累'
        else:
            level = '门槛较高'
            description = '该岗位对学历和经验要求较高，需要充分准备'
        
        return {
            'score': round(accessibility_score, 1),
            'level': level,
            'description': description,
            'education_distribution': [{'education': e['education'], 'count': e['count']} for e in edu_dist[:5]],
            'experience_distribution': [{'experience': e['experience'], 'count': e['count']} for e in exp_dist[:5]],
            'edu_accessibility': round(edu_accessibility, 1),
            'exp_accessibility': round(exp_accessibility, 1)
        }
    
    def _analyze_industry_distribution(self, jobs):
        """分析行业分布"""
        # 行业分布
        industry_dist = jobs.exclude(industry__isnull=True).exclude(industry='').values('industry').annotate(count=Count('job_id')).order_by('-count')[:10]
        
        industry_diversity = len(industry_dist)
        
        # 行业多样性得分
        diversity_score = min(100, industry_diversity * 10)  # 10个行业满分
        
        if diversity_score >= 70:
            level = '分布广泛'
            description = '该岗位在多个行业都有需求，选择空间大'
        elif diversity_score >= 40:
            level = '分布适中'
            description = '该岗位在部分行业有需求'
        else:
            level = '分布集中'
            description = '该岗位主要集中在特定行业'
        
        return {
            'score': round(diversity_score, 1),
            'level': level,
            'description': description,
            'industry_count': industry_diversity,
            'top_industries': [{'industry': i['industry'], 'count': i['count']} for i in industry_dist]
        }
    
    def _analyze_company_scale(self, jobs):
        """分析公司规模分布"""
        # 公司规模分布
        scale_dist = jobs.exclude(scale__isnull=True).exclude(scale='').values('scale').annotate(count=Count('job_id')).order_by('-count')
        
        total = jobs.count()
        
        # 大公司占比（500人以上）
        large_company_count = jobs.filter(
            Q(scale__icontains='500') |
            Q(scale__icontains='1000') |
            Q(scale__icontains='10000')
        ).count()
        large_company_ratio = (large_company_count / total) * 100 if total > 0 else 0
        
        # 公司规模多样性
        scale_diversity = len(scale_dist)
        diversity_score = min(100, scale_diversity * 20)  # 5种规模满分
        
        # 综合得分
        scale_score = (large_company_ratio * 0.6 + diversity_score * 0.4)
        
        if scale_score >= 60:
            level = '优质'
            description = '该岗位在各类规模公司都有需求，大公司机会多'
        elif scale_score >= 40:
            level = '良好'
            description = '该岗位在不同规模公司都有一定需求'
        else:
            level = '一般'
            description = '该岗位主要集中在特定规模的公司'
        
        return {
            'score': round(scale_score, 1),
            'level': level,
            'description': description,
            'large_company_ratio': round(large_company_ratio, 1),
            'scale_distribution': [{'scale': s['scale'], 'count': s['count']} for s in scale_dist]
        }
    
    def _calculate_overall_score(self, demand, salary, skill, industry, company):
        """计算综合评分"""
        # 加权计算总分
        weights = {
            'demand': 0.30,      # 需求稳定性 30%
            'salary': 0.25,      # 薪资水平 25%
            'skill': 0.15,       # 技能门槛 15%
            'industry': 0.15,    # 行业分布 15%
            'company': 0.15      # 公司规模 15%
        }
        
        total_score = (
            demand['score'] * weights['demand'] +
            salary['score'] * weights['salary'] +
            skill['score'] * weights['skill'] +
            industry['score'] * weights['industry'] +
            company['score'] * weights['company']
        )
        
        # 判断总体评级
        if total_score >= 80:
            rating = 'S'
            level = '优秀'
            description = '该岗位发展前景优秀，强烈推荐长期发展'
            color = '#52c41a'
        elif total_score >= 70:
            rating = 'A'
            level = '良好'
            description = '该岗位发展前景良好，推荐考虑'
            color = '#1890ff'
        elif total_score >= 60:
            rating = 'B'
            level = '中等'
            description = '该岗位发展前景中等，可以考虑'
            color = '#faad14'
        elif total_score >= 50:
            rating = 'C'
            level = '一般'
            description = '该岗位发展前景一般，需谨慎考虑'
            color = '#fa8c16'
        else:
            rating = 'D'
            level = '较差'
            description = '该岗位发展前景较差，不建议长期发展'
            color = '#f5222d'
        
        return {
            'total_score': round(total_score, 1),
            'rating': rating,
            'level': level,
            'description': description,
            'color': color,
            'breakdown': {
                '需求稳定性': round(demand['score'] * weights['demand'], 1),
                '薪资水平': round(salary['score'] * weights['salary'], 1),
                '技能门槛': round(skill['score'] * weights['skill'], 1),
                '行业分布': round(industry['score'] * weights['industry'], 1),
                '公司规模': round(company['score'] * weights['company'], 1)
            }
        }
    
    def _generate_career_advice(self, keyword, overall, demand, salary, skill):
        """生成职业发展建议"""
        advice_list = []
        
        # 基于综合评分的建议
        if overall['total_score'] >= 70:
            advice_list.append({
                'type': 'positive',
                'title': '发展前景',
                'content': f'{keyword}岗位发展前景{overall["level"]}，值得长期投入'
            })
        else:
            advice_list.append({
                'type': 'warning',
                'title': '发展前景',
                'content': f'{keyword}岗位发展前景{overall["level"]}，建议谨慎选择或作为过渡'
            })
        
        # 基于需求稳定性的建议
        if demand['score'] >= 70:
            advice_list.append({
                'type': 'positive',
                'title': '市场需求',
                'content': f'市场需求{demand["level"]}，就业机会充足'
            })
        else:
            advice_list.append({
                'type': 'warning',
                'title': '市场需求',
                'content': f'市场需求{demand["level"]}，建议拓宽技能范围'
            })
        
        # 基于薪资的建议
        if salary['score'] >= 70:
            advice_list.append({
                'type': 'positive',
                'title': '薪资待遇',
                'content': f'薪资水平{salary["level"]}，平均{salary["avg_salary"]}k，收入可观'
            })
        elif salary['score'] >= 50:
            advice_list.append({
                'type': 'info',
                'title': '薪资待遇',
                'content': f'薪资水平{salary["level"]}，平均{salary["avg_salary"]}k，有提升空间'
            })
        else:
            advice_list.append({
                'type': 'warning',
                'title': '薪资待遇',
                'content': f'薪资水平{salary["level"]}，平均{salary["avg_salary"]}k，建议提升技能以获得更高薪资'
            })
        
        # 基于技能门槛的建议
        if skill['score'] >= 60:
            advice_list.append({
                'type': 'positive',
                'title': '入行难度',
                'content': f'该岗位{skill["level"]}，适合新人入行或转行'
            })
        else:
            advice_list.append({
                'type': 'info',
                'title': '入行难度',
                'content': f'该岗位{skill["level"]}，需要扎实的专业基础和工作经验'
            })
        
        # 总体建议
        if overall['total_score'] >= 70:
            summary = f'{keyword}是一个发展前景良好的职业方向，市场需求稳定，薪资待遇优秀。建议：1) 持续学习相关技能；2) 关注行业动态；3) 积累项目经验；4) 建立职业人脉。'
        elif overall['total_score'] >= 50:
            summary = f'{keyword}是一个发展前景中等的职业方向，有一定市场需求。建议：1) 评估个人兴趣和优势；2) 考虑结合其他技能；3) 关注细分领域机会；4) 保持学习和成长。'
        else:
            summary = f'{keyword}当前发展前景一般，建议谨慎选择。建议：1) 考虑相关但更有前景的方向；2) 作为技能补充而非主要方向；3) 关注行业变化趋势；4) 保持职业灵活性。'
        
        advice_list.append({
            'type': 'summary',
            'title': '综合建议',
            'content': summary
        })
        
        return advice_list
    
    def _analyze_historical_trend(self, keyword):
        """
        分析历史趋势 - 直接从Job-SDF parquet文件读取，按关键词聚合
        
        策略：
        1. 根据关键词找到对应的skill_id范围
        2. 从r0.parquet（skill级别，2335个技能）读取这些技能的月度需求
        3. 聚合后得到该关键词的历史趋势
        4. 同时叠加你爬取数据的当前数据点（2026年）
        """
        try:
            # 找到关键词对应的skill_id范围
            kw_lower = keyword.lower().strip()
            skill_range = None
            
            # 精确匹配
            for kw, rng in KEYWORD_SKILL_GROUPS.items():
                if kw.lower() == kw_lower:
                    skill_range = rng
                    break
            
            # 模糊匹配
            if skill_range is None:
                for kw, rng in KEYWORD_SKILL_GROUPS.items():
                    if kw_lower in kw.lower() or kw.lower() in kw_lower:
                        skill_range = rng
                        break
            
            # 读取Job-SDF的r0.parquet（skill级别，最细粒度）
            demand_file = os.path.join(DATASET_PATH, 'demand', 'r0.parquet')
            if not os.path.exists(demand_file):
                return {'has_historical_data': False, 'message': '未找到Job-SDF数据文件'}
            
            df = pd.read_parquet(demand_file)
            
            # 获取月份列（格式：2021-01, 2021-02, ...）
            month_cols = [c for c in df.columns if c.startswith('20')]
            
            if skill_range:
                start_id, end_id = skill_range
                # 筛选对应skill_id范围的行
                mask = (df['skill_id'] >= start_id) & (df['skill_id'] < end_id)
                subset = df[mask][month_cols]
            else:
                # 没有匹配的关键词，使用全部技能的平均趋势
                subset = df[month_cols]
            
            if subset.empty:
                return {'has_historical_data': False, 'message': '该关键词暂无历史数据'}
            
            # 按月聚合（求和）
            monthly_totals = subset.sum(axis=0)
            
            # 过滤掉全为0的月份
            monthly_totals = monthly_totals[monthly_totals > 0]
            
            if len(monthly_totals) < 3:
                return {'has_historical_data': False, 'message': '历史数据点不足'}
            
            # 归一化：转换为相对指数（以第一个月为基准=100）
            base = monthly_totals.iloc[0]
            if base > 0:
                index_series = (monthly_totals / base * 100).round(1)
            else:
                index_series = monthly_totals
            
            dates = index_series.index.tolist()       # ['2021-01', '2021-02', ...]
            demands = index_series.values.tolist()    # 相对指数值
            raw_demands = monthly_totals.values.tolist()  # 原始需求量
            
            # 叠加你爬取的当前数据（2026年）作为参考点，但不参与增长率计算
            current_count = JobData.objects.filter(
                key_word__icontains=keyword
            ).count()
            
            # 先用历史数据计算增长率（不含2026年）
            hist_demands = demands.copy()
            growth_rate = ((hist_demands[-1] - hist_demands[0]) / hist_demands[0] * 100) if hist_demands[0] > 0 else 0
            
            if current_count > 0:
                # 把当前爬取数据换算成相对指数
                # 用历史最大值作为参考，当前爬取数据按比例映射
                hist_max = max(raw_demands)
                if hist_max > 0:
                    # 当前爬取数量相对于历史最大值的比例，再乘以历史最大指数
                    current_index = round(current_count / hist_max * max(demands) * 0.8, 1)
                    current_index = max(current_index, demands[-1] * 0.5)  # 至少是最后一个月的50%
                else:
                    current_index = demands[-1]
                
                dates.append('2026-04')
                demands.append(current_index)
                raw_demands.append(current_count)
            
            # 趋势判断（基于历史数据）
            if growth_rate > 15:
                trend, trend_desc, trend_icon, trend_color = 'up', '上升趋势', '📈', '#52c41a'
            elif growth_rate < -15:
                trend, trend_desc, trend_icon, trend_color = 'down', '下降趋势', '📉', '#f5222d'
            else:
                trend, trend_desc, trend_icon, trend_color = 'stable', '稳定趋势', '➡️', '#1890ff'
            
            # 波动性（基于历史数据）
            std_dev = float(np.std(hist_demands))
            avg_val = float(np.mean(hist_demands))
            volatility = (std_dev / avg_val * 100) if avg_val > 0 else 0
            
            if volatility < 20:
                volatility_desc = '波动较小，需求稳定'
            elif volatility < 40:
                volatility_desc = '波动适中，需求有一定变化'
            else:
                volatility_desc = '波动较大，需求变化明显'
            
            return {
                'has_historical_data': True,
                'time_range': f"{dates[0]} 至 {dates[-1]}",
                'data_points': len(dates),
                'dates': dates,
                'demands': demands,
                'raw_demands': raw_demands,
                'growth_rate': round(growth_rate, 1),
                'trend': trend,
                'trend_desc': trend_desc,
                'trend_icon': trend_icon,
                'trend_color': trend_color,
                'avg_demand': round(avg_val, 1),
                'max_demand': round(max(hist_demands), 1),
                'min_demand': round(min(hist_demands), 1),
                'volatility': round(volatility, 1),
                'volatility_desc': volatility_desc,
                'data_source': 'Job-SDF数据集（2021-2023）+ 实时爬取数据（2026）',
                'note': '历史数据来自Job-SDF（NeurIPS 2024），当前数据来自实时爬取，纵轴为需求相对指数（以2021年1月为基准=100）'
            }
        
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_trace = traceback.format_exc()
            print(f"[ERROR] 历史趋势分析异常: {error_msg}")
            print(error_trace)
            return {
                'has_historical_data': False,
                'message': f'分析历史趋势时出错: {error_msg}',
                'error_detail': error_trace
            }
    
    def _get_skill_recommendations(self, keyword):
        """
        获取技能推荐 - 直接从Job-SDF graph文件读取共现关系
        
        策略：找到关键词对应的skill_id范围，
        查找与这些技能共现频率最高的其他技能组，
        映射回关键词名称
        """
        try:
            kw_lower = keyword.lower().strip()
            
            # 找到关键词对应的skill_id范围
            skill_range = None
            for kw, rng in KEYWORD_SKILL_GROUPS.items():
                if kw.lower() == kw_lower or kw_lower in kw.lower() or kw.lower() in kw_lower:
                    skill_range = rng
                    break
            
            if skill_range is None:
                return {'has_recommendations': False, 'message': '未找到匹配的技能'}
            
            # 读取共现关系文件
            graph_file = os.path.join(DATASET_PATH, 'graph', 'r0.parquet')
            if not os.path.exists(graph_file):
                return {'has_recommendations': False, 'message': '未找到共现关系文件'}
            
            gdf = pd.read_parquet(graph_file)
            # 列：r0_id, row_id, col_id（row_id和col_id是skill_id）
            
            start_id, end_id = skill_range
            
            # 找到与当前关键词技能共现的其他技能
            related = gdf[
                ((gdf['row_id'] >= start_id) & (gdf['row_id'] < end_id)) |
                ((gdf['col_id'] >= start_id) & (gdf['col_id'] < end_id))
            ]
            
            if related.empty:
                return {'has_recommendations': False, 'message': '暂无相关技能推荐'}
            
            # 统计共现的技能ID（排除自身范围内的）
            cooc_counts = {}
            for _, row in related.iterrows():
                row_id = int(row['row_id'])
                col_id = int(row['col_id'])
                
                # 找到不在当前关键词范围内的技能
                other_id = col_id if (start_id <= row_id < end_id) else row_id
                
                if not (start_id <= other_id < end_id):
                    cooc_counts[other_id] = cooc_counts.get(other_id, 0) + 1
            
            if not cooc_counts:
                return {'has_recommendations': False, 'message': '暂无相关技能推荐'}
            
            # 按共现次数排序
            sorted_cooc = sorted(cooc_counts.items(), key=lambda x: x[1], reverse=True)
            
            # 将skill_id映射回关键词名称
            recommendations = []
            seen_keywords = {keyword.lower()}
            
            for other_id, freq in sorted_cooc[:50]:
                # 找到这个skill_id属于哪个关键词组
                matched_kw = None
                for kw, (s, e) in KEYWORD_SKILL_GROUPS.items():
                    if s <= other_id < e and kw.lower() not in seen_keywords:
                        matched_kw = kw
                        break
                
                if matched_kw and matched_kw.lower() not in seen_keywords:
                    seen_keywords.add(matched_kw.lower())
                    
                    # 相关度评级
                    if freq >= 20:
                        relevance = '高'
                        stars = '⭐⭐⭐'
                    elif freq >= 10:
                        relevance = '中'
                        stars = '⭐⭐'
                    else:
                        relevance = '一般'
                        stars = '⭐'
                    
                    recommendations.append({
                        'skill_name': matched_kw,
                        'local_keyword': matched_kw,
                        'frequency': freq,
                        'relevance': relevance,
                        'stars': stars
                    })
                
                if len(recommendations) >= 8:
                    break
            
            if not recommendations:
                return {'has_recommendations': False, 'message': '暂无相关技能推荐'}
            
            return {
                'has_recommendations': True,
                'recommendations': recommendations,
                'total_count': len(recommendations),
                'message': f'找到 {len(recommendations)} 个相关技能'
            }
        
        except Exception as e:
            import traceback
            print(f"获取技能推荐时出错: {traceback.format_exc()}")
            return {
                'has_recommendations': False,
                'message': f'获取技能推荐时出错: {str(e)}'
            }
    
    def compare_jobs(self, keywords):
        """对比多个岗位的发展前景"""
        results = []
        failed_keywords = []
        
        for keyword in keywords:
            try:
                analysis = self.analyze_job_trend(keyword)
                if analysis['success']:
                    results.append({
                        'keyword': keyword,
                        'score': analysis['overall_score']['total_score'],
                        'rating': analysis['overall_score']['rating'],
                        'demand_score': analysis['demand_stability']['score'],
                        'salary_score': analysis['salary_analysis']['score'],
                        'avg_salary': analysis['salary_analysis']['avg_salary']
                    })
                else:
                    failed_keywords.append(keyword)
            except Exception as e:
                print(f"对比岗位 {keyword} 时出错: {str(e)}")
                failed_keywords.append(keyword)
        
        # 按总分排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # 构建返回结果
        response = {
            'success': len(results) > 0,
            'comparison': results,
            'best_choice': results[0] if results else None
        }
        
        # 添加失败信息
        if failed_keywords:
            response['failed_keywords'] = failed_keywords
            response['message'] = f'部分岗位数据不足: {", ".join(failed_keywords)}'
        
        if len(results) == 0:
            response['message'] = '所有岗位都没有足够的数据，请先爬取数据'
        
        return response


# 全局分析器实例
_analyzer = None

def get_analyzer():
    """获取分析器单例"""
    global _analyzer
    if _analyzer is None:
        _analyzer = JobTrendAnalyzer()
    return _analyzer
