"""Helpers for generating and emailing signup verification OTPs."""

import secrets

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def generate_otp_code():
    """Return a cryptographically-random 6-digit code as a zero-padded string."""
    return f"{secrets.randbelow(1_000_000):06d}"


def send_otp_email(user, otp_code, recipient=None):
    """
    Send the OTP as a multipart (text + HTML) email.

    `recipient` overrides where the code is sent — used when confirming a *new*
    email address that isn't saved on the user yet (e.g. profile email change).
    Defaults to the user's current email.

    Raises on SMTP failure (fail_silently=False) so the caller can surface a
    "couldn't send email" message and let the user retry.
    """
    to_email = recipient or user.email
    expiry_minutes = getattr(settings, "OTP_EXPIRY_MINUTES", 10)
    context = {
        "otp": otp_code,
        "username": user.username,
        "expiry_minutes": expiry_minutes,
    }
    html_content = render_to_string("emails/otp_email.html", context)
    text_content = (
        f"Hi {user.username},\n\n"
        f"Your Money Logger verification code is: {otp_code}\n"
        f"This code expires in {expiry_minutes} minutes.\n\n"
        f"If you didn't request this, you can safely ignore this email."
    )

    message = EmailMultiAlternatives(
        subject="Money Logger — Email Verification Code",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(html_content, "text/html")
    message.send(fail_silently=False)
