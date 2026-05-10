from django.urls import path
from . import views

urlpatterns = [
    path('', views.recommend_page, name='recommend'),
    path('api/list/', views.get_recommend_list, name='get_recommend_list'),
]
