from django.urls import path
from . import views

urlpatterns = [
    path('', views.spider_manage, name='spider_manage'),
    path('api/status/', views.get_spider_status, name='get_spider_status'),
    path('api/mode/', views.get_spider_mode, name='get_spider_mode'),
    path('api/start/', views.start_spider, name='start_spider'),
    path('api/scheduler/', views.scheduler_status, name='scheduler_status'),
    path('api/start-boss/', views.start_boss_spider, name='start_boss_spider'),
    path('api/source-stats/', views.get_source_stats, name='get_source_stats'),
    path('api/open-boss-browser/', views.open_boss_browser, name='open_boss_browser'),
    path('api/debug-boss/', views.debug_boss_spider, name='debug_boss_spider'),
    path('import/', views.import_csv, name='import_csv'),
]
