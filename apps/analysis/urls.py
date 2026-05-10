from django.urls import path
from . import views

urlpatterns = [
    path('', views.welcome, name='analysis_home'),  # 添加根路径，重定向到欢迎页面
    path('welcome/', views.welcome, name='welcome'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('api/edu/', views.get_edu_data, name='get_edu_data'),
    path('api/salary/', views.get_salary_data, name='get_salary_data'),
    path('api/city/', views.get_city_data, name='get_city_data'),
    path('api/keyword/', views.get_keyword_data, name='get_keyword_data'),
    path('api/exp_salary/', views.get_exp_salary_data, name='get_exp_salary_data'),
    path('api/company_type/', views.get_company_type_data, name='get_company_type_data'),
    # 新增功能
    path('job/', views.job_analysis, name='job_analysis'),
    path('api/job/edu/', views.get_job_type_edu, name='get_job_type_edu'),
    path('api/job/exp/', views.get_job_type_exp, name='get_job_type_exp'),
    path('api/job/salary/', views.get_job_type_salary, name='get_job_type_salary'),
    path('api/job/city/', views.get_job_type_city, name='get_job_type_city'),
    path('salary-map/', views.salary_map, name='salary_map'),
    path('api/salary-map/', views.get_salary_map_data, name='get_salary_map_data'),
    path('salary-predict/', views.salary_predict, name='salary_predict'),
    path('api/salary-predict/', views.do_salary_predict, name='do_salary_predict'),
    path('job-match/', views.job_match, name='job_match'),
    path('api/job-match/', views.do_job_match, name='do_job_match'),
    path('api/map/', views.get_map_data, name='get_map_data'),
    path('api/experience/', views.get_experience_data, name='get_experience_data'),
    path('api/scale/', views.get_scale_data, name='get_scale_data'),
    path('api/train-model/', views.train_salary_model, name='train_salary_model'),
    path('api/build-index/', views.build_job_index, name='build_job_index'),
    path('export/', views.export_analysis_data, name='export_analysis_data'),
    path('api/trend/', views.get_trend_data, name='get_trend_data'),
    path('trend-predict/', views.job_trend_predict, name='job_trend_predict'),
    path('api/trend-predict/', views.get_trend_predict_data, name='get_trend_predict_data'),
    # Job-SDF 历史数据 API（供所有分析页面使用）
    path('api/sdf/skill-trend/', views.get_sdf_skill_trend, name='get_sdf_skill_trend'),
    path('api/sdf/hot-skills/', views.get_sdf_hot_skills, name='get_sdf_hot_skills'),
    path('api/sdf/cooccurrence/', views.get_sdf_cooccurrence, name='get_sdf_cooccurrence'),
    path('api/sdf/salary-reference/', views.get_sdf_salary_reference, name='get_sdf_salary_reference'),
]
