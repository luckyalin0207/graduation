from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='CompanyVerification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(db_index=True, max_length=255, verbose_name='公司名称')),
                ('unified_code', models.CharField(blank=True, max_length=50, null=True, verbose_name='统一社会信用代码')),
                ('legal_person', models.CharField(blank=True, max_length=100, null=True, verbose_name='法定代表人')),
                ('registered_capital', models.CharField(blank=True, max_length=100, null=True, verbose_name='注册资本')),
                ('establishment_date', models.CharField(blank=True, max_length=50, null=True, verbose_name='成立日期')),
                ('business_status', models.CharField(blank=True, max_length=50, null=True, verbose_name='经营状态')),
                ('registered_address', models.CharField(blank=True, max_length=500, null=True, verbose_name='注册地址')),
                ('business_scope', models.TextField(blank=True, null=True, verbose_name='经营范围')),
                ('company_type', models.CharField(blank=True, max_length=100, null=True, verbose_name='企业类型')),
                ('industry', models.CharField(blank=True, max_length=100, null=True, verbose_name='所属行业')),
                ('staff_size', models.CharField(blank=True, max_length=50, null=True, verbose_name='人员规模')),
                ('phone', models.CharField(blank=True, max_length=50, null=True, verbose_name='联系电话')),
                ('email', models.CharField(blank=True, max_length=100, null=True, verbose_name='联系邮箱')),
                ('website', models.CharField(blank=True, max_length=255, null=True, verbose_name='官网')),
                ('risk_count', models.IntegerField(default=0, verbose_name='风险数量')),
                ('lawsuit_count', models.IntegerField(default=0, verbose_name='司法案件数')),
                ('dishonest_count', models.IntegerField(default=0, verbose_name='失信记录数')),
                ('risk_level', models.CharField(
                    choices=[('低', '低风险'), ('中', '中风险'), ('高', '高风险'), ('未知', '未知')],
                    default='未知', max_length=20, verbose_name='风险等级'
                )),
                ('source', models.CharField(
                    choices=[
                        ('aiqicha', '爱企查'), ('tianyancha', '天眼查'),
                        ('qichacha', '企查查'), ('gsxt', '国家企业信用信息公示系统'),
                        ('manual', '手动录入'),
                    ],
                    default='aiqicha', max_length=20, verbose_name='数据来源'
                )),
                ('status', models.CharField(
                    choices=[
                        ('verified', '已验证'), ('not_found', '未找到'),
                        ('error', '查询失败'), ('pending', '待验证'),
                    ],
                    default='pending', max_length=20, verbose_name='验证状态'
                )),
                ('raw_data', models.JSONField(blank=True, null=True, verbose_name='原始数据')),
                ('verified_at', models.DateTimeField(auto_now=True, verbose_name='验证时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': '企业验证信息',
                'verbose_name_plural': '企业验证信息',
                'db_table': 'company_verification',
                'ordering': ['-verified_at'],
                'indexes': [
                    models.Index(fields=['company_name'], name='company_ver_company_idx'),
                    models.Index(fields=['unified_code'], name='company_ver_code_idx'),
                ],
            },
        ),
    ]
