"""
智能求职助手Agent
自动搜集职位信息并为用户推荐合适的职位
"""
import logging
from datetime import datetime, timedelta
from django.db.models import Q
from jobs.models import JobData, UserExpect, SendList, FavoriteJob, UserExpectItem
from agent.models import UserFeedback
from users.models import UserList
from apps.analysis.ml_predictor import get_predictor
from apps.analysis.job_matcher import get_matcher
import json

logger = logging.getLogger(__name__)


class UserProfile:
    """用户画像"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.user = None
        self.expect = None
        self.skills = []
        self.preferences = {}
        self.history = []
        
        self._load_profile()
    
    def _load_profile(self):
        """加载用户画像"""
        try:
            self.user = UserList.objects.get(user_id=self.user_id)

            # 加载多条求职意向
            expect_items = list(UserExpectItem.objects.filter(user_id=self.user_id))
            if not expect_items:
                legacy = UserExpect.objects.filter(user_id=self.user_id).first()
                if legacy:
                    expect_items = [legacy]

            if expect_items:
                # 提取技能列表
                skills = []
                cities = []
                salary_mins = []
                salary_maxs = []
                for item in expect_items:
                    if getattr(item, 'key_word', None):
                        skills.extend([s.strip() for s in item.key_word.split(',') if s.strip()])
                    if getattr(item, 'place', None):
                        cities.extend([s.strip() for s in item.place.split(',') if s.strip()])
                    if getattr(item, 'salary_min', None):
                        salary_mins.append(float(item.salary_min))
                    if getattr(item, 'salary_max', None):
                        salary_maxs.append(float(item.salary_max))

                self.skills = list(dict.fromkeys(skills))
                self.preferences = {
                    'cities': list(dict.fromkeys(cities)),
                    'salary_min': min(salary_mins) if salary_mins else 0,
                    'salary_max': max(salary_maxs) if salary_maxs else 999,
                    'education': getattr(expect_items[0], 'education', '') or '',
                    'experience': getattr(expect_items[0], 'experience', '') or '',
                }
            else:
                logger.warning(f"用户 {self.user_id} 未设置求职意向")
            
            # 加载历史投递记录
            sent_jobs = SendList.objects.filter(user__user_id=self.user_id).order_by('-created_at')[:50]
            self.history = [
                {
                    'job_id': item.job.job_id,
                    'send_time': item.created_at,
                    'status': item.status
                }
                for item in sent_jobs
            ]
            
        except UserList.DoesNotExist:
            logger.error(f"用户 {self.user_id} 不存在")
    
    def get_sent_job_ids(self):
        """获取已投递的职位ID列表"""
        return [item['job_id'] for item in self.history]

    def get_excluded_job_ids(self):
        """获取需要排除的职位ID列表（已投递/不感兴趣/已收藏）"""
        excluded = set(self.get_sent_job_ids())
        try:
            negative_ids = UserFeedback.objects.filter(
                user_id=self.user_id, feedback_type='not_interested'
            ).values_list('job_id', flat=True)
            excluded.update(list(negative_ids))
        except Exception:
            pass
        try:
            favorite_ids = FavoriteJob.objects.filter(
                user_id=self.user_id
            ).values_list('job_id', flat=True)
            excluded.update(list(favorite_ids))
        except Exception:
            pass
        return list(excluded)
    
    def is_interested_in_city(self, city):
        """判断是否对某城市感兴趣"""
        if not self.preferences.get('cities'):
            return True
        return any(c in city for c in self.preferences['cities']) if city else False
    
    def is_salary_acceptable(self, salary_min, salary_max):
        """判断薪资是否可接受（放宽条件）"""
        if not salary_max:
            return True
        
        # 转换为float类型进行计算
        from decimal import Decimal
        
        user_min = float(self.preferences.get('salary_min', 0) or 0)
        user_max = float(self.preferences.get('salary_max', 999) or 999)
        job_min = float(salary_min) if salary_min else 0
        job_max = float(salary_max) if salary_max else 0
        
        # 放宽条件：
        # 1. 职位最高薪资 >= 用户期望最低薪资的80%
        # 2. 或者职位薪资范围与用户期望有重叠
        # 3. 或者职位最低薪资 <= 用户期望最高薪资的120%
        relaxed_min = user_min * 0.8
        relaxed_max = user_max * 1.2
        
        return (job_max >= relaxed_min) or \
               (job_min <= relaxed_max and job_max >= relaxed_min) or \
               (job_min <= user_max and job_max >= user_min)


class JobSearchAgent:
    """智能求职助手Agent"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.profile = UserProfile(user_id)
        self.ml_predictor = get_predictor()
        self.job_matcher = get_matcher()
        
        # 大模型服务（可选）
        try:
            from .llm_service import get_llm_service
            self.llm_service = get_llm_service()
        except Exception as e:
            logger.warning(f"大模型服务初始化失败: {str(e)}")
            self.llm_service = None
        
        # Agent状态
        self.recommended_jobs = []
        self.analysis_results = {}
    
    def search_jobs(self, limit=50):
        """搜索适合用户的职位"""
        logger.info(f"Agent开始为用户 {self.user_id} 搜索职位...")
        
        # 1. 基础过滤：排除已投递的职位
        excluded_job_ids = self.profile.get_excluded_job_ids()
        jobs = JobData.objects.exclude(job_id__in=excluded_job_ids)
        
        # 2. 根据用户意向过滤
        if self.profile.expect:
            # 技能关键词匹配
            if self.profile.skills:
                q = Q()
                for skill in self.profile.skills:
                    q |= Q(name__icontains=skill) | Q(key_word__icontains=skill)
                jobs = jobs.filter(q)
            
            # 城市过滤
            if self.profile.preferences.get('cities'):
                city_q = Q()
                for city in self.profile.preferences['cities']:
                    city_q |= Q(city__icontains=city) | Q(place__icontains=city)
                jobs = jobs.filter(city_q)
            
            # 薪资过滤（放宽条件：职位最高薪资 >= 用户最低薪资的80%）
            salary_min = self.profile.preferences.get('salary_min', 0)
            if salary_min:
                # 放宽到80%，避免过滤太严格
                relaxed_min = float(salary_min) * 0.8
                jobs = jobs.filter(salary_max__gte=relaxed_min)
        
        # 3. 限制数量并转为列表
        jobs = list(jobs[:500])  # 先取500个候选
        
        logger.info(f"找到 {len(jobs)} 个候选职位")
        
        return jobs
    
    def analyze_job(self, job):
        """分析单个职位并计算匹配度（支持大模型增强）"""
        # 如果大模型可用，优先使用大模型分析
        if self.llm_service and self.llm_service.enabled:
            llm_result = self._analyze_with_llm(job)
            if llm_result:
                return llm_result
        
        # 否则使用传统算法
        return self._analyze_with_traditional(job)
    
    def _analyze_with_llm(self, job):
        """使用大模型分析职位"""
        try:
            # 构建职位描述
            job_description = f"""
职位名称：{job.name}
公司：{job.company}
薪资：{job.salary}
城市：{job.city}
学历要求：{job.education or '不限'}
经验要求：{job.experience or '不限'}
关键词：{job.key_word or ''}
职位描述：{job.description or ''}
"""
            
            # 构建用户画像
            user_profile = {
                'skills': self.profile.skills,
                'cities': self.profile.preferences.get('cities', []),
                'salary_min': float(self.profile.preferences.get('salary_min', 0) or 0),
                'salary_max': float(self.profile.preferences.get('salary_max', 999) or 999),
                'education': self.profile.preferences.get('education', ''),
                'experience': self.profile.preferences.get('experience', '')
            }
            
            # 调用大模型分析
            result = self.llm_service.analyze_job_match(user_profile, job_description)
            
            if result and 'total_score' in result:
                return {
                    'score': min(100, int(result['total_score'])),
                    'reasons': result.get('match_reasons', []),
                    'llm_enhanced': True,
                    'improvement_suggestions': result.get('improvement_suggestions', [])
                }
        except Exception as e:
            logger.warning(f"大模型分析失败，回退到传统算法: {str(e)}")
        
        return None
    
    def _analyze_with_traditional(self, job):
        """使用传统算法分析职位"""
        score = 0
        reasons = []
        
        # 1. 技能匹配度 (0-40分)
        skill_match = 0
        if self.profile.skills:
            matched_skills = []
            for skill in self.profile.skills:
                if skill.lower() in (job.name or '').lower() or \
                   skill.lower() in (job.key_word or '').lower():
                    skill_match += 8
                    matched_skills.append(skill)
            
            skill_match = min(skill_match, 40)
            if matched_skills:
                reasons.append(f"技能匹配: {', '.join(matched_skills)}")
        
        score += skill_match
        
        # 2. 城市匹配度 (0-20分)
        if self.profile.is_interested_in_city(job.city):
            score += 20
            if self.profile.preferences.get('cities'):
                reasons.append(f"目标城市: {job.city}")
        
        # 3. 薪资匹配度 (0-30分)
        if job.salary_min and job.salary_max:
            if self.profile.is_salary_acceptable(job.salary_min, job.salary_max):
                # 计算薪资匹配度（转换为float进行计算）
                user_min = float(self.profile.preferences.get('salary_min', 0) or 0)
                user_max = float(self.profile.preferences.get('salary_max', 999) or 999)
                job_min = float(job.salary_min)
                job_max = float(job.salary_max)
                
                # 如果职位薪资在用户期望范围内，给满分
                if job_min >= user_min and job_max <= user_max:
                    salary_score = 30
                # 如果职位薪资高于用户期望，按超出比例扣分
                elif job_min > user_max:
                    # 超出太多，扣分
                    over_rate = (job_min - user_max) / max(user_max, 1)
                    salary_score = max(10, 30 - int(over_rate * 20))
                # 如果职位薪资低于用户期望，按低于比例扣分
                elif job_max < user_min:
                    # 低于太多，扣分
                    under_rate = (user_min - job_max) / max(user_min, 1)
                    salary_score = max(10, 30 - int(under_rate * 20))
                else:
                    # 有重叠，给较高分
                    overlap_min = max(job_min, user_min)
                    overlap_max = min(job_max, user_max)
                    overlap_rate = (overlap_max - overlap_min) / max(job_max - job_min, 1)
                    salary_score = 15 + int(overlap_rate * 15)
                
                score += salary_score
                reasons.append(f"薪资符合: {job.salary}")
            else:
                # 薪资不符合，但可以给少量分数（避免完全过滤掉）
                reasons.append(f"薪资略不符合: {job.salary}")
        
        # 4. 使用TF-IDF计算文本相似度 (0-10分)
        try:
            tfidf_score = 0
            if self.profile.skills:
                skills_text = ' '.join(self.profile.skills)
                results = self.job_matcher.match_jobs(
                    skills=skills_text,
                    city='',
                    salary_min=0,
                    top_k=1
                )
                if results and results[0]['job_id'] == job.job_id:
                    tfidf_score = min(10, results[0]['match_score'] / 10)
            score += tfidf_score
        except Exception as e:
            logger.warning(f"TF-IDF计算失败: {str(e)}")
        
        return {
            'score': min(100, int(score)),
            'reasons': reasons,
            'llm_enhanced': False
        }
    
    def recommend_jobs(self, limit=20, min_score=60):
        """推荐职位"""
        # 1. 搜索候选职位（限制100个，避免逐个分析500个导致超时）
        candidate_jobs = self.search_jobs(limit=100)
        
        if not candidate_jobs:
            logger.warning(f"未找到适合用户 {self.user_id} 的职位")
            # 如果严格条件找不到，尝试放宽条件
            if self.profile.expect:
                logger.info("尝试放宽搜索条件...")
                # 只按技能搜索，不限制城市和薪资
                jobs = JobData.objects.all()
                excluded_job_ids = self.profile.get_excluded_job_ids()
                if excluded_job_ids:
                    jobs = jobs.exclude(job_id__in=excluded_job_ids)
                
                if self.profile.skills:
                    q = Q()
                    for skill in self.profile.skills:
                        q |= Q(name__icontains=skill) | Q(key_word__icontains=skill)
                    jobs = jobs.filter(q)
                
                candidate_jobs = list(jobs[:100])
                logger.info(f"放宽条件后找到 {len(candidate_jobs)} 个候选职位")
        
        if not candidate_jobs:
            logger.warning(f"数据库中可能没有职位数据或条件过于严格")
            return []
        
        # 2. 分析并评分
        scored_jobs = []
        for job in candidate_jobs:
            analysis = self.analyze_job(job)
            
            if analysis['score'] >= min_score:
                scored_jobs.append({
                    'job': job,
                    'score': analysis['score'],
                    'reasons': analysis['reasons'],
                    'improvement_suggestions': analysis.get('improvement_suggestions', []),
                    'llm_enhanced': analysis.get('llm_enhanced', False),
                })
        
        # 如果按min_score找不到，降低阈值
        if not scored_jobs and min_score > 40:
            logger.info(f"未找到{min_score}分以上的职位，降低阈值到40分...")
            for job in candidate_jobs:
                analysis = self.analyze_job(job)
                if analysis['score'] >= 40:
                    scored_jobs.append({
                        'job': job,
                        'score': analysis['score'],
                        'reasons': analysis['reasons'],
                        'improvement_suggestions': analysis.get('improvement_suggestions', []),
                        'llm_enhanced': analysis.get('llm_enhanced', False),
                    })
        
        # 3. 按分数排序
        scored_jobs.sort(key=lambda x: x['score'], reverse=True)
        
        # 4. 取前N个
        self.recommended_jobs = scored_jobs[:limit]
        
        logger.info(f"为用户 {self.user_id} 推荐了 {len(self.recommended_jobs)} 个职位")
        
        return self.recommended_jobs
    
    def predict_salary_range(self):
        """预测用户的合理薪资范围"""
        if not self.profile.expect:
            return None
        
        try:
            predicted_salary, msg = self.ml_predictor.predict(
                city=self.profile.preferences.get('cities', [''])[0] if self.profile.preferences.get('cities') else '',
                education=self.profile.preferences.get('education', ''),
                experience=self.profile.preferences.get('experience', ''),
                job_type=self.profile.skills[0] if self.profile.skills else ''
            )
            
            if predicted_salary:
                lower, upper = self.ml_predictor.get_confidence_interval(
                    city=self.profile.preferences.get('cities', [''])[0] if self.profile.preferences.get('cities') else '',
                    education=self.profile.preferences.get('education', ''),
                    experience=self.profile.preferences.get('experience', ''),
                    job_type=self.profile.skills[0] if self.profile.skills else ''
                )
                
                return {
                    'predicted': round(predicted_salary, 2),
                    'lower': round(lower, 2) if lower else round(predicted_salary * 0.7, 2),
                    'upper': round(upper, 2) if upper else round(predicted_salary * 1.3, 2),
                    'message': msg
                }
        except Exception as e:
            logger.error(f"薪资预测失败: {str(e)}")
        
        return None
    
    def generate_report(self):
        """生成求职分析报告"""
        report = {
            'user_id': self.user_id,
            'generated_at': datetime.now().isoformat(),
            'profile': {
                'skills': self.profile.skills,
                'target_cities': self.profile.preferences.get('cities', []),
                'salary_range': [
                    self.profile.preferences.get('salary_min', 0),
                    self.profile.preferences.get('salary_max', 999)
                ],
                'applied_jobs': len(self.profile.history)
            },
            'market_analysis': {},
            'recommendations': [],
            'salary_prediction': None
        }
        
        # 薪资预测
        salary_pred = self.predict_salary_range()
        if salary_pred:
            report['salary_prediction'] = salary_pred
        
        # 推荐职位（限制数量，避免超时）
        if not self.recommended_jobs:
            self.recommend_jobs(limit=10, min_score=50)
        
        report['recommendations'] = [
            {
                'job_id': item['job'].job_id,
                'name': item['job'].name,
                'company': item['job'].company,
                'salary': item['job'].salary,
                'city': item['job'].city,
                'education': item['job'].education,
                'experience': item['job'].experience,
                'match_score': item['score'],
                'match_reasons': item['reasons']
            }
            for item in self.recommended_jobs[:10]
        ]
        
        # 市场分析
        if self.profile.skills:
            main_skill = self.profile.skills[0]
            market_jobs = JobData.objects.filter(
                Q(name__icontains=main_skill) | Q(key_word__icontains=main_skill)
            ).exclude(salary_max__isnull=True)
            
            if market_jobs.exists():
                from django.db.models import Avg, Count
                
                report['market_analysis'] = {
                    'skill': main_skill,
                    'total_jobs': market_jobs.count(),
                    'avg_salary': round(market_jobs.aggregate(avg=Avg('salary_max'))['avg'], 2),
                    'top_cities': list(
                        market_jobs.values('city').annotate(count=Count('job_id'))
                        .order_by('-count')[:5].values_list('city', flat=True)
                    )
                }
        
        return report
    
    def auto_apply_suggestions(self):
        """智能申请建议（支持大模型增强）"""
        if not self.recommended_jobs:
            self.recommend_jobs()
        
        suggestions = []
        
        for item in self.recommended_jobs[:5]:
            job = item['job']
            score = item['score']
            
            suggestion = {
                'job': {
                    'id': job.job_id,
                    'name': job.name,
                    'company': job.company,
                },
                'priority': 'high' if score >= 85 else 'medium' if score >= 70 else 'low',
                'action': 'apply' if score >= 80 else 'review',
                'tips': []
            }
            
            # 如果大模型可用，使用大模型生成建议
            if self.llm_service and self.llm_service.enabled:
                try:
                    job_description = f"职位：{job.name}，公司：{job.company}，薪资：{job.salary}，城市：{job.city}"
                    user_profile = {
                        'skills': self.profile.skills,
                        'salary_min': float(self.profile.preferences.get('salary_min', 0) or 0),
                        'salary_max': float(self.profile.preferences.get('salary_max', 999) or 999)
                    }
                    
                    llm_result = self.llm_service.generate_apply_suggestions(user_profile, job_description)
                    if llm_result:
                        suggestion['priority'] = llm_result.get('priority', suggestion['priority'])
                        suggestion['action'] = llm_result.get('action', suggestion['action'])
                        suggestion['tips'] = llm_result.get('tips', suggestion['tips'])
                        suggestion['llm_enhanced'] = True
                except Exception as e:
                    logger.warning(f"大模型生成建议失败: {str(e)}")
            
            # 如果没有大模型或大模型失败，使用规则生成建议
            if not suggestion.get('tips'):
                if score >= 90:
                    suggestion['tips'].append("强烈推荐！高度匹配您的技能和期望")
                
                if job.salary_max and self.profile.preferences.get('salary_max'):
                    if float(job.salary_max) > float(self.profile.preferences['salary_max']) * 1.2:
                        suggestion['tips'].append("薪资高于预期，可积极争取")
                
                if self.profile.preferences.get('education'):
                    if self.profile.preferences['education'] in ['本科', '硕士', '博士']:
                        suggestion['tips'].append("学历要求匹配，申请成功率较高")
            
            suggestions.append(suggestion)
        
        return suggestions


