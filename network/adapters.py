import io
import uuid

import requests
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from PIL import Image

from .models import Profile

AVATAR_MAX_BYTES = 5 * 1024 * 1024
AVATAR_FETCH_TIMEOUT = 10


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Створює Profile для Google-користувачів і підтягує їхню аватарку."""

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        self.setup_profile(sociallogin)
        return user

    def setup_profile(self, sociallogin):
        profile, _ = Profile.objects.get_or_create(user=sociallogin.user)
        picture = sociallogin.account.extra_data.get("picture", "")
        if picture and not profile.avatar:
            url = self.download_avatar(picture)
            if url:
                profile.avatar = url
                profile.save()

    def download_avatar(self, picture_url):
        """Завантажує аватар із зовнішнього URL на локальний MEDIA_ROOT.

        Повертає URL збереженого файлу або '' за будь-якої помилки —
        зовнішній URL ніколи не зберігається в БД (захист від SSRF/CSP).
        """
        try:
            resp = requests.get(picture_url, timeout=AVATAR_FETCH_TIMEOUT)
            resp.raise_for_status()
            if not resp.headers.get("Content-Type", "").lower().startswith("image/"):
                return ""
            if len(resp.content) > AVATAR_MAX_BYTES:
                return ""
            Image.open(io.BytesIO(resp.content)).verify()
        except Exception:
            return ""
        storage = FileSystemStorage(
            location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL
        )
        name = f"avatars/{uuid.uuid4().hex}.jpg"
        storage.save(name, ContentFile(resp.content))
        return storage.url(name)
