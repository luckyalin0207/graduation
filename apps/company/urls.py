from django.urls import path
from . import views

urlpatterns = [
    path('', views.company_verify_page, name='company_verify'),
    path('list/', views.company_list_page, name='company_list'),
    path('api/verify/', views.api_verify_company, name='api_verify_company'),
    path('api/batch/', views.api_batch_verify, name='api_batch_verify'),
    path('api/cached/', views.api_get_cached, name='api_get_cached'),
    path('api/list/', views.api_company_list, name='api_company_list'),
    path('api/config-status/', views.api_config_status, name='api_config_status'),
]
