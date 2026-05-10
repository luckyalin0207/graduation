"""
大模型服务模块
支持多种大模型API（OpenAI、Claude、文心一言等）
"""
import logging
import json
from django.conf import settings

logger = logging.getLogger(__name__)


class LLMService:
    """大模型服务基类"""
    
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or getattr(settings, 'LLM_API_KEY', None)
        self.model = model or getattr(settings, 'LLM_MODEL', 'gpt-3.5-turbo')
        self.enabled = bool(self.api_key)
    
    def analyze_job_match(self, user_profile, job_description):
        """分析职位匹配度（大模型增强）"""
        if not self.enabled:
            return None
        
        try:
            prompt = self._build_match_prompt(user_profile, job_description)
            response = self._call_api(prompt)
            return self._parse_match_response(response)
        except Exception as e:
            logger.error(f"大模型分析失败: {str(e)}")
            return None
    
    def generate_apply_suggestions(self, user_profile, job_description):
        """生成申请建议（大模型增强）"""
        if not self.enabled:
            return None
        
        try:
            prompt = self._build_suggestion_prompt(user_profile, job_description)
            response = self._call_api(prompt)
            return self._parse_suggestion_response(response)
        except Exception as e:
            logger.error(f"大模型生成建议失败: {str(e)}")
            return None
    
    def optimize_resume(self, resume_text, job_description):
        """优化简历（大模型增强）"""
        if not self.enabled:
            return None
        
        try:
            prompt = self._build_resume_prompt(resume_text, job_description)
            response = self._call_api(prompt)
            return self._parse_resume_response(response)
        except Exception as e:
            logger.error(f"大模型优化简历失败: {str(e)}")
            return None
    
    def _build_match_prompt(self, user_profile, job_description):
        """构建匹配分析提示词"""
        return f"""你是一个专业的招聘顾问。请分析以下求职者与职位的匹配度。

求职者信息：
- 技能：{', '.join(user_profile.get('skills', []))}
- 期望城市：{', '.join(user_profile.get('cities', []))}
- 期望薪资：{user_profile.get('salary_min', 0)}K - {user_profile.get('salary_max', 999)}K
- 学历：{user_profile.get('education', '不限')}
- 经验：{user_profile.get('experience', '不限')}

职位信息：
{job_description}

请从以下维度分析匹配度（0-100分）：
1. 技能匹配度（40分）
2. 城市匹配度（20分）
3. 薪资匹配度（20分）
4. 综合匹配度（20分）

请以JSON格式返回：
{{
    "total_score": 85,
    "skill_score": 35,
    "city_score": 20,
    "salary_score": 18,
    "comprehensive_score": 12,
    "match_reasons": ["技能高度匹配", "目标城市", "薪资符合期望"],
    "improvement_suggestions": ["可以突出Python项目经验", "强调Django框架使用"]
}}
"""
    
    def _build_suggestion_prompt(self, user_profile, job_description):
        """构建申请建议提示词"""
        return f"""你是一个专业的职业规划师。请为求职者提供申请建议。

求职者信息：
- 技能：{', '.join(user_profile.get('skills', []))}
- 期望薪资：{user_profile.get('salary_min', 0)}K - {user_profile.get('salary_max', 999)}K

职位信息：
{job_description}

请提供：
1. 申请优先级（high/medium/low）
2. 是否建议立即申请（apply/review）
3. 申请建议和技巧（3-5条）

请以JSON格式返回：
{{
    "priority": "high",
    "action": "apply",
    "tips": [
        "强烈推荐！技能高度匹配",
        "薪资高于预期，可积极争取",
        "建议突出Python和Django项目经验"
    ]
}}
"""
    
    def _build_resume_prompt(self, resume_text, job_description):
        """构建简历优化提示词"""
        return f"""你是一个专业的简历优化顾问。请优化以下简历以匹配目标职位。

目标职位：
{job_description}

当前简历：
{resume_text[:2000]}  # 限制长度

请提供优化建议，以JSON格式返回：
{{
    "optimized_sections": {{
        "summary": "优化后的个人简介",
        "skills": ["技能1", "技能2"],
        "experience": "优化后的工作经历描述"
    }},
    "suggestions": [
        "建议1",
        "建议2"
    ]
}}
"""
    
    def _call_api(self, prompt):
        """调用大模型API（子类实现）"""
        raise NotImplementedError
    
    def _parse_match_response(self, response):
        """解析匹配分析响应"""
        try:
            # 尝试提取JSON
            if isinstance(response, str):
                # 提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            return response if isinstance(response, dict) else None
        except Exception as e:
            logger.error(f"解析响应失败: {str(e)}")
            return None
    
    def _parse_suggestion_response(self, response):
        """解析建议响应"""
        return self._parse_match_response(response)
    
    def _parse_resume_response(self, response):
        """解析简历优化响应"""
        return self._parse_match_response(response)


