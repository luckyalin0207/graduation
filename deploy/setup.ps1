# 招聘数据分析系统 - 自动化设置脚本

Write-Host "🚀 开始设置招聘数据分析系统..." -ForegroundColor Green

# 1. 重新创建虚拟环境
Write-Host "`n📦 设置虚拟环境..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "删除旧的虚拟环境..."
    Remove-Item -Recurse -Force venv -ErrorAction SilentlyContinue
}

Write-Host "创建新的虚拟环境..."
python -m venv venv

Write-Host "激活虚拟环境..."
& ".\venv\Scripts\Activate.ps1"

Write-Host "升级pip..."
python -m pip install --upgrade pip

# 2. 安装依赖
Write-Host "`n📚 安装Python依赖..." -ForegroundColor Yellow
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 创建必要目录
Write-Host "`n📁 创建项目目录..." -ForegroundColor Yellow
$directories = @("logs", "media", "staticfiles")
foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "✅ 创建目录: $dir" -ForegroundColor Green
    } else {
        Write-Host "📁 目录已存在: $dir" -ForegroundColor Gray
    }
}

# 4. 复制环境变量文件
Write-Host "`n⚙️ 设置环境变量..." -ForegroundColor Yellow
if (!(Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "✅ 创建 .env 文件" -ForegroundColor Green
} elseif (Test-Path ".env") {
    Write-Host "📄 .env 文件已存在" -ForegroundColor Gray
} else {
    Write-Host "⚠️ .env.example 文件不存在" -ForegroundColor Red
}

# 5. Django设置
Write-Host "`n🔍 检查Django配置..." -ForegroundColor Yellow
python manage.py check

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n🗄️ 执行数据库迁移..." -ForegroundColor Yellow
    python manage.py migrate
    
    Write-Host "`n📦 收集静态文件..." -ForegroundColor Yellow
    python manage.py collectstatic --noinput
    
    Write-Host "`n🎉 项目设置完成！" -ForegroundColor Green
    Write-Host "`n📝 下一步操作:" -ForegroundColor Cyan
    Write-Host "1. 创建管理员: python manage.py createsuperuser" -ForegroundColor White
    Write-Host "2. 启动服务器: python manage.py runserver" -ForegroundColor White
    Write-Host "3. 访问系统: http://127.0.0.1:8000/" -ForegroundColor White
    
    # 询问是否创建管理员
    $createAdmin = Read-Host "`n是否现在创建管理员账号? (y/n)"
    if ($createAdmin -eq "y" -or $createAdmin -eq "Y") {
        python manage.py createsuperuser
    }
    
    # 询问是否启动服务器
    $startServer = Read-Host "`n是否现在启动开发服务器? (y/n)"
    if ($startServer -eq "y" -or $startServer -eq "Y") {
        Write-Host "`n🌐 启动开发服务器..." -ForegroundColor Green
        Write-Host "访问 http://127.0.0.1:8000/ 查看系统" -ForegroundColor Cyan
        python manage.py runserver
    }
} else {
    Write-Host "`n❌ Django配置检查失败，请检查配置" -ForegroundColor Red
}