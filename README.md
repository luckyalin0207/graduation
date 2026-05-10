# 招聘数据分析与可视化系统

基于 Django 的智能招聘数据分析平台，集成 Job-SDF 历史数据集，支持多平台爬虫、岗位趋势分析、AI 对话助手、职位推荐等功能。

## 功能特性

- 🕷️ **多平台爬虫** — 51job、BOSS直聘，支持多关键词并行爬取
- 📊 **岗位趋势分析** — 基于 Job-SDF 数据集（NeurIPS 2024）的历史趋势分析（2021-2023），结合实时爬取数据，提供五维评分、薪资分布、技能推荐
- 🤖 **AI 对话助手** — 简历优化、薪资查询、职位推荐
- 📋 **求职看板** — 拖拽式投递进度管理
- 📄 **简历解析** — PDF/Word 自动解析结构化信息
- 🏢 **公司分析** — 公司规模、行业分布可视化

## 技术栈

- **后端**: Django, Python 3.11
- **数据库**: PostgreSQL（生产）/ SQLite（开发）
- **爬虫**: Selenium, Requests
- **数据集**: [Job-SDF](https://github.com/Job-SDF/benchmark)（NeurIPS 2024，1035万条真实招聘数据）
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

## Job-SDF 数据集集成

岗位趋势分析功能依赖 [Job-SDF 数据集](https://github.com/Job-SDF/benchmark)。

```bash
# 克隆数据集到项目根目录
git clone https://github.com/Job-SDF/benchmark.git

# 导入数据（快速测试，100个技能）
python manage.py import_job_sdf --path ./benchmark/dataset --granularity l2 --limit 100

# 完整导入（约30-60分钟）
python manage.py import_job_sdf --path ./benchmark/dataset --granularity l2
```

数据集已下载后，系统会自动读取 `benchmark/dataset/demand/r0.parquet` 进行历史趋势分析，无需额外配置。

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
