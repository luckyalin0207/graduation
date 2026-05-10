from django.contrib import admin
from .models import SpiderInfo


@admin.register(SpiderInfo)
class SpiderInfoAdmin(admin.ModelAdmin):
    list_display = ['spider_id', 'spider_name', 'target_site', 'status', 'total_count', 'run_count', 'last_run_time']
    list_filter = ['status']
