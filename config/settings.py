import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def env_bool(name, default=False):
    """Read a conventional truthy environment flag with a safe default."""

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    """Read a comma-separated environment value as a trimmed list."""

    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def required_env(name):
    """Read a required setting or stop startup with an actionable error."""

    value = os.getenv(name)
    if value:
        return value
    raise ImproperlyConfigured(
        f"{name} must be set. Start the app with Docker Compose so it uses the "
        "project database instead of an unrelated local PostgreSQL instance."
    )


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool("DJANGO_DEBUG", default=True)

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-wj1_)%xyi5(=qq$lrs-bxx^y6aac1)*a+sbnovv@$7o)lz3(a("
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG=False")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")


# Application definition

INSTALLED_APPS = [
    # Django default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Bahasha apps
    'churches',
    'users',
    'members',
    'jumuiya',
    'categories',
    'financial_years',
    'contribution_weeks',
    'annual_targets',
    'contributions',
    'excel_uploads',
    'notifications',
    'reports',
    'audit_logs',
    'dashboard',
    'payments',
    'web',
    "printing",

]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "api.common.middleware.RequestIDMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        'DIRS': [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "web.context_processors.current_page",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required_env("POSTGRES_DB"),
        "USER": required_env("POSTGRES_USER"),
        "PASSWORD": required_env("POSTGRES_PASSWORD"),
        "HOST": required_env("POSTGRES_HOST"),
        "PORT": required_env("POSTGRES_PORT"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Africa/Dar_es_Salaam")

USE_I18N = True

USE_TZ = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=False)
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", default=False)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", default=False)

# Email is printed to the application logs by default for local development.
# Production deployments should configure SMTP through the documented variables.
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", default=False)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Bahasha <noreply@localhost>")

# Payment provider requests are server-to-server. Keep all provider credentials out
# of the mobile application and enable the public payment flow only after sandbox
# settlement and failure-path tests pass.
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "vodacom_m_pesa")
PAYMENTS_ENABLED = env_bool("PAYMENTS_ENABLED", default=False)
MPESA_ENVIRONMENT = os.getenv("MPESA_ENVIRONMENT", "sandbox").lower()
MPESA_DEFAULT_BASE_URLS = {
    "sandbox": "https://openapi.m-pesa.com/sandbox/",
    "production": "https://openapi.m-pesa.com/openapi/",
}
if MPESA_ENVIRONMENT not in MPESA_DEFAULT_BASE_URLS:
    raise ImproperlyConfigured(
        "MPESA_ENVIRONMENT must be either sandbox or production."
    )
MPESA = {
    "enabled": env_bool("MPESA_ENABLED", default=False),
    "environment": MPESA_ENVIRONMENT,
    "base_url": os.getenv(
        "MPESA_BASE_URL",
        MPESA_DEFAULT_BASE_URLS[MPESA_ENVIRONMENT],
    ),
    "api_key": os.getenv("MPESA_API_KEY", ""),
    "public_key": os.getenv("MPESA_PUBLIC_KEY", "").replace("\\n", "\n"),
    "service_provider_code": os.getenv("MPESA_SERVICE_PROVIDER_CODE", ""),
    "market": os.getenv("MPESA_MARKET", "vodacomTZN"),
    "country": os.getenv("MPESA_COUNTRY", "TZN"),
    "currency": os.getenv("MPESA_CURRENCY", "TZS"),
    "c2b_path": os.getenv(
        "MPESA_C2B_PATH",
        "ipg/v2/{market}/c2bPayment/singleStage/",
    ),
    "query_path": os.getenv(
        "MPESA_QUERY_PATH",
        "ipg/v2/{market}/queryTransactionStatus/",
    ),
    "timeout_seconds": float(os.getenv("MPESA_TIMEOUT_SECONDS", "20")),
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

AUTH_USER_MODEL = "users.User"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
