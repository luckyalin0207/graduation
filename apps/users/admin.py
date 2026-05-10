from django.contrib import admin
from .models import UserList


@admin.register(UserList)
class UserListAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'user_name', 'email', 'phone', 'created_at']
    search_fields = ['user_id', 'user_name', 'email']
    list_filter = ['created_at']
