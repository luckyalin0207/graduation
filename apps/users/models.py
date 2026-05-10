from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class UserList(models.Model):
    """用户信息表"""
    user_id = models.CharField('用户ID', primary_key=True, max_length=20)
    user_name = models.CharField('用户名', max_length=100)
    password = models.CharField('密码', max_length=255)
    email = models.EmailField('邮箱', max_length=100, blank=True, null=True)
    phone = models.CharField('手机号', max_length=20, blank=True, null=True)
    avatar = models.CharField('头像', max_length=255, blank=True, null=True)
    resume_file = models.FileField('简历文件', upload_to='resumes/', blank=True, null=True)
    resume_name = models.CharField('简历文件名', max_length=255, blank=True, null=True)
    resume_updated_at = models.DateTimeField('简历更新时间', blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'user_list'
        verbose_name = '用户信息'
        verbose_name_plural = verbose_name

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.user_name


class UserWorkExperience(models.Model):
    """用户工作经历"""
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(UserList, on_delete=models.CASCADE, related_name='work_experiences')
    company = models.CharField('公司名称', max_length=200, blank=True, null=True)
    title = models.CharField('职位名称', max_length=200, blank=True, null=True)
    start_date = models.CharField('开始时间', max_length=20, blank=True, null=True)
    end_date = models.CharField('结束时间', max_length=20, blank=True, null=True)
    description = models.TextField('工作描述', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_work_experience'
        verbose_name = '工作经历'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.user.user_name} - {self.company}"


class UserEducation(models.Model):
    """用户教育经历"""
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(UserList, on_delete=models.CASCADE, related_name='educations')
    school = models.CharField('学校名称', max_length=200, blank=True, null=True)
    degree = models.CharField('学历', max_length=50, blank=True, null=True)
    major = models.CharField('专业', max_length=200, blank=True, null=True)
    start_date = models.CharField('开始时间', max_length=20, blank=True, null=True)
    end_date = models.CharField('结束时间', max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_education'
        verbose_name = '教育经历'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.user.user_name} - {self.school}"
