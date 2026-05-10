from django.db import models
from django.db.models import Sum


class HistoricalJobData(models.Model):
    """历史招聘数据表（来自Job-SDF数据集）"""
    hist_id = models.AutoField('历史数据ID', primary_key=True)
    
    # 基本信息
    skill_name = models.CharField('技能名称', max_length=200, db_index=True)
    skill_id = models.IntegerField('技能ID', db_index=True)
    
    # 时间信息
    year = models.IntegerField('年份', db_index=True)
    month = models.IntegerField('月份', db_index=True)
    date = models.DateField('日期', db_index=True)
    
    # 需求数据
    demand_count = models.IntegerField('需求数量')
    demand_proportion = models.FloatField('需求占比', null=True, blank=True)
    
    # 分类信息
    occupation_l1 = models.CharField('一级职业', max_length=100, null=True, blank=True, db_index=True)
    occupation_l2 = models.CharField('二级职业', max_length=100, null=True, blank=True, db_index=True)
    company = models.CharField('公司', max_length=200, null=True, blank=True, db_index=True)
    region = models.CharField('地区', max_length=100, null=True, blank=True, db_index=True)
    
    # 元数据
    data_source = models.CharField('数据来源', max_length=50, default='Job-SDF')
    created_at = models.DateTimeField('导入时间', auto_now_add=True)
    
    class Meta:
        app_label = 'analysis'
        db_table = 'historical_job_data'
        verbose_name = '历史招聘数据'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['skill_name', 'date']),
            models.Index(fields=['occupation_l2', 'date']),
            models.Index(fields=['year', 'month']),
        ]
        unique_together = ['skill_id', 'year', 'month', 'occupation_l2', 'company', 'region']
    
    def __str__(self):
        return f"{self.skill_name} - {self.year}-{self.month:02d}"


class SkillMapping(models.Model):
    """技能映射表（Job-SDF技能ID到本地关键词的映射）"""
    mapping_id = models.AutoField('映射ID', primary_key=True)
    
    # Job-SDF数据
    skill_id = models.IntegerField('技能ID', unique=True, db_index=True)
    skill_name = models.CharField('技能名称', max_length=200, db_index=True)
    
    # 本地映射
    local_keyword = models.CharField('本地关键词', max_length=100, db_index=True)
    
    # 元数据
    confidence = models.FloatField('匹配置信度', default=1.0)
    is_manual = models.BooleanField('是否手动映射', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        app_label = 'analysis'
        db_table = 'skill_mapping'
        verbose_name = '技能映射'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.skill_name} -> {self.local_keyword}"


class SkillCooccurrence(models.Model):
    """技能共现关系表"""
    cooc_id = models.AutoField('共现ID', primary_key=True)
    
    skill_1_id = models.IntegerField('技能1 ID', db_index=True)
    skill_1_name = models.CharField('技能1名称', max_length=200)
    
    skill_2_id = models.IntegerField('技能2 ID', db_index=True)
    skill_2_name = models.CharField('技能2名称', max_length=200)
    
    frequency = models.IntegerField('共现频率')
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        app_label = 'analysis'
        db_table = 'skill_cooccurrence'
        verbose_name = '技能共现'
        verbose_name_plural = verbose_name
        unique_together = ['skill_1_id', 'skill_2_id']
        indexes = [
            models.Index(fields=['skill_1_id', '-frequency']),
            models.Index(fields=['skill_2_id', '-frequency']),
        ]
    
    def __str__(self):
        return f"{self.skill_1_name} <-> {self.skill_2_name} ({self.frequency})"
    
    @classmethod
    def get_related_skills(cls, skill_id, limit=10):
        """获取与指定技能相关的技能"""
        related = cls.objects.filter(
            models.Q(skill_1_id=skill_id) | models.Q(skill_2_id=skill_id)
        ).order_by('-frequency')[:limit]
        
        results = []
        for cooc in related:
            if cooc.skill_1_id == skill_id:
                results.append({
                    'skill_id': cooc.skill_2_id,
                    'skill_name': cooc.skill_2_name,
                    'frequency': cooc.frequency
                })
            else:
                results.append({
                    'skill_id': cooc.skill_1_id,
                    'skill_name': cooc.skill_1_name,
                    'frequency': cooc.frequency
                })
        
        return results
