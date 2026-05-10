from django.db import models


class ChatSession(models.Model):
    """对话会话历史"""
    user_id = models.CharField(max_length=20, db_index=True)
    role = models.CharField(max_length=10)   # user / assistant
    content = models.TextField()
    intent = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_session'
        ordering = ['created_at']
        indexes = [models.Index(fields=['user_id', 'created_at'])]


class JobNotification(models.Model):
    """职位匹配通知"""
    user_id = models.CharField(max_length=20, db_index=True)
    job = models.ForeignKey('jobs.JobData', on_delete=models.CASCADE)
    match_score = models.IntegerField(default=0)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'job_notification'
        ordering = ['-created_at']
        unique_together = ['user_id', 'job']


class AgentReport(models.Model):
    """Agent分析报告"""
    user_id = models.CharField(max_length=20, verbose_name="用户ID")
    report_data = models.JSONField(verbose_name="报告数据")
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name="生成时间")

    class Meta:
        db_table = "agent_report"
        verbose_name = "Agent报告"
        verbose_name_plural = verbose_name
        ordering = ['-generated_at']


class UserFeedback(models.Model):
    """用户反馈"""
    user_id = models.CharField(max_length=20, verbose_name="用户ID")
    job_id = models.CharField(max_length=50, verbose_name="职位ID")
    feedback_type = models.CharField(max_length=20, verbose_name="反馈类型")  # interested, not_interested, applied
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="反馈时间")

    class Meta:
        db_table = "user_feedback"
        verbose_name = "用户反馈"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']


class LLMConfig(models.Model):
    """大模型配置（全局配置，单例模式）"""
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI (GPT)'),
        ('claude', 'Claude (Anthropic)'),
        ('wenxin', '文心一言 (百度)'),
        ('none', '不使用大模型'),
    ]

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='none', verbose_name="提供商")
    api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="API Key")
    secret_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="Secret Key（文心一言）")
    model = models.CharField(max_length=100, default='gpt-3.5-turbo', verbose_name="模型名称")
    base_url = models.CharField(max_length=255, blank=True, null=True, verbose_name="Base URL（可选，用于代理）")
    enabled = models.BooleanField(default=False, verbose_name="是否启用")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "llm_config"
        verbose_name = "大模型配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.get_provider_display()} - {self.model}"

    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
