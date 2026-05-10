from django.db import models


class SpiderInfo(models.Model):
    """爬虫运行信息表"""
    STATUS_CHOICES = [
        (0, '空闲'),
        (1, '运行中'),
    ]
    
    spider_id = models.AutoField('爬虫ID', primary_key=True)
    spider_name = models.CharField('爬虫名称', max_length=100, blank=True, null=True)
    target_site = models.CharField('目标网站', max_length=100, blank=True, null=True)
    total_count = models.IntegerField('累计爬取数量', default=0)
    last_new_count = models.IntegerField('本次新增数量', default=0)
    run_count = models.IntegerField('运行次数', default=0)
    last_run_time = models.DateTimeField('最后运行时间', blank=True, null=True)
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'spider_info'
        verbose_name = '爬虫信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.spider_name or f"爬虫{self.spider_id}"
