# UASocial — Django Social Network

**English** · [Українська](README.ua.md)

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
