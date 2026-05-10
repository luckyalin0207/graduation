@echo off
echo 🚀 开始设置招聘数据分析系统...

echo.
echo 📦 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python未安装或不在PATH中
    pause
    exit /b 1
)

echo.
echo 📚 安装核心依赖...
pip install Django==4.2.7 python-dotenv pandas numpy mysqlclient

echo.
echo 📁 创建必要目录...
if not exist "logs" mkdir logs
if not exist "media" mkdir media
if not exist "staticfiles" mkdir staticfiles
echo ✅ 目录创建完成

echo.
echo ⚙️ 复制环境变量文件...
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env"
        echo ✅ 创建 .env 文件
    ) else (
        echo ⚠️ .env.example 文件不存在
    )
) else (
    echo 📄 .env 文件已存在
)

echo.
echo 🔍 检查Django配置...
python manage.py check
if %errorlevel% neq 0 (
    echo ❌ Django配置检查失败
    echo 请检查数据库配置和依赖安装
    pause
    exit /b 1
)

echo.
echo 🗄️ 执行数据库迁移...
python manage.py migrate

echo.
echo 📦 收集静态文件...
python manage.py collectstatic --noinput

echo.
echo 🎉 项目设置完成！
echo.
echo 📝 下一步操作:
echo 1. 创建管理员: python manage.py createsuperuser
echo 2. 启动服务器: python manage.py runserver
echo 3. 访问系统: http://127.0.0.1:8000/

echo.
set /p choice="是否现在创建管理员账号? (y/n): "
if /i "%choice%"=="y" (
    python manage.py createsuperuser
)

echo.
set /p choice="是否现在启动开发服务器? (y/n): "
if /i "%choice%"=="y" (
    echo 🌐 启动开发服务器...
    echo 访问 http://127.0.0.1:8000/ 查看系统
    python manage.py runserver
)

pause