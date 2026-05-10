"""
智能职位匹配模块
使用 TF-IDF 和余弦相似度进行职位匹配
"""
import jieba
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from jobs.models import JobData
import pickle
import os
from django.conf import settings


class JobMatcher:
    """职位匹配器"""
    
    def __init__(self):
        self.vectorizer = None
        self.job_vectors = None
        self.job_ids = []
        self.job_data = []
        self.model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'job_matcher.pkl')
        
        # 确保模型目录存在
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        # 加载自定义词典（可选）
        self._load_custom_dict()
    
    def _load_custom_dict(self):
        """加载自定义技术词典"""
        tech_words = [
            'Python', 'Java', 'JavaScript', 'C++', 'Go', 'Rust', 'PHP', 'Ruby',
            'Django', 'Flask', 'Spring', 'Vue', 'React', 'Angular', 'Node.js',
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch',
            'Docker', 'Kubernetes', 'Linux', 'Git', 'Jenkins', 'CI/CD',
            '机器学习', '深度学习', '数据分析', '数据挖掘', '自然语言处理',
            '计算机视觉', '推荐系统', '搜索引擎', '大数据', '云计算',
            '前端', '后端', '全栈', '测试', '运维', '架构师', '算法',
        ]
        for word in tech_words:
            jieba.add_word(word)
    
    def _preprocess_text(self, text):
        """文本预处理：分词"""
        if not text:
            return ''
        # 使用jieba分词
        words = jieba.cut(str(text))
        return ' '.join(words)
    
    def build_index(self, jobs_queryset=None):
        """构建职位索引"""
        if jobs_queryset is None:
            jobs_queryset = JobData.objects.all()
        
        if jobs_queryset.count() == 0:
            return False, "没有职位数据"
        
        # 收集职位数据
        self.job_ids = []
        self.job_data = []
        texts = []
        
        for job in jobs_queryset[:5000]:  # 限制数量避免内存问题
            # 组合职位名称、关键词、公司等信息作为文本
            text_parts = [
                job.name or '',
                job.key_word or '',
                job.education or '',
                job.experience or '',
                job.city or '',
            ]
            text = ' '.join(text_parts)
            processed_text = self._preprocess_text(text)
            
            texts.append(processed_text)
            self.job_ids.append(job.job_id)
            self.job_data.append({
                'job_id': job.job_id,
                'name': job.name,
                'company': job.company,
                'salary': job.salary,
                'city': job.city,
                'education': job.education,
                'experience': job.experience,
                'key_word': job.key_word,
                'salary_min': float(job.salary_min) if job.salary_min else None,
                'salary_max': float(job.salary_max) if job.salary_max else None,
            })
        
        # 构建TF-IDF向量
        self.vectorizer = TfidfVectorizer(max_features=500, min_df=1)
        self.job_vectors = self.vectorizer.fit_transform(texts)
        
        # 保存模型
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'vectorizer': self.vectorizer,
                    'job_vectors': self.job_vectors,
                    'job_ids': self.job_ids,
                    'job_data': self.job_data
                }, f)
        except Exception as e:
            return False, f"索引保存失败: {str(e)}"
        
        return True, f"成功索引 {len(self.job_ids)} 个职位"
    
    def load_index(self):
        """加载已构建的索引"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.vectorizer = data['vectorizer']
                    self.job_vectors = data['job_vectors']
                    self.job_ids = data['job_ids']
                    self.job_data = data['job_data']
                return True
        except Exception:
            pass
        return False
    
    def match_jobs(self, skills='', city='', salary_min=0, education='', experience='', top_k=20):
        """匹配职位"""
        # 确保索引已加载
        if self.vectorizer is None or self.job_vectors is None:
            if not self.load_index():
                # 如果没有索引，构建一个
                success, msg = self.build_index()
                if not success:
                    return []
        
        # 构建查询向量
        query_parts = []
        if skills:
            query_parts.append(skills)
        if city:
            query_parts.append(city)
        if education:
            query_parts.append(education)
        if experience:
            query_parts.append(experience)
        
        query_text = ' '.join(query_parts)
        processed_query = self._preprocess_text(query_text)
        
        if not processed_query:
            # 如果没有查询词，返回高薪职位
            results = sorted(self.job_data, 
                           key=lambda x: x['salary_max'] if x['salary_max'] else 0, 
                           reverse=True)[:top_k]
            for job in results:
                job['match_score'] = 70 + np.random.randint(0, 20)
            return results
        
        # 计算相似度
        try:
            query_vector = self.vectorizer.transform([processed_query])
            similarities = cosine_similarity(query_vector, self.job_vectors)[0]
        except Exception:
            # 如果计算失败，返回随机结果
            return []
        
        # 应用过滤条件
        filtered_results = []
        for idx, sim_score in enumerate(similarities):
            job = self.job_data[idx]
            
            # 城市过滤
            if city and job['city']:
                if city not in job['city']:
                    continue
            
            # 薪资过滤
            if salary_min > 0 and job['salary_max']:
                if job['salary_max'] < salary_min:
                    continue
            
            # 学历过滤（可选）
            # if education and job['education']:
            #     if education not in job['education']:
            #         continue
            
            # 计算匹配分数（0-100）
            match_score = int(sim_score * 100)
            
            # 如果有技能匹配，额外加分
            if skills:
                skill_list = [s.strip() for s in skills.split(',')]
                for skill in skill_list:
                    if skill and job['name'] and skill.lower() in job['name'].lower():
                        match_score = min(100, match_score + 5)
                    if skill and job['key_word'] and skill.lower() in job['key_word'].lower():
                        match_score = min(100, match_score + 5)
            
            job_result = job.copy()
            job_result['match_score'] = match_score
            filtered_results.append(job_result)
        
        # 按匹配分数排序
        filtered_results.sort(key=lambda x: x['match_score'], reverse=True)
        
        return filtered_results[:top_k]


# 全局匹配器实例
_matcher = None

def get_matcher():
    """获取匹配器单例"""
    global _matcher
    if _matcher is None:
        _matcher = JobMatcher()
    return _matcher

