"""Configuración común. Lo específico de cada entorno va en dev.py / prod.py."""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
# Orígenes de confianza para peticiones POST por HTTPS (p. ej. https://mi-app.onrender.com).
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps del proyecto
    "apps.core",
    "apps.accounts",      # Sprint 1: perfil, registro, login, roles
    "apps.destinations",  # Sprint 1: destinos
    "apps.suppliers",     # Sprint 2: proveedores
    "apps.hotels",        # Sprint 2: hoteles, habitaciones, tarifas
    "apps.flights",       # Sprint 2: vuelos
    "apps.packages",      # Sprint 2: paquetes turísticos
    "apps.reservations",  # Sprint 3: reservas, pasajeros, documentos, itinerarios
    "apps.payments",      # Sprint 4: pagos, cuotas, facturas, reembolsos, caja
    # Sprint 5
    "apps.preferences",
    "apps.recommendations",
    "apps.reports",
    "apps.notifications.apps.NotificationsConfig",
    # Sprint 6
    "apps.support", 
    "apps.reviews.apps.ReviewsConfig",

]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise sirve los archivos estáticos directamente desde la app WSGI
    # (necesario en Render/Heroku, donde no hay nginx delante).
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # SEGURIDAD "DENY BY DEFAULT": toda vista exige sesión iniciada salvo que
    # se marque como pública con @login_not_required (ver apps/core/access.py).
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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
                "apps.accounts.context_processors.roles",
            ],
        },
    },
]

# Base de datos: PostgreSQL (estropical_db). Ver DATABASE_URL en .env
DATABASES = {"default": env.db("DATABASE_URL")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------- Autenticación
# Se usa el usuario estándar de Django (tablas auth_*), gestionado desde Django admin.
# El correo se guarda también como username (ver apps/accounts/forms.py).
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "core:home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------- Sesión / tokens
SESSION_COOKIE_AGE = 60 * 60 * 8            # la sesión caduca a las 8 horas
SESSION_COOKIE_HTTPONLY = True              # JS no puede leer la cookie de sesión
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 * 3   # enlaces de verificación/recuperación: 3 días
# El cambio de correo usa su propia caducidad (configurable por variable de entorno).
EMAIL_CHANGE_TIMEOUT = env.int("EMAIL_CHANGE_TIMEOUT", default=60 * 60 * 24)
# TODO: limitar intentos fallidos de login (p. ej. django-axes) antes de producción.

# ---------------------------------------------------------------- Correo
EMAIL_CONFIG = env.email("EMAIL_URL", default="consolemail://")
vars().update(EMAIL_CONFIG)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Estropical <no-reply@estropical.local>")
SITE_URL = env("SITE_URL", default="http://localhost:8000")

# ---------------------------------------------------------------- Inteligencia Artificial - Sprint 5
# Integración con Google Gemini para recomendaciones y chatbot turístico.

GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-3.8-flash")

# ---------------------------------------------------------------- Internacionalización
LANGUAGE_CODE = "es"
TIME_ZONE = "America/La_Paz"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------- Archivos
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise: comprime los estáticos y los sirve desde el proceso WSGI.
# Se usa CompressedStaticFilesStorage (sin manifest) para que el arranque no
# falle si collectstatic no se ejecutó exactamente en el mismo build.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
# CU-13: límite para documentos de proveedores (5 MB por defecto).
DOCUMENTO_PROVEEDOR_MAX_BYTES = env.int(
    "DOCUMENTO_PROVEEDOR_MAX_BYTES", default=5 * 1024 * 1024)
