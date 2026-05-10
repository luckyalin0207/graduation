from django.db import models


class JobData(models.Model):
    """招聘职位信息表"""
    job_id = models.AutoField('职位ID', primary_key=True)
    name = models.CharField('职位名称', max_length=255)
    salary = models.CharField('薪资范围', max_length=100, blank=True, null=True)
    salary_min = models.DecimalField('最低薪资', max_digits=10, decimal_places=2, blank=True, null=True, db_index=True)
    salary_max = models.DecimalField('最高薪资', max_digits=10, decimal_places=2, blank=True, null=True, db_index=True)
    place = models.CharField('工作地点', max_length=100, blank=True, null=True, db_index=True)
    city = models.CharField('城市', max_length=50, blank=True, null=True, db_index=True)
    education = models.CharField('学历要求', max_length=50, blank=True, null=True, db_index=True)
    experience = models.CharField('工作经验', max_length=100, blank=True, null=True, db_index=True)
    company = models.CharField('公司名称', max_length=255, blank=True, null=True, db_index=True)
    company_type = models.CharField('公司类型', max_length=100, blank=True, null=True, db_index=True)
    scale = models.CharField('公司规模', max_length=100, blank=True, null=True, db_index=True)
    industry = models.CharField('所属行业', max_length=100, blank=True, null=True, db_index=True)
    label = models.CharField('职位标签', max_length=500, blank=True, null=True)
    description = models.TextField('职位描述', blank=True, null=True)
    href = models.CharField('原始链接', max_length=500, blank=True, null=True)
    key_word = models.CharField('搜索关键词', max_length=100, blank=True, null=True, db_index=True)
    source = models.CharField('数据来源', max_length=50, default='前程无忧')
    created_at = models.DateTimeField('爬取时间', auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'job_data'
        verbose_name = '招聘信息'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.company}"


class SendList(models.Model):
    """简历投递记录表"""
    STATUS_CHOICES = [
        (0, '已投递'),
        (1, '已查看'),
        (2, '邀请面试'),
        (3, '不合适'),
        (4, '已Offer'),
    ]
    
    send_id = models.AutoField('投递ID', primary_key=True)
    user = models.ForeignKey('users.UserList', on_delete=models.CASCADE, verbose_name='用户')
    job = models.ForeignKey(JobData, on_delete=models.CASCADE, verbose_name='职位')
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=0)
    cover_letter = models.TextField('求职信', blank=True, null=True)
    email_sent = models.BooleanField('是否已发邮件', default=False)
    created_at = models.DateTimeField('投递时间', auto_now_add=True)

    class Meta:
        db_table = 'send_list'
        verbose_name = '投递记录'
        verbose_name_plural = verbose_name
        unique_together = ['user', 'job']

    def __str__(self):
        return f"{self.user.user_name} - {self.job.name}"


class FavoriteJob(models.Model):
    """职位收藏"""
    favorite_id = models.AutoField('收藏ID', primary_key=True)
    user = models.ForeignKey('users.UserList', on_delete=models.CASCADE, verbose_name='用户')
    job = models.ForeignKey(JobData, on_delete=models.CASCADE, verbose_name='职位')
    created_at = models.DateTimeField('收藏时间', auto_now_add=True)

    class Meta:
        db_table = 'favorite_job'
        verbose_name = '职位收藏'
        verbose_name_plural = verbose_name
        unique_together = ['user', 'job']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.user_name} 收藏 {self.job.name}"


class UserExpect(models.Model):
    """用户求职意向表"""
    expect_id = models.AutoField('意向ID', primary_key=True)
    user = models.OneToOneField('users.UserList', on_delete=models.CASCADE, verbose_name='用户')
    key_word = models.CharField('期望职位', max_length=100, blank=True, null=True)
    place = models.CharField('期望地点', max_length=100, blank=True, null=True)
    salary_min = models.DecimalField('期望最低薪资', max_digits=10, decimal_places=2, blank=True, null=True)
    salary_max = models.DecimalField('期望最高薪资', max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'user_expect'
        verbose_name = '求职意向'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.user_name}的求职意向"


class UserExpectItem(models.Model):
    """用户多条求职意向"""
    expect_item_id = models.AutoField('意向项ID', primary_key=True)
    user = models.ForeignKey('users.UserList', on_delete=models.CASCADE, verbose_name='用户')
    key_word = models.CharField('期望职位', max_length=100, blank=True, null=True)
    place = models.CharField('期望地点', max_length=100, blank=True, null=True)
    salary_min = models.DecimalField('期望最低薪资', max_digits=10, decimal_places=2, blank=True, null=True)
    salary_max = models.DecimalField('期望最高薪资', max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'user_expect_item'
        verbose_name = '求职意向项'
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.user_name}的意向项"
