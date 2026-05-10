from django.contrib import admin
from .models import CompanyVerification


@admin.register(CompanyVerification)
class CompanyVerificationAdmin(admin.ModelAdmin):
    list_display = [
        'company_name', 'unified_code', 'legal_person',
        'business_status', 'risk_level', 'source', 'status', 'verified_at',
    ]
    list_filter = ['status', 'risk_level', 'source', 'business_status']
    search_fields = ['company_name', 'unified_code', 'legal_person']
    readonly_fields = ['verified_at', 'created_at', 'raw_data']
    ordering = ['-verified_at']

    fieldsets = (
        ('基本信息', {
            'fields': ('company_name', 'unified_code', 'legal_person',
                       'registered_capital', 'establishment_date',
                       'business_status', 'company_type', 'industry')
        }),
        ('联系信息', {
            'fields': ('registered_address', 'phone', 'email', 'website')
        }),
        ('风险信息', {
            'fields': ('risk_level', 'risk_count', 'lawsuit_count', 'dishonest_count')
        }),
        ('元数据', {
            'fields': ('source', 'status', 'verified_at', 'created_at', 'raw_data'),
            'classes': ('collapse',),
        }),
    )
