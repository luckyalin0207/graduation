from django.contrib import admin
from .models import AgentReport, UserFeedback, LLMConfig


@admin.register(AgentReport)
class AgentReportAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'generated_at']
    list_filter = ['generated_at']
    search_fields = ['user_id']


@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'job_id', 'feedback_type', 'created_at']
    list_filter = ['feedback_type', 'created_at']
    search_fields = ['user_id', 'job_id']


@admin.register(LLMConfig)
class LLMConfigAdmin(admin.ModelAdmin):
    list_display = ['provider', 'model', 'enabled', 'updated_at']
    list_filter = ['provider', 'enabled']
    
    def has_add_permission(self, request):
        # 只允许有一个配置实例
        return not LLMConfig.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # 不允许删除配置
        return False

