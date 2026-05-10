"""
Job-SDF数据集导入脚本
用于导入Job-SDF数据集到Django数据库
"""
import os
import json
import pandas as pd
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from .models import HistoricalJobData, SkillMapping, SkillCooccurrence


class JobSDFImporter:
    """Job-SDF数据集导入器"""
    
    def __init__(self, dataset_path):
        """
        初始化导入器
        
        参数:
            dataset_path: Job-SDF数据集的路径（benchmark/dataset目录）
        """
        self.dataset_path = dataset_path
        self.demand_path = os.path.join(dataset_path, 'demand')
        self.entity_map_path = os.path.join(dataset_path, 'entity_map')
        self.graph_path = os.path.join(dataset_path, 'graph')
        self.proportion_path = os.path.join(dataset_path, 'proportion')
        
        # 技能关键词映射（用于将Job-SDF的技能映射到本地关键词）
        self.keyword_mapping = {
            'python': 'Python',
            'java': 'Java',
            'javascript': '前端',
            'js': '前端',
            'react': '前端',
            'vue': '前端',
            'angular': '前端',
            'html': '前端',
            'css': '前端',
            'node': '后端',
            'nodejs': '后端',
            'spring': 'Java',
            'django': 'Python',
            'flask': 'Python',
            'sql': '数据库',
            'mysql': '数据库',
            'postgresql': '数据库',
            'mongodb': '数据库',
            'redis': '数据库',
            'docker': '运维',
            'kubernetes': '运维',
            'k8s': '运维',
            'linux': '运维',
            'aws': '云计算',
            'azure': '云计算',
            'gcp': '云计算',
            'machine learning': '算法',
            'deep learning': '算法',
            'ai': '算法',
            'data science': '数据分析',
            'data analysis': '数据分析',
            'big data': '大数据',
            'hadoop': '大数据',
            'spark': '大数据',
            'android': 'Android',
            'ios': 'iOS',
            'swift': 'iOS',
            'kotlin': 'Android',
            'c++': 'C++',
            'c#': 'C#',
            'go': 'Go',
            'golang': 'Go',
            'rust': 'Rust',
            'php': 'PHP',
            'ruby': 'Ruby',
        }
    
    def import_all(self, granularity='l2', limit_skills=None):
        """
        导入所有数据
        
        参数:
            granularity: 粒度级别 ('l1', 'l2', 'company', 'region')
            limit_skills: 限制导入的技能数量（None表示全部导入）
        """
        print(f"开始导入Job-SDF数据集（粒度: {granularity}）...")
        print(f"数据集路径: {self.dataset_path}")
        
        # 1. 导入技能映射
        print("\n[1/3] 导入技能映射...")
        skill_count = self.import_skill_mapping(limit_skills)
        
        if skill_count == 0:
            print("⚠️ 没有技能映射数据，无法继续导入")
            return
        
        # 2. 导入历史需求数据
        print("\n[2/3] 导入历史需求数据...")
        data_count = self.import_demand_data(granularity, limit_skills)
        
        # 3. 导入技能共现关系
        print("\n[3/3] 导入技能共现关系...")
        cooc_count = self.import_skill_graph(granularity, limit_skills)
        
        print(f"\n✅ 数据导入完成！")
        print(f"   - 技能映射: {skill_count} 条")
        print(f"   - 历史数据: {data_count} 条")
        print(f"   - 共现关系: {cooc_count} 条")
    
    def import_skill_mapping(self, limit_skills=None):
        """导入技能映射表"""
        # 读取技能映射文件
        skill_map_file = os.path.join(self.entity_map_path, 'skill_map.json')
        
        if not os.path.exists(skill_map_file):
            print(f"⚠️ 技能映射文件不存在: {skill_map_file}")
            print("   尝试从需求数据中提取技能...")
            return self._extract_skills_from_demand(limit_skills)
        
        with open(skill_map_file, 'r', encoding='utf-8') as f:
            skill_map = json.load(f)
        
        # 限制技能数量
        if limit_skills:
            skill_map = dict(list(skill_map.items())[:limit_skills])
        
        # 批量创建映射
        mappings = []
        for skill_id, skill_name in skill_map.items():
            # 提取本地关键词
            local_keyword = self._extract_keyword(skill_name)
            
            mappings.append(SkillMapping(
                skill_id=int(skill_id),
                skill_name=skill_name,
                local_keyword=local_keyword,
                confidence=1.0,
                is_manual=False
            ))
        
        # 批量插入
        with transaction.atomic():
            SkillMapping.objects.all().delete()  # 清空旧数据
            SkillMapping.objects.bulk_create(mappings, ignore_conflicts=True)
        
        print(f"✅ 导入了 {len(mappings)} 个技能映射")
        return len(mappings)
    
    def _extract_skills_from_demand(self, limit_skills=None):
        """从需求数据中提取技能列表"""
        # 尝试读取任意一个需求文件（支持新旧两种命名）
        for filename in ['r2.parquet', 'r1.parquet', 'r0.parquet', 'l2.parquet', 'l1.parquet', 'company.parquet']:
            demand_file = os.path.join(self.demand_path, filename)
            if os.path.exists(demand_file):
                print(f"正在从 {filename} 提取技能...")
                df = pd.read_parquet(demand_file)
                
                # 使用索引作为技能ID
                mappings = []
                skill_ids = df.index.tolist()
                
                if limit_skills:
                    skill_ids = skill_ids[:limit_skills]
                
                for skill_id in skill_ids:
                    skill_name = f"Skill_{skill_id}"
                    local_keyword = f"技能{skill_id}"
                    
                    mappings.append(SkillMapping(
                        skill_id=int(skill_id),
                        skill_name=skill_name,
                        local_keyword=local_keyword,
                        confidence=0.5,
                        is_manual=False
                    ))
                
                with transaction.atomic():
                    SkillMapping.objects.all().delete()
                    SkillMapping.objects.bulk_create(mappings, ignore_conflicts=True)
                
                print(f"✅ 从需求数据中提取了 {len(mappings)} 个技能")
                return len(mappings)
        
        print("❌ 无法提取技能列表")
        return 0
    
    def import_demand_data(self, granularity='l2', limit_skills=None):
        """导入历史需求数据"""
        # 映射粒度参数到实际文件名
        granularity_map = {
            'l1': 'r1',
            'l2': 'r2',
            'r0': 'r0',
            'r1': 'r1',
            'r2': 'r2',
            'company': 'company',
            'region': 'region'
        }
        
        file_granularity = granularity_map.get(granularity, granularity)
        
        # 读取需求数据文件
        demand_file = os.path.join(self.demand_path, f'{file_granularity}.parquet')
        
        if not os.path.exists(demand_file):
            print(f"⚠️ 需求数据文件不存在: {demand_file}")
            return 0
        
        # 读取parquet文件
        print(f"正在读取文件: {demand_file}")
        df = pd.read_parquet(demand_file)
        
        print(f"数据形状: {df.shape}")
        print(f"技能数量: {len(df)}")
        print(f"时间跨度: {len(df.columns)} 个月")
        
        # 限制技能数量
        if limit_skills:
            df = df.head(limit_skills)
            print(f"限制为前 {limit_skills} 个技能")
        
        # 获取技能映射
        skill_mappings = {sm.skill_id: sm.skill_name 
                         for sm in SkillMapping.objects.all()}
        
        # 转换数据
        historical_data = []
        start_date = datetime(2021, 1, 1)  # 假设从2021年1月开始
        
        total_rows = len(df)
        for idx, (skill_idx, row) in enumerate(df.iterrows()):
            if (idx + 1) % 100 == 0:
                print(f"处理进度: {idx + 1}/{total_rows} ({(idx+1)/total_rows*100:.1f}%)")
            
            skill_id = int(skill_idx)
            skill_name = skill_mappings.get(skill_id, f'Skill_{skill_id}')
            
            for month_idx, demand_count in enumerate(row):
                if pd.isna(demand_count) or demand_count == 0:
                    continue
                
                # 计算日期
                year = start_date.year + (start_date.month + month_idx - 1) // 12
                month = (start_date.month + month_idx - 1) % 12 + 1
                date = datetime(year, month, 1)
                
                historical_data.append(HistoricalJobData(
                    skill_id=skill_id,
                    skill_name=skill_name,
                    year=year,
                    month=month,
                    date=date,
                    demand_count=int(demand_count),
                    occupation_l2=granularity if granularity.startswith('l') else None,
                    data_source='Job-SDF'
                ))
        
        # 批量插入（分批处理，避免内存溢出）
        batch_size = 10000
        total_batches = (len(historical_data) + batch_size - 1) // batch_size
        
        print(f"\n开始批量插入数据...")
        with transaction.atomic():
            # 清空旧数据
            HistoricalJobData.objects.filter(data_source='Job-SDF').delete()
        
        for i in range(0, len(historical_data), batch_size):
            batch = historical_data[i:i+batch_size]
            with transaction.atomic():
                HistoricalJobData.objects.bulk_create(batch, ignore_conflicts=True)
            
            print(f"插入进度: {i//batch_size + 1}/{total_batches} 批次")
        
        print(f"✅ 导入了 {len(historical_data)} 条历史数据")
        return len(historical_data)
    
    def import_skill_graph(self, granularity='l2', limit_skills=None):
        """导入技能共现关系"""
        # 映射粒度参数到实际文件名
        granularity_map = {
            'l1': 'r1',
            'l2': 'r2',
            'r0': 'r0',
            'r1': 'r1',
            'r2': 'r2',
            'company': 'company',
            'region': 'region'
        }
        
        file_granularity = granularity_map.get(granularity, granularity)
        
        # 尝试读取parquet文件
        graph_file = os.path.join(self.graph_path, f'{file_granularity}.parquet')
        
        if not os.path.exists(graph_file):
            print(f"⚠️ 技能共现文件不存在: {graph_file}")
            return 0
        
        # 读取parquet文件
        print(f"正在读取文件: {graph_file}")
        df = pd.read_parquet(graph_file)
        
        print(f"共现关系数量: {len(df)}")
        
        # 获取技能映射
        skill_mappings = {sm.skill_id: sm.skill_name 
                         for sm in SkillMapping.objects.all()}
        
        # 如果限制技能数量，只导入相关的共现关系
        if limit_skills:
            valid_skill_ids = set(skill_mappings.keys())
            df = df[
                df.iloc[:, 0].isin(valid_skill_ids) & 
                df.iloc[:, 1].isin(valid_skill_ids)
            ]
            print(f"限制后的共现关系数量: {len(df)}")
        
        # 转换数据
        cooccurrences = []
        for _, row in df.iterrows():
            skill_1_id = int(row.iloc[0])
            skill_2_id = int(row.iloc[1])
            frequency = int(row.iloc[2])
            
            # 确保两个技能都存在
            if skill_1_id not in skill_mappings or skill_2_id not in skill_mappings:
                continue
            
            cooccurrences.append(SkillCooccurrence(
                skill_1_id=skill_1_id,
                skill_1_name=skill_mappings[skill_1_id],
                skill_2_id=skill_2_id,
                skill_2_name=skill_mappings[skill_2_id],
                frequency=frequency
            ))
        
        # 批量插入
        with transaction.atomic():
            SkillCooccurrence.objects.all().delete()  # 清空旧数据
            SkillCooccurrence.objects.bulk_create(cooccurrences, ignore_conflicts=True)
        
        print(f"✅ 导入了 {len(cooccurrences)} 条技能共现关系")
        return len(cooccurrences)
    
    def _extract_keyword(self, skill_name):
        """从技能名称提取本地关键词"""
        skill_lower = skill_name.lower()
        
        # 尝试匹配预定义的关键词
        for key, value in self.keyword_mapping.items():
            if key in skill_lower:
                return value
        
        # 如果没有匹配，返回原名称
        return skill_name


def run_import(dataset_path, granularity='l2', limit_skills=None):
    """
    运行导入
    
    参数:
        dataset_path: Job-SDF数据集路径
        granularity: 数据粒度 ('l1', 'l2', 'company', 'region')
        limit_skills: 限制导入的技能数量（None表示全部导入）
    """
    importer = JobSDFImporter(dataset_path)
    importer.import_all(granularity, limit_skills)


if __name__ == '__main__':
    # 测试导入
    import sys
    if len(sys.argv) < 2:
        print("用法: python import_job_sdf.py <数据集路径> [粒度] [技能数量限制]")
        print("示例: python import_job_sdf.py ./benchmark/dataset l2 100")
        sys.exit(1)
    
    dataset_path = sys.argv[1]
    granularity = sys.argv[2] if len(sys.argv) > 2 else 'l2'
    limit_skills = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    run_import(dataset_path, granularity, limit_skills)
