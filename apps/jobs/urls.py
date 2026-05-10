from django.urls import path
from django.shortcuts import render
from . import views

urlpatterns = [
    path('', views.index, name='job_home'),
    path('index/', views.index, name='index'),
    path('list/', views.job_list, name='job_list'),
    path('api/list/', views.get_job_list, name='get_job_list'),
    path('api/detail/<int:job_id>/', views.get_job_detail, name='get_job_detail'),
    path('api/compare/', views.compare_jobs, name='compare_jobs'),
    path('api/funnel/', views.send_funnel, name='send_funnel'),
    path('kanban/', views.kanban, name='kanban'),
    path('kanban/test/', lambda request: render(request, 'jobs/kanban_test.html'), name='kanban_test'),
    path('api/kanban/', views.get_kanban_data, name='get_kanban_data'),
    path('api/kanban/move/', views.move_kanban_card, name='move_kanban_card'),
    path('send/', views.send_job, name='send_job'),
    path('favorite/', views.favorite_job, name='favorite_job'),
    path('my_send/', views.my_send_list, name='my_send_list'),
    path('api/my_send/', views.get_my_send_list, name='get_my_send_list'),
    path('api/send_status/', views.update_send_status, name='update_send_status'),
    path('my_favorite/', views.my_favorite_list, name='my_favorite_list'),
    path('api/my_favorite/', views.get_my_favorite_list, name='get_my_favorite_list'),
    path('expect/', views.job_expect, name='job_expect'),
]
