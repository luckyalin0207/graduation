# 数据集目录

## Lagou_Data.csv — 拉勾网招聘数据

| 项 | 值 |
|---|---|
| 来源 | [weizhuang1113/Lagou_Spider_And_Data_Analysis](https://github.com/weizhuang1113/Lagou_Spider_And_Data_Analysis) `data/Lagou_Data.csv` |
| 体量 | 2,983 条招聘记录 |
| 时间跨度 | 2018-03-12 ~ 2018-04-12(共 32 天) |
| 字段数 | 33 列 |
| 编码 | GB18030(已知 GB2312 超集,导入脚本自动识别) |
| 主要字段 | `positionName / companyFullName / companyShortName / salary / topSalary / bottomSalary / avgSalary / workYear / education / city / district / industryField / companySize / financeStage / positionLables / positionAdvantage / content / createTime / longitude / latitude` |

## 字段到 `JobData` 的映射

| CSV 列 | `JobData` 字段 | 备注 |
|---|---|---|
| `positionName` | `name` | 职位名称 |
| `companyFullName` | `company` | 公司全称 |
| `salary` | `salary` | 原始字符串,如 `10k-16k` |
| `bottomSalary` | `salary_min` | 数据集已解析好,免再正则 |
| `topSalary` | `salary_max` | 同上 |
| `city` | `city` | 城市 |
| `education` | `education` | 学历 |
| `workYear` | `experience` | 工作年限 |
| `industryField` | `industry` | 所属行业 |
| `companySize` | `scale` | 公司规模 |
| `financeStage` | `company_type` | 借用公司类型字段存放融资阶段 |
| `positionLables` | `label` | 技能标签集合 |
| `content` | `description` | 职位详情 |
| `firstType` / `secondType` | `key_word` | 合并为搜索关键词 |
| `createTime` | `created_at` | 职位发布时间 |
| `positionId` | (不直接存) | 仅用于去重 |
| `longitude` / `latitude` | (不直接存) | 保留在导入日志中,未来地图可复用 |

## 导入

```powershell
# 默认读取 data/Lagou_Data.csv
python manage.py import_lagou

# 指定其他路径或限制条数(快速测试)
python manage.py import_lagou --path data/Lagou_Data.csv --limit 500

# 同时写入时间序列表(供岗位趋势分析使用)
python manage.py import_lagou --with-trend

# 重新导入前清空旧数据
python manage.py import_lagou --flush
```

## 许可与致谢

原始数据遵循原仓库授权。本项目仅将该数据集用于学术研究与毕业设计的课堂展示,不用于商业用途。引用时请注明原作者 weizhuang1113 与拉勾网。
