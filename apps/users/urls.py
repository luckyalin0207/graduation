from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),
    path('user_info/', views.user_info, name='user_info'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('api/upload-resume/', views.upload_resume, name='upload_resume'),
    path('api/resume-info/', views.get_resume_info, name='get_resume_info'),
    path('api/resume-summary/', views.get_resume_summary, name='get_resume_summary'),
    path('api/resume-match/', views.resume_match_jobs, name='resume_match_jobs'),
    path('api/resume-score/', views.resume_score, name='resume_score'),
    path('api/resume-download/', views.resume_download, name='resume_download'),
]
