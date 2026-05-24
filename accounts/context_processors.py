from django.conf import settings


def recaptcha_site_key(request):
    return {
        "RECAPTCHA_SITE_KEY": getattr(settings, "RECAPTCHA_SITE_KEY", None),
        "RECAPTCHA_ENABLED": getattr(settings, "RECAPTCHA_ENABLED", True),
        "RECAPTCHA_VERSION": getattr(settings, "RECAPTCHA_VERSION", "v2"),
    }
