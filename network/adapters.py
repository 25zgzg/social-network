from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from .models import Profile


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Створює Profile для Google-користувачів і підтягує їхню аватарку."""

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        self.setup_profile(sociallogin)
        return user

    def setup_profile(self, sociallogin):
        profile, _ = Profile.objects.get_or_create(user=sociallogin.user)
        picture = sociallogin.account.extra_data.get('picture', '')
        if picture and not profile.avatar:
            profile.avatar = picture
            profile.save()