class OpenAIService(LLMService):
    """OpenAI服务（GPT模型）"""

    # anyrouter.top 实际可用的模型降级列表
    FALLBACK_MODELS = [
        'gpt-3.5-turbo',                  # OpenAI官方模型（优先）
        'gpt-4o-mini',                    # OpenAI官方模型
        'claude-3-5-haiku-20241022',      # Claude模型（需要特定API）
        'claude-3-5-sonnet-20241022',     # Claude模型
        'claude-sonnet-4-20250514',       # Claude模型
    ]

    def __init__(self, api_key=None, model='gpt-3.5-turbo', base_url=None):
        super().__init__(api_key, model)
        self.base_url = base_url or getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.base_url = self.base_url.rstrip('/')
        self._working_model = None  # 缓存已验证可用的模型

    def _call_api(self, prompt):
        """调用 OpenAI 兼容 API，自动降级到可用模型"""
        import requests

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        # 优先用上次验证可用的模型
        models_to_try = []
        if self._working_model:
            models_to_try.append(self._working_model)
        models_to_try.append(self.model)
        for m in self.FALLBACK_MODELS:
            if m not in models_to_try:
                models_to_try.append(m)

        for model in models_to_try:
            try:
                data = {
                    'model': model,
                    'messages': [
                        {'role': 'system', 'content': '你是一个专业的招聘顾问和职业规划师。'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.7,
                    'max_tokens': 1000
                }
                response = requests.post(
                    f'{self.base_url}/chat/completions',
                    headers=headers, json=data, timeout=30
                )
                if response.status_code == 200:
                    self._working_model = model  # 缓存可用模型
                    if model != self.model:
                        logger.info(f'[LLM] 使用降级模型: {model}')
                    return response.json()['choices'][0]['message']['content']
                elif response.status_code == 404:
                    logger.debug(f'[LLM] 模型 {model} 不可用，尝试下一个')
                    continue
                else:
                    logger.warning(f'[LLM] API返回 {response.status_code}，跳过')
                    continue
            except Exception as e:
                logger.debug(f'调用 {model} 失败: {e}')
                continue

        # 所有模型不可用时只打印一次 warning，不打印 ERROR
        logger.warning('[LLM] API 不可用，将使用规则兜底')
        return None


class ClaudeService(LLMService):
    """Claude服务（Anthropic）"""
    
    def __init__(self, api_key=None, model='claude-3-sonnet-20240229'):
        if api_key is None:
            api_key = getattr(settings, 'CLAUDE_API_KEY', None) or getattr(settings, 'LLM_API_KEY', None)
        super().__init__(api_key, model)
    
    def _call_api(self, prompt):
        """调用Claude API"""
        try:
            import requests
            
            headers = {
                'x-api-key': self.api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.model,
                'max_tokens': 1000,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ]
            }
            
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['content'][0]['text']
            else:
                logger.error(f"Claude API错误: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"调用Claude API失败: {str(e)}")
            return None


class WenxinService(LLMService):
    """文心一言服务（百度）"""
    
    def __init__(self, api_key=None, secret_key=None, model='ernie-bot-turbo'):
        if api_key is None:
            api_key = getattr(settings, 'LLM_API_KEY', None)
        super().__init__(api_key, model)
        self.secret_key = secret_key or getattr(settings, 'WENXIN_SECRET_KEY', None)
        self.access_token = None
        if self.api_key and self.secret_key:
            self._get_access_token()
    
    def _get_access_token(self):
        """获取访问令牌"""
        try:
            import requests
            
            url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.api_key}&client_secret={self.secret_key}"
            response = requests.post(url, timeout=10)
            
            if response.status_code == 200:
                self.access_token = response.json().get('access_token')
            else:
                logger.error(f"获取文心一言token失败: {response.text}")
        except Exception as e:
            logger.error(f"获取文心一言token失败: {str(e)}")
    
    def _call_api(self, prompt):
        """调用文心一言API"""
        if not self.access_token:
            self._get_access_token()
        
        if not self.access_token:
            return None
        
        try:
            import requests
            
            url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{self.model}?access_token={self.access_token}"
            
            data = {
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('result', '')
            else:
                logger.error(f"文心一言API错误: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"调用文心一言API失败: {str(e)}")
            return None


def get_llm_service():
    """获取大模型服务实例（优先从数据库读取配置）"""
    try:
        from .models import LLMConfig
        config = LLMConfig.get_config()
        
        # 如果数据库中有配置且已启用，优先使用数据库配置
        if config.enabled and config.provider != 'none':
            provider = config.provider.lower()
            api_key = config.api_key
            model = config.model
            base_url = config.base_url
            secret_key = config.secret_key
            
            if provider == 'openai':
                service = OpenAIService(api_key=api_key, model=model, base_url=base_url)
                return service if service.enabled else None
            elif provider == 'claude':
                return ClaudeService(api_key=api_key, model=model) if api_key else None
            elif provider == 'wenxin':
                return WenxinService(api_key=api_key, secret_key=secret_key, model=model) if (api_key and secret_key) else None
    except Exception as e:
        logger.warning(f"从数据库读取配置失败，使用settings配置: {str(e)}")
    
    # 回退到settings.py配置
    provider = getattr(settings, 'LLM_PROVIDER', 'openai').lower()
    
    if provider == 'openai':
        return OpenAIService()
    elif provider == 'claude':
        return ClaudeService()
    elif provider == 'wenxin':
        return WenxinService()
    else:
        # 默认返回OpenAI，如果没有配置则返回None
        service = OpenAIService()
        return service if service.enabled else None

