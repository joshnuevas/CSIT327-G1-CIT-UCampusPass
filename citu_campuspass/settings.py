"""
Django settings for citu_campuspass project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env (local only)
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Environment Variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# SQLite fallback (local)
default_sqlite = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"

# SECURITY
SECRET_KEY = 'django-insecure-b8r!x^&twa6+#0sb^ek*w2rpe2d@-(u5%kbjwy9gd!$yz94_fj'
DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com']

# Installed Apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Project Apps
    'dashboard_app',
    'register_app',
    'login_app',
    'book_visit_app',
    'history_app',
    'profile_app',
    'help_app',
    'manage_staff_app',
    'manage_visitor_app',
    'manage_admin_app',
    'manage_visit_records_app',
    'manage_reports_logs_app',
    'walk_in_app',
    'visitor_search_app',
    'staff_visit_records_app',
    'calendar_app',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'citu_campuspass.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "dashboard_app.context_processors.visitor_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = 'citu_campuspass.wsgi.application'

# Database (Supabase)
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", default_sqlite),
        conn_max_age=0,
        ssl_require=True
    )
}

# Password Validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static Files (Render)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Default Primary Key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login Settings
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'

# ===========================
# EMAIL (SendGrid Web API Only)
# ===========================

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "citucampuspass@gmail.com")

# Disable SMTP (Render free tier blocks it)
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
