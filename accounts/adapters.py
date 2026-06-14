"""
Custom django-allauth adapter for social (Google) login.

Google has already verified the user's email before handing it to us, so there
is no point asking for an email OTP on top. Instead we trust that verification
and mark the account active + email-verified automatically.
"""

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        # Runs when a brand-new account is created from a social login.
        user = super().save_user(request, sociallogin, form)
        fields = []
        if user.email and not user.is_email_verified:
            user.is_email_verified = True
            fields.append("is_email_verified")
        if not user.is_active:
            user.is_active = True
            fields.append("is_active")
        if fields:
            user.save(update_fields=fields)
        return user

    def pre_social_login(self, request, sociallogin):
        # Runs on every social login; ensure returning Google users are flagged.
        super().pre_social_login(request, sociallogin)
        user = sociallogin.user
        if user.pk and user.email and not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
