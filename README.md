# UASocial — Django Social Network / Соціальна мережа на Django

[English](#english) · [Українська](#українська)

<a name="english"></a>
A full-featured social network built with Django: posts with smart media, real-time WebSocket chat, friends & follows, groups with moderation, ratings/reviews, notifications with per-type settings, Google OAuth, and a theming system with 5 dual light/dark palettes.

## Features

- **Auth**: local signup with live username availability check, login, Google OAuth 2.0 (django-allauth, auto-creates account with avatar on first login).
- **Feed & posts**: publish text + media (images, video, YouTube embeds, plain links), likes, comments, shares/reposts; home feed scoped to friends/follows/groups for logged-in users.
- **Friends**: full lifecycle — send / accept / reject / cancel / remove, friends page with incoming/outgoing/friends sections; follows without friending.
- **Groups**: list with search, join/leave, posting for members, moderation by owner/admins (delete posts, kick members, promote/demote admins).
- **Chat**: private and group conversations created from friends; real-time WebSocket messaging (Django Channels + Redis), file/image attachments, message persistence, participant-only access.
- **Notifications**: likes, comments, shares, friend requests, follows, messages — with per-type settings (mute likes/comments/etc.) and a live unread badge pushed over WebSocket.
- **Ratings & reviews**: 1–5 stars on posts and groups with text reviews; staff moderation (hide/restore).
- **Personalization**: `/settings/` — theme mode (light / dark / follow device via `prefers-color-scheme`) and 5 color palettes (Violet, Ocean, Forest, Sunset, Mono with true-black dark), each defining both light and dark variants; instant preview + autosave.
- **Search**: users by username/first/last name and groups by name, with inline actions.
- **Events**: upcoming-events widget on home (managed via Django admin).

## Tech stack

Django 6 + Django Channels (ASGI/Daphne), django-allauth, SQLite (dev) / PostgreSQL-ready, Bootstrap 5 + custom CSS variables theming, Inter font, Sentry SDK (optional), Playwright E2E tests.

## Quick start (Docker)

```bash
cp .env.example .env        # fill DJANGO_SECRET_KEY (required) and Google keys
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser   # or seed demo data:
docker compose exec web python manage.py seed_demo          # 8 demo users, posts, chats, events (password: demo-pass-123)
```

Open http://localhost:8000 — admin at `/admin/`. Services: `web` (Django + Daphne, port 8000), `redis` (channel layer).

Without Docker: venv + `pip install -r requirements.txt`, local Redis at `redis://127.0.0.1:6379` (required for WebSocket chat).

## Environment variables (`.env`)

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | required — the app refuses to start without it |
| `DJANGO_DEBUG` / `DJANGO_ALLOWED_HOSTS` | environment mode |
| `REDIS_URL` | channel layer for WS chat (default `redis://127.0.0.1:6379`) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth client; redirect URI: `http://localhost:8000/accounts/google/login/callback/` |
| `SENTRY_DSN` | Sentry init; empty — SDK disabled |
| `SENTRY_ENVIRONMENT` / `SENTRY_TRACES_SAMPLE_RATE` | Sentry options |

## Architecture

- `network/models.py` — profiles, social graph, posts, groups, chats, notifications, ratings, events.
- `network/views.py`, `forms.py`, `urls.py` — server logic, CSRF-protected forms, access control.
- `network/consumers.py` + `routing.py` — WebSocket chat (auth + participant checks, persistence) and real-time notifications.
- `network/adapters.py` — allauth adapter (auto Profile + Google avatar).
- `network/management/commands/seed_demo.py` — realistic demo content; `--clean` removes E2E leftovers.
- `templates/`, `static/css/` — Bootstrap 5 + palette-driven CSS variables, minimal JS (chat & notification WebSocket clients).
- `tests/e2e/` — Playwright end-to-end tests.

## Testing

```bash
docker compose exec web python manage.py test     # 72 unit tests
# E2E (against a running server):
venv/Scripts/python -m pip install -r requirements-dev.txt
venv/Scripts/python -m playwright install chromium
venv/Scripts/python -m pytest tests/e2e -v        # 3 E2E tests incl. realtime chat
```

E2E coverage: home + Google button, signup + post publish, full two-user chat flow verifying live WebSocket delivery. Set `E2E_BASE_URL` to target another host.

## Production notes

`DEBUG=False`, domain in `ALLOWED_HOSTS`, HTTPS/HSTS, secure cookies, PostgreSQL, gunicorn instead of runserver. For Google OAuth add the production redirect URI (`https://domain/accounts/google/login/callback/`).


---

<a name="українська"></a>
Повнофункціональна соціальна мережа на Django: публікації з розумними медіа, чат у реальному часі через WebSocket, друзі та підписки, групи з модерацією, рейтинги й відгуки, сповіщення з налаштуваннями по типах, Google OAuth і система тем з 5 подвійними палітрами (світла + темна).

## Можливості

- **Авторизація**: локальна реєстрація з живою перевіркою доступності юзернейму, вхід, Google OAuth 2.0 (django-allauth, акаунт з аватаркою створюється автоматично при першому вході).
- **Стрічка та пости**: публікація тексту + медіа (зображення, відео, YouTube-вбудови, звичайні посилання), лайки, коментарі, поширення; головна для залогінених показує друзів/підписки/групи.
- **Друзі**: повний цикл — надіслати / прийняти / відхилити / скасувати / видалити, сторінка друзів із секціями вхідних/вихідних/друзів; підписки без додавання в друзі.
- **Групи**: список з пошуком, приєднання/вихід, пости для учасників, модерація власником/адмінами (видалення постів, кік учасників, призначення адмінів).
- **Чат**: приватні та групові розмови, створювані з друзів; повідомлення в реальному часі через WebSocket (Django Channels + Redis), вкладення-файли й зображення, збереження в БД, доступ лише учасникам.
- **Сповіщення**: лайки, коментарі, поширення, запити в друзі, підписки, повідомлення — з налаштуваннями по типах (вимкнути лайки/коментарі тощо) і живим бейджем непрочитаних через WebSocket.
- **Рейтинги й відгуки**: 1–5 зірок для постів і груп з текстовими відгуками; модерація staff-ом (сховати/показати).
- **Персоналізація**: `/settings/` — режим теми (світла / темна / як на пристрої через `prefers-color-scheme`) і 5 палітр (Фіолет, Океан, Ліс, Захід, Монохром зі справжнім чорним), кожна визначає обидва варіанти; миттєве прев'ю + автозбереження.
- **Пошук**: люди за юзернеймом/ім'ям/прізвищем і групи за назвою, з діями прямо в результатах.
- **Події**: віджет найближчих подій на головній (керуються через Django-адмінку).

## Технології

Django 6 + Django Channels (ASGI/Daphne), django-allauth, SQLite (розробка) / готово до PostgreSQL, Bootstrap 5 + темизація через CSS-змінні, шрифт Inter, Sentry SDK (опційно), E2E-тести на Playwright.

## Швидкий старт (Docker)

```bash
cp .env.example .env        # заповнити DJANGO_SECRET_KEY (обов'язково) і Google-ключі
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser   # або засіяти демо-дані:
docker compose exec web python manage.py seed_demo          # 8 демо-юзерів, пости, чати, події (пароль: demo-pass-123)
```

Відкрити http://localhost:8000 — адмінка на `/admin/`. Сервіси: `web` (Django + Daphne, порт 8000), `redis` (channel layer).

Без Docker: venv + `pip install -r requirements.txt`, локальний Redis на `redis://127.0.0.1:6379` (потрібен для WebSocket-чату).

## Змінні середовища (`.env`)

| Змінна | Призначення |
|---|---|
| `DJANGO_SECRET_KEY` | обов'язкова — без неї застосунок не стартує |
| `DJANGO_DEBUG` / `DJANGO_ALLOWED_HOSTS` | режими оточення |
| `REDIS_URL` | channel layer для WS-чату (за замовчуванням `redis://127.0.0.1:6379`) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth-клієнт Google; redirect URI: `http://localhost:8000/accounts/google/login/callback/` |
| `SENTRY_DSN` | ініціалізація Sentry; порожня — SDK вимкнено |
| `SENTRY_ENVIRONMENT` / `SENTRY_TRACES_SAMPLE_RATE` | параметри Sentry |

## Архітектура

- `network/models.py` — профілі, соціальний граф, пости, групи, чати, сповіщення, рейтинги, події.
- `network/views.py`, `forms.py`, `urls.py` — серверна логіка, CSRF-захищені форми, контроль доступу.
- `network/consumers.py` + `routing.py` — WebSocket-чат (авторизація + перевірка учасників, збереження) і сповіщення в реальному часі.
- `network/adapters.py` — allauth-адаптер (автоматичний Profile + аватарка Google).
- `network/management/commands/seed_demo.py` — реалістичний демо-контент; `--clean` видаляє залишки E2E.
- `templates/`, `static/css/` — Bootstrap 5 + палітри на CSS-змінних, мінімум JS (WebSocket-клієнти чату й сповіщень).
- `tests/e2e/` — наскрізні тести Playwright.

## Тестування

```bash
docker compose exec web python manage.py test     # 72 юніт-тести
# E2E (проти запущеного сервера):
venv/Scripts/python -m pip install -r requirements-dev.txt
venv/Scripts/python -m playwright install chromium
venv/Scripts/python -m pytest tests/e2e -v        # 3 E2E, включно з чатом у реальному часі
```

Покриття E2E: головна + кнопка Google, реєстрація + публікація поста, повний флоу чату двох користувачів із перевіркою доставки наживо через WebSocket. Через `E2E_BASE_URL` можна цілитись на інший хост.

## Примітки для production

`DEBUG=False`, домен у `ALLOWED_HOSTS`, HTTPS/HSTS, secure cookies, PostgreSQL, gunicorn замість runserver. Для Google OAuth додати прод-redirect URI (`https://домен/accounts/google/login/callback/`).
