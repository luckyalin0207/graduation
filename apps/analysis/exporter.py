"""
数据导出模块
支持将分析数据导出为Excel格式
"""
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.chart import BarChart, PieChart, Reference
from django.http import HttpResponse
from jobs.models import JobData
from django.db.models import Count, Avg, Max, Min
import io


class DataExporter:
    """数据导出器"""
    
    @staticmethod
    def export_salary_distribution(job_type=''):
        """导出薪资分布数据"""
        jobs = JobData.objects.exclude(salary_max__isnull=True)
        
        if job_type:
            jobs = jobs.filter(key_word__icontains=job_type)
        
        # 薪资区间统计
        salary_ranges = [
            ('5K及以下', 0, 5),
            ('5-10K', 5, 10),
            ('10-15K', 10, 15),
            ('15-20K', 15, 20),
            ('20-30K', 20, 30),
            ('30-50K', 30, 50),
            ('50K以上', 50, 9999),
        ]
        
        data = []
        for name, min_v, max_v in salary_ranges:
            count = jobs.filter(salary_max__gte=min_v, salary_max__lt=max_v).count()
            data.append({'薪资区间': name, '职位数量': count})
        
        df = pd.DataFrame(data)
        return df
    
    @staticmethod
    def export_city_distribution(job_type=''):
        """导出城市分布数据"""
        jobs = JobData.objects.all()
        
        if job_type:
            jobs = jobs.filter(key_word__icontains=job_type)
        
        city_counts = jobs.values('city').annotate(
            count=Count('job_id'),
            avg_salary=Avg('salary_max')
        ).order_by('-count')[:30]
        
        data = []
        for item in city_counts:
            if item['city']:
                data.append({
                    '城市': item['city'],
                    '职位数量': item['count'],
                    '平均薪资(K)': round(item['avg_salary'], 2) if item['avg_salary'] else 0
                })
        
        df = pd.DataFrame(data)
        return df
    
    @staticmethod
    def export_education_distribution(job_type=''):
        """导出学历分布数据"""
        jobs = JobData.objects.all()
        
        if job_type:
            jobs = jobs.filter(key_word__icontains=job_type)
        
        edu_list = ['博士', '硕士', '本科', '大专', '中专', '高中', '不限']
        data = []
        
        for edu in edu_list:
            count = jobs.filter(education__icontains=edu).count()
            if count > 0:
                avg_salary = jobs.filter(education__icontains=edu).exclude(
                    salary_max__isnull=True
                ).aggregate(avg=Avg('salary_max'))['avg']
                
                data.append({
                    '学历要求': edu,
                    '职位数量': count,
                    '平均薪资(K)': round(avg_salary, 2) if avg_salary else 0
                })
        
        df = pd.DataFrame(data)
        return df
    
    @staticmethod
    def export_experience_distribution(job_type=''):
        """导出经验分布数据"""
        jobs = JobData.objects.all()
        
        if job_type:
            jobs = jobs.filter(key_word__icontains=job_type)
        
        exp_list = ['应届', '1年', '1-3年', '3-5年', '5-10年', '10年以上', '经验不限']
        data = []
        
        for exp in exp_list:
            count = jobs.filter(experience__icontains=exp).count()
            if count > 0:
                avg_salary = jobs.filter(experience__icontains=exp).exclude(
                    salary_max__isnull=True
                ).aggregate(avg=Avg('salary_max'))['avg']
                
                data.append({
                    '经验要求': exp,
                    '职位数量': count,
                    '平均薪资(K)': round(avg_salary, 2) if avg_salary else 0
                })
        
        df = pd.DataFrame(data)
        return df
    
    @staticmethod
    def export_top_jobs(job_type='', top_n=50):
        """导出高薪职位列表"""
        jobs = JobData.objects.exclude(salary_max__isnull=True)
        
        if job_type:
            jobs = jobs.filter(key_word__icontains=job_type)
        
        top_jobs = jobs.order_by('-salary_max')[:top_n]
        
        data = []
        for job in top_jobs:
            data.append({
                '职位名称': job.name,
                '公司': job.company,
                '薪资': job.salary,
                '城市': job.city,
                '学历': job.education,
                '经验': job.experience,
                '关键词': job.key_word,
                '最高薪资(K)': float(job.salary_max) if job.salary_max else 0
            })
        
        df = pd.DataFrame(data)
        return df
    
    @staticmethod
    def export_historical_sdf(job_type=''):
        """导出 Job-SDF 历史需求数据"""
        try:
            from analysis.job_trend_analyzer import KEYWORD_SKILL_GROUPS, DATASET_PATH
            import pandas as pd
            import os

            demand_file = os.path.join(DATASET_PATH, 'demand', 'r0.parquet')
            if not os.path.exists(demand_file):
                return pd.DataFrame({'说明': ['未找到Job-SDF数据文件，请确认benchmark/dataset目录存在']})

            df = pd.read_parquet(demand_file)
            month_cols = [c for c in df.columns if str(c).startswith('20')]

            rows = []
            seen = set()
            for kw, (s, e) in KEYWORD_SKILL_GROUPS.items():
                if kw in seen:
                    continue
                seen.add(kw)
                # 如果指定了job_type，只导出匹配的
                if job_type and job_type.lower() not in kw.lower() and kw.lower() not in job_type.lower():
                    continue
                subset = df[(df['skill_id'] >= s) & (df['skill_id'] < e)][month_cols]
                monthly = subset.sum(axis=0)
                base = monthly.iloc[0] if len(monthly) > 0 and monthly.iloc[0] > 0 else 1
                index_s = (monthly / base * 100).round(1)
                row = {'技能/岗位': kw}
                for col, val in index_s.items():
                    row[str(col)] = val
                rows.append(row)

            if not rows:
                return pd.DataFrame({'说明': ['无匹配的Job-SDF历史数据']})

            result_df = pd.DataFrame(rows)
            return result_df
        except Exception as e:
            return pd.DataFrame({'说明': [f'导出Job-SDF数据时出错: {str(e)}']})

    @staticmethod
    def create_excel_report(job_type=''):
        """创建完整的Excel报告"""
        # 创建一个BytesIO对象来存储Excel文件
        output = io.BytesIO()
        
        # 创建Excel writer
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 导出各个维度的数据
            df_salary = DataExporter.export_salary_distribution(job_type)
            df_city = DataExporter.export_city_distribution(job_type)
            df_edu = DataExporter.export_education_distribution(job_type)
            df_exp = DataExporter.export_experience_distribution(job_type)
            df_top = DataExporter.export_top_jobs(job_type)
            
            # 写入不同的sheet
            df_salary.to_excel(writer, sheet_name='薪资分布', index=False)
            df_city.to_excel(writer, sheet_name='城市分布', index=False)
            df_edu.to_excel(writer, sheet_name='学历分布', index=False)
            df_exp.to_excel(writer, sheet_name='经验分布', index=False)
            df_top.to_excel(writer, sheet_name='高薪职位TOP50', index=False)
            
            # Job-SDF 历史数据 Sheet
            df_sdf = DataExporter.export_historical_sdf(job_type)
            df_sdf.to_excel(writer, sheet_name='Job-SDF历史需求指数', index=False)
            
            # 添加概览页
            jobs = JobData.objects.all()
            if job_type:
                jobs = jobs.filter(key_word__icontains=job_type)
            
            summary_data = {
                '统计项': ['总职位数', '平均薪资(K)', '最高薪资(K)', '最低薪资(K)', '分析类型'],
                '数值': [
                    jobs.count(),
                    round(jobs.exclude(salary_max__isnull=True).aggregate(avg=Avg('salary_max'))['avg'] or 0, 2),
                    jobs.exclude(salary_max__isnull=True).aggregate(max=Max('salary_max'))['max'] or 0,
                    jobs.exclude(salary_min__isnull=True).aggregate(min=Min('salary_min'))['min'] or 0,
                    job_type if job_type else '全部职位'
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='数据概览', index=False)
        
        # 获取Excel文件内容
        output.seek(0)
        return output.getvalue()
    
    @staticmethod
    def export_to_response(job_type=''):
        """生成HTTP响应用于下载"""
        excel_data = DataExporter.create_excel_report(job_type)
        
        response = HttpResponse(
            excel_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        filename = f'招聘数据分析报告_{job_type if job_type else "全部"}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

