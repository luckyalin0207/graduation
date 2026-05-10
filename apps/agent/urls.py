from django.urls import path
from . import views

urlpatterns = [
    path('', views.agent_dashboard, name='agent_dashboard'),
    path('chat/', views.agent_chat_page, name='agent_chat'),
    path('api/chat/', views.chat, name='agent_chat_api'),
    path('api/chat/history/', views.chat_history, name='agent_chat_history'),
    path('api/chat/clear/', views.clear_chat, name='agent_chat_clear'),
    path('api/notifications/', views.get_notifications, name='agent_notifications'),
    path('api/recommendations/', views.get_recommendations, name='get_recommendations'),
    path('api/report/', views.generate_report, name='generate_report'),
    path('api/suggestions/', views.get_apply_suggestions, name='get_apply_suggestions'),
    path('api/feedback/', views.submit_feedback, name='submit_feedback'),
    path('api/salary-prediction/', views.get_salary_prediction, name='agent_salary_prediction'),
    path('api/report-history/', views.get_report_history, name='get_report_history'),
    path('api/run-daily-task/', views.run_daily_task, name='run_daily_task'),
    path('api/debug/', views.debug_info, name='debug_info'),
    path('llm-config/', views.llm_config, name='llm_config'),
    path('api/test-llm/', views.test_llm_config, name='test_llm_config'),
]

