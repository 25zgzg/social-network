"""Простий in-memory rate limiter (без зовнішніх залежностей).

Для багатопроцесного production замінити на Redis-бекенд (див. README).
Правила: POST-запити — 60/хв на IP глобально, 10/хв на /accounts/;
GET /check-username/ — 30/хв на IP (анти-енумерація).

IP береться лише з REMOTE_ADDR: заголовок X-Forwarded-For керується
клієнтом і дозволяє обходити ліміт підміною значення. Якщо застосунок
стоїть за проксі (Nginx/Caddy), проксі має перезаписувати/очищати XFF
на кордоні мережі, а сама лічба все одно ведеться за REMOTE_ADDR.
"""
import threading
import time

from django.http import HttpResponse

_WINDOW = 60
_RULES = {'POST': 60, 'LOGIN': 10, 'CHECK': 30}
_hits = {}
_lock = threading.Lock()


def _key(ip, bucket):
    return f'{ip}|{bucket}'


def _too_many(ip, bucket, limit):
    now = time.monotonic()
    with _lock:
        key = _key(ip, bucket)
        hits = [t for t in _hits.get(key, []) if now - t < _WINDOW]
        if len(hits) >= limit:
            _hits[key] = hits
            return True
        hits.append(now)
        _hits[key] = hits
        return False


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = request.META.get('REMOTE_ADDR', '')
        path = request.path
        if request.method == 'POST':
            if path.startswith('/accounts/') and _too_many(ip, 'login', _RULES['LOGIN']):
                return HttpResponse('Забагато запитів, спробуйте за хвилину.', status=429)
            if _too_many(ip, 'post', _RULES['POST']):
                return HttpResponse('Забагато запитів, спробуйте за хвилину.', status=429)
        elif path.startswith('/check-username/'):
            if _too_many(ip, 'check', _RULES['CHECK']):
                return HttpResponse('Забагато запитів.', status=429)
        return self.get_response(request)
