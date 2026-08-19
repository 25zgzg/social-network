"""Віддає заголовок Content-Security-Policy зі settings.SECURE_CONTENT_SECURITY_POLICY.

Django не має вбудованого CSP, а додавати django-csp заради одного
заголовка немає сенсу — реалізація без зовнішніх залежностей.
Формат словника в settings: {директива: значення або список значень}.
"""
from django.conf import settings


class CSPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        policy = getattr(settings, 'SECURE_CONTENT_SECURITY_POLICY', {})
        parts = []
        for directive, values in policy.items():
            if isinstance(values, str):
                values = [values]
            parts.append(f"{directive} {' '.join(values)}")
        self.policy = '; '.join(parts)

    def __call__(self, request):
        response = self.get_response(request)
        if self.policy:
            response['Content-Security-Policy'] = self.policy
        return response