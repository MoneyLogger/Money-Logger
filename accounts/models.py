from datetime import timedelta

from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """
    Custom user model.

    Login is done by email (see accounts.backends.EmailBackend), but `username`
    remains Django's USERNAME_FIELD so existing users, admin and the allauth
    Google flow keep working. New signups auto-derive a username from the email.
    """

    # Override AbstractUser.email to make it unique. Nullable so existing
    # username-only users (and any account created without an email) are valid;
    # Postgres/SQLite allow multiple NULLs under a unique constraint.
    email = models.EmailField("email address", unique=True, null=True, blank=True)

    # Reserved for later use (SMS / phone login). Not collected at signup yet.
    mobile_number = models.CharField(max_length=20, null=True, blank=True)

    # Set True once the user has confirmed their email via an OTP. New signups
    # start False and stay inactive until they verify.
    is_email_verified = models.BooleanField(default=False)


class EmailOTP(models.Model):
    """A one-time 6-digit code emailed to a user to verify their address."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_otps",
    )
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def is_expired(self):
        minutes = getattr(settings, "OTP_EXPIRY_MINUTES", 10)
        return timezone.now() - self.created_at > timedelta(minutes=minutes)

    def __str__(self):
        return f"{self.user} - {self.otp}"
