from .base import *  # noqa: F401,F403

DEBUG = False
# Render (y la mayoría de PaaS) termina el TLS en su proxy y reenvía HTTP
# internamente. Sin esta cabecera, SECURE_SSL_REDIRECT puede provocar un bucle.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
# WhiteNoise cachea los estáticos con hash/nombre estable durante 1 año.
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365
