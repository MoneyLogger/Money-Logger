from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser

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

