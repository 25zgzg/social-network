# UASocial — соціальна мережа на Django

Навчальний MVP за ТЗ: реєстрація/вхід (локальна + Google OAuth), ролі Django (user/staff/superuser), профілі, стрічка, публікації з медіа-посиланнями, лайки, коментарі, друзі, підписки, спільноти, чати з реальним часом і вкладеннями, сповіщення, рейтингові моделі та адмін-модерація.

## Запуск (Docker — рекомендовано)

```bash
cp .env.example .env        # заповнити DJANGO_SECRET_KEY (обов'язково) та Google-ключі
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Відкрити http://localhost:8000/ . Адмін-панель: `/admin/`. Сервіси: `web` (Django + Daphne/ASGI, порт 8000) і `redis` (channel layer).

Без Docker: venv + `pip install -r requirements.txt`, локальний Redis на `redis://127.0.0.1:6379` (потрібен для WebSocket-чату).

## Змінні середовища (`.env`)

| Змінна | Призначення |
|---|---|
| `DJANGO_SECRET_KEY` | обов'язкова; без неї застосунок не стартує |
| `DJANGO_DEBUG` / `DJANGO_ALLOWED_HOSTS` | режими оточення |
| `REDIS_URL` | channel layer для WS-чату (за замовчуванням `redis://127.0.0.1:6379`) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth-клієнт Google; redirect URI: `http://localhost:8000/accounts/google/login/callback/` |
| `SENTRY_DSN` | ініціалізація Sentry; порожня — SDK вимкнено |
| `SENTRY_ENVIRONMENT` / `SENTRY_TRACES_SAMPLE_RATE` | параметри Sentry |

## Архітектура

- `network/models.py` — профілі, соціальні зв'язки, публікації, групи, чати, сповіщення та рейтинги.
- `network/views.py`, `forms.py`, `urls.py` — серверна бізнес-логіка, CSRF-захищені форми й контроль доступу.
- `network/consumers.py` + `routing.py` — WebSocket-чат (авторизація учасників, збереження повідомлень, сповіщення).
- `network/adapters.py` — allauth-адаптер Google (автоматичний Profile + аватарка).
- `templates/`, `static/css/` — адаптивний frontend: Bootstrap 5 + Bootstrap Icons + власні стилі; мінімальний JS (WebSocket-клієнти чату й сповіщень).
- SQLite для розробки; для production рекомендовано PostgreSQL.

## Перевірка

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py test        # unit-тести Django
```

### E2E-тести (Playwright)

Проти живого сервера (Docker або runserver на :8000):

```bash
venv/Scripts/python -m pip install -r requirements-dev.txt
venv/Scripts/python -m playwright install chromium
venv/Scripts/python -m pytest tests/e2e -v
```

Покриття: головна й сторінка входу з Google-кнопкою, реєстрація + публікація поста, повний флоу чату двох користувачів із перевіркою доставки повідомлення в реальному часі (WebSocket). Базова адреса — через `E2E_BASE_URL`.

### Sentry

Коли `SENTRY_DSN` заповнено, помилки Django та трейси надсилаються в Sentry (DjangoIntegration, `send_default_pii=True` — видно користувача). Локально без DSN — повністю вимкнено.

## Production і безпека

`DEBUG=False`, `ALLOWED_HOSTS` із доменом, HTTPS/HSTS, secure cookies, PostgreSQL, gunicorn замість runserver. Для Google OAuth додати в redirect URIs адресу прод-домену (`https://домен/accounts/google/login/callback/`).
