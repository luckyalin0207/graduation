from django.contrib import admin
from .models import JobData, SendList, UserExpect, FavoriteJob, UserExpectItem


@admin.register(JobData)
class JobDataAdmin(admin.ModelAdmin):
    list_display = ['job_id', 'name', 'salary', 'place', 'education', 'company', 'key_word', 'created_at']
    search_fields = ['name', 'company', 'place', 'key_word']
    list_filter = ['education', 'key_word', 'source', 'created_at']
    list_per_page = 20


@admin.register(SendList)
class SendListAdmin(admin.ModelAdmin):
    list_display = ['send_id', 'get_user_name', 'get_job_name', 'get_status_display', 'created_at']
    search_fields = ['user__user_name', 'job__name']
    list_filter = ['status', 'created_at']
    raw_id_fields = ['user', 'job']  # 使用原始ID字段，避免下拉框加载过多数据
    
    def get_user_name(self, obj):
        return obj.user.user_name if obj.user else '-'
    get_user_name.short_description = '用户'
    
    def get_job_name(self, obj):
        return obj.job.name if obj.job else '-'
    get_job_name.short_description = '职位'


@admin.register(UserExpect)
class UserExpectAdmin(admin.ModelAdmin):
    list_display = ['expect_id', 'get_user_name', 'key_word', 'place', 'salary_min', 'salary_max']
    search_fields = ['user__user_name', 'key_word', 'place']
    raw_id_fields = ['user']
    
    def get_user_name(self, obj):
        return obj.user.user_name if obj.user else '-'
    get_user_name.short_description = '用户'


@admin.register(UserExpectItem)
class UserExpectItemAdmin(admin.ModelAdmin):
    list_display = ['expect_item_id', 'get_user_name', 'key_word', 'place', 'salary_min', 'salary_max', 'updated_at']
    search_fields = ['user__user_name', 'key_word', 'place']
    raw_id_fields = ['user']
    
    def get_user_name(self, obj):
        return obj.user.user_name if obj.user else '-'
    get_user_name.short_description = '用户'


@admin.register(FavoriteJob)
class FavoriteJobAdmin(admin.ModelAdmin):
    list_display = ['favorite_id', 'get_user_name', 'get_job_name', 'created_at']
    search_fields = ['user__user_name', 'job__name']
    list_filter = ['created_at']
    raw_id_fields = ['user', 'job']
    
    def get_user_name(self, obj):
        return obj.user.user_name if obj.user else '-'
    get_user_name.short_description = '用户'
    
    def get_job_name(self, obj):
        return obj.job.name if obj.job else '-'
    get_job_name.short_description = '职位'
