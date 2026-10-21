"""Django settings for megra_prime project (landing -> webapp + HTMX)."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# .env local (stdlib, sin dependencias). En Coolify se usan variables de entorno reales.
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-only-megra-prime")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
# Dominio público del sitio: se usa en canonical, og:url, sitemap y JSON-LD.
SITE_URL = os.environ.get("DJANGO_SITE_URL", "https://megaprimeimport.com").rstrip("/")
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
# Loopback siempre permitido: lo usa el healthcheck interno del contenedor.
# .sslip.io: links temporales de Coolify (preview). Inofensivo.
for _h in ("localhost", "127.0.0.1", "[::1]", ".sslip.io"):
    if _h not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_h)
if DEBUG and "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS += ["testserver"]

CSRF_TRUSTED_ORIGINS = [
    o
    for o in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS", "https://megaprimeimport.com,https://www.megaprimeimport.com"
    ).split(",")
    if o
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django_htmx",
    "core",
    "catalog",
    "cart",
    "calculator",
    "accounts",
    "panel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "megra_prime.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "megra_prime.wsgi.application"

# DB: DATABASE_URL (prod Coolify) > POSTGRES_* (local) > SQLite.
# Ej: DATABASE_URL=postgres://megra_prime:CLAVE@db:5432/megra_prime
import urllib.parse as _up


def _db_from_url(url: str) -> dict:
    u = _up.urlparse(url)
    if u.scheme in ("postgres", "postgresql"):
        cfg = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": (_up.unquote(u.path or "") or "/")[1:],
            "USER": _up.unquote(u.username or ""),
            "PASSWORD": _up.unquote(u.password or ""),
            "HOST": u.hostname or "",
            "PORT": str(u.port or ""),
            "CONN_MAX_AGE": 60,
        }
        qs = _up.parse_qs(u.query)
        if "sslmode" in qs:
            cfg["OPTIONS"] = {"sslmode": qs["sslmode"][0]}
        return cfg
    if u.scheme == "sqlite":
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / (u.path.lstrip("/") or "db.sqlite3")}
    raise ValueError(f"DATABASE_URL no soportada: {u.scheme}")


if os.environ.get("DATABASE_URL"):
    DATABASES = {"default": _db_from_url(os.environ["DATABASE_URL"])}
elif os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "db"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

if not DEBUG and SECRET_KEY.startswith("django-insecure-"):
    raise ValueError("En producción define DJANGO_SECRET_KEY seguro (ver .env.example).")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-ec"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "core:home"

# Negocio
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "593999999999")
CURRENCY = "USD"
IVA_DEFAULT_PCT = float(os.environ.get("IVA_DEFAULT_PCT", "15"))
FODINFA_DEFAULT_PCT = 0.5
