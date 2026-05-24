from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings


@dataclass(frozen=True)
class RecaptchaResult:
    ok: bool
    error_codes: list[str]
    score: float | None = None
    action: str | None = None


def verify_recaptcha(
    *,
    token: str | None,
    remoteip: str | None = None,
    expected_action: str | None = None,
) -> RecaptchaResult:
    if not getattr(settings, "RECAPTCHA_ENABLED", True):
        return RecaptchaResult(ok=True, error_codes=[])

    secret = getattr(settings, "RECAPTCHA_SECRET_KEY", None)
    if not secret:
        return RecaptchaResult(ok=False, error_codes=["missing-secret"])

    if not token:
        return RecaptchaResult(ok=False, error_codes=["missing-input-response"])

    data: dict[str, str] = {"secret": secret, "response": token}
    if remoteip:
        data["remoteip"] = remoteip

    try:
        resp = requests.post("https://www.google.com/recaptcha/api/siteverify", data=data, timeout=7)
        payload = resp.json()
    except Exception:
        return RecaptchaResult(ok=False, error_codes=["recaptcha-unreachable"])

    ok = bool(payload.get("success"))
    codes = payload.get("error-codes") or []
    if not isinstance(codes, list):
        codes = [str(codes)]
    score = payload.get("score")
    action = payload.get("action")
    try:
        score = float(score) if score is not None else None
    except (TypeError, ValueError):
        score = None

    if expected_action and action and action != expected_action:
        ok = False
        codes = [*codes, "action-mismatch"]

    if getattr(settings, "RECAPTCHA_VERSION", "v2") == "v3":
        min_score = float(getattr(settings, "RECAPTCHA_MIN_SCORE", 0.5))
        if score is None or score < min_score:
            ok = False
            codes = [*codes, "low-score"]

    return RecaptchaResult(ok=ok, error_codes=[str(c) for c in codes], score=score, action=action)
