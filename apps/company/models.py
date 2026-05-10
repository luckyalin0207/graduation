from django.db import models


class CompanyVerification(models.Model):
    """企业信息验证缓存表"""

    STATUS_CHOICES = [
        ('verified', '已验证'),
        ('not_found', '未找到'),
        ('error', '查询失败'),
        ('pending', '待验证'),
    ]

    SOURCE_CHOICES = [
        ('aiqicha', '爱企查'),
        ('tianyancha', '天眼查'),
        ('qichacha', '企查查'),
        ('gsxt', '国家企业信用信息公示系统'),
        ('manual', '手动录入'),
    ]

    company_name = models.CharField('公司名称', max_length=255, db_index=True)
    unified_code = models.CharField('统一社会信用代码', max_length=50, blank=True, null=True)
    legal_person = models.CharField('法定代表人', max_length=100, blank=True, null=True)
    registered_capital = models.CharField('注册资本', max_length=100, blank=True, null=True)
    establishment_date = models.CharField('成立日期', max_length=50, blank=True, null=True)
    business_status = models.CharField('经营状态', max_length=50, blank=True, null=True)
    registered_address = models.CharField('注册地址', max_length=500, blank=True, null=True)
    business_scope = models.TextField('经营范围', blank=True, null=True)
    company_type = models.CharField('企业类型', max_length=100, blank=True, null=True)
    industry = models.CharField('所属行业', max_length=100, blank=True, null=True)
    staff_size = models.CharField('人员规模', max_length=50, blank=True, null=True)
    phone = models.CharField('联系电话', max_length=50, blank=True, null=True)
    email = models.CharField('联系邮箱', max_length=100, blank=True, null=True)
    website = models.CharField('官网', max_length=255, blank=True, null=True)

    # 风险信息
    risk_count = models.IntegerField('风险数量', default=0)
    lawsuit_count = models.IntegerField('司法案件数', default=0)
    dishonest_count = models.IntegerField('失信记录数', default=0)
    risk_level = models.CharField('风险等级', max_length=20, default='未知',
                                   choices=[('低', '低风险'), ('中', '中风险'), ('高', '高风险'), ('未知', '未知')])

    # 元数据
    source = models.CharField('数据来源', max_length=20, choices=SOURCE_CHOICES, default='aiqicha')
    status = models.CharField('验证状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    raw_data = models.JSONField('原始数据', blank=True, null=True)
    verified_at = models.DateTimeField('验证时间', auto_now=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'company_verification'
        verbose_name = '企业验证信息'
        verbose_name_plural = verbose_name
        ordering = ['-verified_at']
        indexes = [
            models.Index(fields=['company_name']),
            models.Index(fields=['unified_code']),
        ]

    def __str__(self):
        return f"{self.company_name} [{self.get_status_display()}]"

    @property
    def is_normal(self):
        """经营状态是否正常"""
        return self.business_status in ['存续', '正常', '开业', '在营']

    @property
    def risk_summary(self):
        """风险摘要"""
        total = self.risk_count + self.lawsuit_count + self.dishonest_count
        if total == 0:
            return '暂无风险记录'
        parts = []
        if self.risk_count:
            parts.append(f'{self.risk_count}条风险')
        if self.lawsuit_count:
            parts.append(f'{self.lawsuit_count}条司法案件')
        if self.dishonest_count:
            parts.append(f'{self.dishonest_count}条失信记录')
        return '、'.join(parts)
