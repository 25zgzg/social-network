# UASocial — соціальна мережа на Django

Навчальний MVP за ТЗ: реєстрація/вхід, ролі Django (user/staff/superuser), профілі, стрічка, публікації з медіа-посиланнями, лайки, коментарі, друзі, підписки, спільноти, чати, сповіщення, рейтингові моделі та адмін-модерація.

## Запуск

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Відкрити http://127.0.0.1:8000/ . Адмін-панель: `/admin/`.

## Архітектура

- `network/models.py` — профілі, соціальні зв’язки, публікації, групи, чати, сповіщення та рейтинги.
- `network/views.py`, `forms.py`, `urls.py` — серверна бізнес-логіка, CSRF-захищені форми й контроль доступу.
- `templates/`, `static/css/` — адаптивний frontend без JS-залежностей.
- SQLite для розробки; для production рекомендовано PostgreSQL.

## Перевірка

```powershell
python manage.py check
python manage.py test
```

## Production і безпека

Винести `SECRET_KEY` у змінну середовища, вимкнути `DEBUG`, вказати `ALLOWED_HOSTS`, налаштувати HTTPS/HSTS, secure cookies, PostgreSQL та сервер статики. WebSocket-шар реалізовано через Django Channels; локально використовується `InMemoryChannelLayer`. Для production замініть його на Redis channel layer. Збереження повідомлень виконується HTML-формами, а WebSocket-шар готовий для миттєвого UI-оновлення.

## GitFlow

Рекомендовані гілки: `main`, `develop`, `feature/*`, `release/*`, `hotfix/*`. Злиття — через pull request після проходження тестів.
