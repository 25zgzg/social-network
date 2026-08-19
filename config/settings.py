import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY=os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY environment variable is required')
DEBUG=os.environ.get('DJANGO_DEBUG', 'False') == 'True'
ALLOWED_HOSTS=os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if os.environ.get('DJANGO_ALLOWED_HOSTS') else []
SENTRY_DSN=os.environ.get('SENTRY_DSN','')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(dsn=SENTRY_DSN,integrations=[DjangoIntegration()],traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE','0.1')),send_default_pii=False,environment=os.environ.get('SENTRY_ENVIRONMENT','development'))
INSTALLED_APPS=['daphne','django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','django.contrib.sites','allauth','allauth.account','allauth.socialaccount','allauth.socialaccount.providers.google','channels','network']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','network.csp.CSPMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','network.ratelimit.RateLimitMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware','allauth.account.middleware.AccountMiddleware']
ROOT_URLCONF='config.urls'; ASGI_APPLICATION='config.asgi.application'; CHANNEL_LAYERS={'default':{'BACKEND':'channels_redis.core.RedisChannelLayer','CONFIG':{'hosts':[os.getenv('REDIS_URL', 'redis://127.0.0.1:6379')]}}}; TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]; WSGI_APPLICATION='config.wsgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS=[
 {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
 {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},
 {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
 {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]; LANGUAGE_CODE='uk'; TIME_ZONE='Europe/Kyiv'; USE_I18N=True; USE_TZ=True
STATIC_URL='static/'; STATICFILES_DIRS=[BASE_DIR/'static']; MEDIA_URL='media/'; MEDIA_ROOT=BASE_DIR/'media'; LOGIN_REDIRECT_URL='feed'; LOGOUT_REDIRECT_URL='home'; DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
SITE_ID=1; AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend','allauth.account.auth_backends.AuthenticationBackend']
ACCOUNT_EMAIL_VERIFICATION='none'; SOCIALACCOUNT_LOGIN_ON_GET=False; SOCIALACCOUNT_ADAPTER='network.adapters.CustomSocialAccountAdapter'
SOCIALACCOUNT_PROVIDERS={'google':{'APP':{'client_id':os.environ.get('GOOGLE_CLIENT_ID',''),'secret':os.environ.get('GOOGLE_CLIENT_SECRET','')}}}
_is_prod=not DEBUG
ADMIN_URL=os.environ.get('DJANGO_ADMIN_URL','admin/').strip('/')+'/'
SESSION_COOKIE_SECURE=_is_prod; CSRF_COOKIE_SECURE=_is_prod; SESSION_COOKIE_HTTPONLY=True
SECURE_HSTS_SECONDS=31536000 if _is_prod else 0; SECURE_HSTS_INCLUDE_SUBDOMAINS=_is_prod; SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_SSL_REDIRECT=os.environ.get('SECURE_SSL_REDIRECT','') == 'True'
# Content-Security-Policy: base.html використовує inline-скрипти/стилі та CDN (jsdelivr, Google Fonts)
SECURE_CONTENT_SECURITY_POLICY={'default-src':["'self'"],'script-src':["'self'","'unsafe-inline'",'https://cdn.jsdelivr.net'],'style-src':["'self'","'unsafe-inline'",'https://cdn.jsdelivr.net','https://fonts.googleapis.com'],'font-src':['https://fonts.gstatic.com','https://cdn.jsdelivr.net'],'img-src':["'self'",'data:','https://lh3.googleusercontent.com'],'connect-src':["'self'",'ws:','wss:'],'object-src':["'none'"],'base-uri':["'self'"],'frame-ancestors':["'self'"],'form-action':["'self'"]}
# Messages через сесії (для messages.error у групах)
from django.contrib.messages import constants as messages  # noqa: E402
