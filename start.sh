#!/bin/bash
set -e

echo "=== 安装依赖 ==="
pip install -r requirements.txt -q

echo "=== 数据库迁移 ==="
python manage.py migrate --noinput

echo "=== 收集静态文件 ==="
python manage.py collectstatic --noinput -v 0

echo "=== 启动服务器 ==="
gunicorn recruitment_analysis.wsgi \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
