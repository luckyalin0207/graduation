from django.apps import AppConfig
import os


class SpiderConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "spider"
    
    def ready(self):
        """应用就绪时启动定时任务调度器"""
        # 避免在migrate等命令时启动调度器
        if os.environ.get('RUN_MAIN') == 'true':
            # 重置可能因崩溃/重启遗留的"运行中"状态
            try:
                from .models import SpiderInfo
                SpiderInfo.objects.filter(status=1).update(status=0)
            except Exception:
                pass

            try:
                from .scheduler import start_scheduler
                start_scheduler()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"调度器启动失败（这在开发环境中是正常的）: {str(e)}")
