# 招聘数据分析与可视化系统

基于 Django 的智能招聘数据分析平台，集成 Job-SDF 历史数据集，支持多平台爬虫、岗位趋势分析、AI 对话助手、职位推荐等功能。

## 功能特性

- 🕷️ **多平台爬虫** — 51job、BOSS直聘，支持多关键词并行爬取
- 📊 **岗位趋势分析** — 基于拉勾网招聘数据集(2018 年 3-4 月,2983 条),结合实时爬取数据,提供五维评分、薪资分布、技能推荐
- 🤖 **AI 对话助手** — 简历优化、薪资查询、职位推荐
- 📋 **求职看板** — 拖拽式投递进度管理
- 📄 **简历解析** — PDF/Word 自动解析结构化信息
- 🏢 **公司分析** — 公司规模、行业分布可视化

## 技术栈

- **后端**: Django, Python 3.11
- **数据库**: PostgreSQL（生产）/ SQLite（开发）
- **爬虫**: Selenium, Requests
- **数据集**: [拉勾网招聘数据](https://github.com/weizhuang1113/Lagou_Spider_And_Data_Analysis)(2018 年 3-4 月,2983 条真实岗位)
- **ML**: scikit-learn, pandas, pyarrow
- **前端**: Bootstrap 4, jQuery, ECharts

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python manage.py migrate

# 启动开发服务器
python manage.py runserver
```

访问 `http://127.0.0.1:8000`

## 数据集(拉勾网招聘数据)

岗位趋势分析依赖一份真实的招聘样本。本项目采用拉勾网公开数据集,文件已随仓库放在 `data/Lagou_Data.csv`(约 3 MB,2983 条)。

```bash
# 首次导入(清空旧数据 + 写入 JobData/HistoricalJobData/SkillCooccurrence)
python manage.py import_lagou --flush --with-trend --with-cooc

# 快速冒烟(限 500 条)
python manage.py import_lagou --limit 500

# 仅导岗位明细,不要时间序列
python manage.py import_lagou
```

- 数据来源: <https://github.com/weizhuang1113/Lagou_Spider_And_Data_Analysis> `data/Lagou_Data.csv`
- 时间跨度: 2018-03-12 ~ 2018-04-12(32 天,可做日度趋势)
- 字段对齐说明见 `data/README.md`
- 旧的 Job-SDF 命令 `import_job_sdf` 已标记为 legacy,如需强制使用请加 `--force`

## 部署（Railway）

### 1. 推送代码到 GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/your-repo.git
git push -u origin main
```

### 2. 在 Railway 创建项目

1. 访问 [railway.app](https://railway.app) 并登录
2. 点击 **New Project** → **Deploy from GitHub repo**
3. 选择你的仓库，添加 PostgreSQL 数据库

### 3. 配置环境变量

| 变量名 | 说明 |
|--------|------|
| `SECRET_KEY` | Django 密钥（`python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` 生成） |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `your-app.railway.app` |
| `LLM_API_KEY` | AI 功能的 API Key（可选） |
| `OPENAI_BASE_URL` | LLM 接口地址（可选） |
| `LLM_MODEL` | 模型名称（可选） |