class AgentScheduler:
    """Agent调度器 - 自动化运行Agent任务"""
    
    @staticmethod
    def run_daily_recommendations():
        """每日推荐任务"""
        logger.info("开始执行每日求职推荐任务...")
        
        # 获取所有有求职意向的用户
        user_expects = UserExpect.objects.all()
        
        results = []
        for expect in user_expects:
            try:
                # 为每个用户创建Agent
                agent = JobSearchAgent(expect.user_id)
                
                # 生成推荐
                recommendations = agent.recommend_jobs(limit=10, min_score=70)
                
                # 如果有推荐，发送邮件
                if recommendations:
                    from apps.spider.email_service import EmailService
                    
                    user = UserList.objects.get(user_id=expect.user_id)
                    jobs = [item['job'] for item in recommendations]
                    
                    EmailService.send_job_recommendation(user, jobs)
                    
                    results.append({
                        'user_id': expect.user_id,
                        'recommended': len(recommendations),
                        'status': 'success'
                    })
                else:
                    results.append({
                        'user_id': expect.user_id,
                        'recommended': 0,
                        'status': 'no_match'
                    })
            
            except Exception as e:
                logger.error(f"处理用户 {expect.user_id} 时出错: {str(e)}")
                results.append({
                    'user_id': expect.user_id,
                    'status': 'error',
                    'error': str(e)
                })
        
        logger.info(f"每日推荐任务完成，处理了 {len(results)} 个用户")
        return results
    
    @staticmethod
    def update_all_user_profiles():
        """更新所有用户画像"""
        logger.info("开始更新用户画像...")
        
        users = UserList.objects.all()
        for user in users:
            try:
                profile = UserProfile(user.user_id)
                # 这里可以添加用户行为分析、偏好学习等逻辑
                logger.info(f"更新用户 {user.user_id} 画像成功")
            except Exception as e:
                logger.error(f"更新用户 {user.user_id} 画像失败: {str(e)}")


def get_agent(user_id):
    """获取用户的求职助手Agent"""
    return JobSearchAgent(user_id)

