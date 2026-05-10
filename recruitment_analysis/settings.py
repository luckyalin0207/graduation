"""
Django settings for recruitment_analysis project.
支持本地开发（SQLite）和生产环境（PostgreSQL on Railway）
"""
import os
import sys
import warnings
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')
warnings.filterwarnings('ignore', message='X has feature names')

BASE_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = Path(os.getenv("RUNTIME_DIR", BASE_DIR / "var"))

sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

ADMIN_USER_IDS = ['admin']

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-flx(mt^&4(ntvivj%kxkr*wo!nzjol2-as1b_(c^f9y8cac&#')

DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS_ENV = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_ENV.split(',') if h.strip()]
# Railway 自动注入 RAILWAY_PUBLIC_DOMAIN
RAILWAY_DOMAIN = os.getenv('RAILWAY_PUBLIC_DOMAIN', '')
if RAILWAY_DOMAIN and RAILWAY_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RAILWAY_DOMAIN)

# Replit 域名自动支持（变量定义，实际处理在 CSRF_TRUSTED_ORIGINS 之后）
REPLIT_DOMAIN = os.getenv('REPL_SLUG', '')
REPLIT_OWNER = os.getenv('REPL_OWNER', '')

CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]
if RAILWAY_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RAILWAY_DOMAIN}')
# 支持自定义域名
CUSTOM_DOMAIN = os.getenv('CUSTOM_DOMAIN', '')
if CUSTOM_DOMAIN:
    ALLOWED_HOSTS.append(CUSTOM_DOMAIN)
    CSRF_TRUSTED_ORIGINS.append(f'https://{CUSTOM_DOMAIN}')

CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False

# Replit 域名自动支持（移到 CSRF_TRUSTED_ORIGINS 定义之后）
if REPLIT_DOMAIN and REPLIT_OWNER:
    replit_host = f'{REPLIT_DOMAIN}.{REPLIT_OWNER}.repl.co'
    replit_host2 = f'{REPLIT_DOMAIN}-{REPLIT_OWNER}.replit.app'
    for h in [replit_host, replit_host2, '*.replit.app', '*.repl.co']:
        if h not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(h)
    CSRF_TRUSTED_ORIGINS.extend([
        f'https://{replit_host}',
        f'https://{replit_host2}',
    ])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users",
    "jobs",
    "spider",
    "analysis",
    "recommend",
    "agent",
    "company",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # 静态文件（生产）
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "recruitment_analysis.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "recruitment_analysis.wsgi.application"

# ── 数据库 ────────────────────────────────────────────────────────────────────
# Railway 注入 DATABASE_URL 环境变量（PostgreSQL）
# 本地开发使用 SQLite
DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    # Replit 持久化目录在项目根目录下
    db_dir = BASE_DIR if os.getenv('REPL_SLUG') else RUNTIME_DIR
    os.makedirs(db_dir, exist_ok=True)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_dir / 'db.sqlite3',
        }
    }

# ── 缓存 ──────────────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "recruitment-cache",
        "TIMEOUT": 300,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# ── 静态文件 ──────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = RUNTIME_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400

# ── 邮件 ──────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.qq.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@recruitment-system.com')

# ── 企业信息验证 API 配置 ──────────────────────────────────────────────────────
# 企查查 Open API（付费）：https://openapi.qcc.com/
QICHACHA_KEY = os.getenv('QICHACHA_KEY', '')
QICHACHA_SECRET = os.getenv('QICHACHA_SECRET', '')
# 天眼查 Open API（付费）：https://www.tianyancha.com/cloud-other-information/openApi.html
TIANYANCHA_TOKEN = os.getenv('TIANYANCHA_TOKEN', '')

# ── LLM 配置 ──────────────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv('LLM_PROVIDER', '')
LLM_API_KEY = os.getenv('LLM_API_KEY', '')
LLM_MODEL = os.getenv('LLM_MODEL', 'claude-3-5-haiku-20241022')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://anyrouter.top/v1')
WENXIN_SECRET_KEY = os.getenv('WENXIN_SECRET_KEY', '')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')

# ── 生产安全配置 ───────────────────────────────────────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ── 日志 ──────────────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(RUNTIME_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '{levelname} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'spider': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'agent': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
