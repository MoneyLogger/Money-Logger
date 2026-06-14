"""
Custom django-allauth adapter for social (Google) login.

Google has already verified the user's email before handing it to us, so there
is no point asking for an email OTP on top. Instead we trust that verification
and mark the account active + email-verified automatically.
"""

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model


def _mark_verified(user):
    """Activate + flag a user as email-verified (Google already verified it)."""
    fields = []
    if user.email and not user.is_email_verified:
        user.is_email_verified = True
        fields.append("is_email_verified")
    if not user.is_active:
        user.is_active = True
        fields.append("is_active")
    if fields:
        user.save(update_fields=fields)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        # Runs when a brand-new account is created from a social login.
        user = super().save_user(request, sociallogin, form)
        _mark_verified(user)
        return user

    def pre_social_login(self, request, sociallogin):
        # Runs on every social login, before allauth decides to log in / sign up.
        super().pre_social_login(request, sociallogin)

        # Already linked to a local account → just ensure the flags are set.
        if sociallogin.is_existing:
            if sociallogin.user.pk:
                _mark_verified(sociallogin.user)
            return

        # Not linked yet. If a local account already uses this (Google-verified)
        # email, connect this Google login to it instead of showing the social
        # signup form — that avoids both the ImproperlyConfigured page and
        # duplicate/locked accounts.
        email = (sociallogin.user.email or "").strip()
        if not email:
            return
        User = get_user_model()
        try:
            existing = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return
        _mark_verified(existing)
        sociallogin.connect(request, existing)
