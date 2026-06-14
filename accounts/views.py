import re

from django.shortcuts import render, redirect
from django.conf import settings
from django.urls import reverse
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django import forms
from django.contrib import messages
from .models import User, EmailOTP
from .emails import generate_otp_code, send_otp_email
from .recaptcha import verify_recaptcha

MODEL_BACKEND = "django.contrib.auth.backends.ModelBackend"


def _mask_email(email):
    """Turn 'jane.doe@gmail.com' into 'ja***@gmail.com' for display."""
    if not email or "@" not in email:
        return email or ""
    local, domain = email.split("@", 1)
    head = local[:2] if len(local) > 2 else local[:1]
    return f"{head}***@{domain}"


def _issue_otp(user, recipient=None):
    """Create a fresh OTP for the user and email it (to `recipient` if given)."""
    code = generate_otp_code()
    otp = EmailOTP.objects.create(user=user, otp=code)
    send_otp_email(user, code, recipient=recipient)
    return otp


def _resend_remaining(user):
    """Seconds left before the user may request another code (0 = allowed now)."""
    cooldown = getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60)
    latest = user.email_otps.first()  # newest first (Meta.ordering)
    if not latest:
        return 0
    elapsed = (timezone.now() - latest.created_at).total_seconds()
    return max(0, int(cooldown - elapsed))


def _verify_code(user, entered):
    """
    Validate the entered code against the newest unverified OTP.

    On success the OTP is consumed (marked verified) and (True, None) returned.
    On failure nothing is consumed and (False, "<reason>") is returned, so the
    caller can keep the code alive for a retry.
    """
    entered = (entered or "").strip()
    otp_obj = user.email_otps.filter(is_verified=False).first()
    if not entered:
        return False, "Please enter the 6-digit code."
    if otp_obj is None:
        return False, "No active code. Please request a new one."
    if otp_obj.is_expired():
        return False, "This code has expired. Please request a new one."
    if entered != otp_obj.otp:
        return False, "Incorrect code. Please check and try again."
    otp_obj.is_verified = True
    otp_obj.save(update_fields=["is_verified"])
    return True, None


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com"}),
    )

    class Meta:
        model = User
        fields = ('username', 'email')

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class RecaptchaAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Users may log in with either their username or their email. The value
        # is still submitted as "username"; EmailBackend matches it against the
        # email and ModelBackend matches it against the username.
        self.fields["username"].label = "Username or Email"
        self.fields["username"].widget = forms.TextInput(
            attrs={"autofocus": True, "placeholder": "Username or email"}
        )

    def clean(self):
        token = self.data.get("g-recaptcha-response")
        result = verify_recaptcha(
            token=token,
            remoteip=self.request.META.get("REMOTE_ADDR"),
            expected_action="login",
        )
        if not result.ok:
            raise forms.ValidationError("reCAPTCHA verification failed. Please try again.")
        return super().clean()


class RecaptchaLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = RecaptchaAuthenticationForm


def signup(request):
    if request.method == 'POST':
        token = request.POST.get("g-recaptcha-response")
        result = verify_recaptcha(
            token=token,
            remoteip=request.META.get("REMOTE_ADDR"),
            expected_action="signup",
        )
        if not result.ok:
            messages.error(request, "reCAPTCHA verification failed. Please try again.")
            form = CustomUserCreationForm(request.POST)
            return render(request, "accounts/signup.html", {"form": form})

        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Create the account but keep it inactive until the email is
            # verified — an inactive user cannot authenticate/log in.
            user = form.save(commit=False)
            user.is_active = False
            user.is_email_verified = False
            user.save()

            try:
                _issue_otp(user)
            except Exception:
                # Account exists but the code didn't go out (e.g. SMTP issue).
                # Send them to the OTP screen where they can hit "Resend".
                messages.error(request, "We couldn't send your verification email. Please try Resend.")

            # Remember who is mid-verification across the redirect.
            request.session["pending_user_id"] = user.id
            return redirect("verify_otp")
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})


def verify_otp(request):
    """Screen shown after signup: enter the emailed code to activate the account."""
    user_id = request.session.get("pending_user_id")
    if not user_id:
        messages.error(request, "Your session expired. Please sign up again.")
        return redirect("signup")

    try:
        user = User.objects.get(id=user_id, is_active=False)
    except User.DoesNotExist:
        request.session.pop("pending_user_id", None)
        messages.error(request, "Account not found or already verified. Please log in.")
        return redirect("login")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "resend":
            remaining = _resend_remaining(user)
            if remaining > 0:
                messages.error(request, f"Please wait {remaining}s before requesting a new code.")
            else:
                try:
                    _issue_otp(user)
                    messages.success(request, "A new verification code has been sent.")
                except Exception:
                    messages.error(request, "We couldn't send the email right now. Please try again shortly.")
            return redirect("verify_otp")

        # Otherwise: verify the entered code.
        ok, error = _verify_code(user, request.POST.get("otp"))
        if not ok:
            messages.error(request, error)
            return redirect("verify_otp")

        user.is_active = True
        user.is_email_verified = True
        user.save(update_fields=["is_active", "is_email_verified"])
        request.session.pop("pending_user_id", None)
        login(request, user, backend=MODEL_BACKEND)
        messages.success(request, "Email verified! Welcome to Money Logger 🎉")
        return redirect("dashboard")

    context = {
        "masked_email": _mask_email(user.email),
        "resend_remaining": _resend_remaining(user),
        "expiry_minutes": getattr(settings, "OTP_EXPIRY_MINUTES", 10),
        "verify_heading": "Verify your email",
        "back_prompt": "Entered the wrong email?",
        "back_url": reverse("signup"),
        "back_label": "Start over",
    }
    return render(request, "accounts/verify_otp.html", context)

class ProfileForm(forms.ModelForm):
    """
    Lets a user fill in / update their email and mobile number.

    Email is required here even though it is nullable on the model: legacy
    accounts were created with only a username, and this form is how we get
    them to register one. Uniqueness is enforced against every other user.
    """

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com"}),
    )
    mobile_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "+91 98765 43210"}),
    )

    class Meta:
        model = User
        fields = ("email", "mobile_number")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email is required.")
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already linked to another account.")
        return email

    def clean_mobile_number(self):
        mobile = (self.cleaned_data.get("mobile_number") or "").strip()
        if not mobile:
            return None
        if not re.fullmatch(r"[0-9+\-\s()]{7,20}", mobile):
            raise forms.ValidationError("Enter a valid mobile number.")
        return mobile


@login_required
def profile(request):
    # The page hosts two independent forms; a hidden `form_type` field tells us
    # which one was submitted so we only validate/bind the relevant one.
    form = ProfileForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "password":
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Keep the user logged in after the password hash changes.
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully!")
                return redirect("profile")
            messages.error(request, "Please correct the errors below.")
        else:
            original_email = request.user.email
            form = ProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                new_email = form.cleaned_data["email"]
                new_mobile = form.cleaned_data["mobile_number"]
                email_changed = (new_email or "") != (original_email or "")

                # Mobile needs no verification — save it right away. (ModelForm's
                # is_valid() already wrote new_email onto the instance in memory;
                # we revert that until the new address is confirmed by OTP.)
                request.user.email = original_email
                request.user.mobile_number = new_mobile
                request.user.save(update_fields=["mobile_number"])

                if email_changed:
                    request.session["email_change_target"] = new_email
                    try:
                        _issue_otp(request.user, recipient=new_email)
                    except Exception:
                        request.session.pop("email_change_target", None)
                        messages.error(request, "We couldn't send a code to that email. Please try again.")
                        return redirect("profile")
                    messages.info(request, "We sent a verification code to your new email.")
                    return redirect("verify_email_change")

                messages.success(request, "Profile updated successfully!")
                return redirect("profile")
            messages.error(request, "Please correct the errors below.")

    return render(request, "accounts/profile.html", {
        "form": form,
        "password_form": password_form,
        "active_page": "profile",
    })


@login_required
def verify_email_change(request):
    """Confirm a new email address (added/changed on the profile page) via OTP."""
    target = request.session.get("email_change_target")
    if not target:
        messages.error(request, "No email change in progress.")
        return redirect("profile")

    user = request.user

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "resend":
            remaining = _resend_remaining(user)
            if remaining > 0:
                messages.error(request, f"Please wait {remaining}s before requesting a new code.")
            else:
                try:
                    _issue_otp(user, recipient=target)
                    messages.success(request, "A new verification code has been sent.")
                except Exception:
                    messages.error(request, "We couldn't send the email right now. Please try again shortly.")
            return redirect("verify_email_change")

        ok, error = _verify_code(user, request.POST.get("otp"))
        if not ok:
            messages.error(request, error)
            return redirect("verify_email_change")

        # Re-check uniqueness in case the address got claimed during verification.
        if User.objects.filter(email__iexact=target).exclude(pk=user.pk).exists():
            request.session.pop("email_change_target", None)
            messages.error(request, "That email was just linked to another account.")
            return redirect("profile")

        user.email = target
        user.is_email_verified = True
        user.save(update_fields=["email", "is_email_verified"])
        request.session.pop("email_change_target", None)
        messages.success(request, "Email verified and saved!")
        return redirect("profile")

    context = {
        "masked_email": _mask_email(target),
        "resend_remaining": _resend_remaining(user),
        "expiry_minutes": getattr(settings, "OTP_EXPIRY_MINUTES", 10),
        "verify_heading": "Confirm your email",
        "back_prompt": "Changed your mind?",
        "back_url": reverse("profile"),
        "back_label": "Back to profile",
    }
    return render(request, "accounts/verify_otp.html", context)


def logout_view(request):
    logout(request)
    return redirect('login')


def forgot_password(request):
    """Step 1 of password reset: enter the account email, we send an OTP."""
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()

        if not email:
            messages.error(request, "Please enter your email.")
            return render(request, "accounts/forgot_password.html")

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            messages.error(request, "No account found with that email.")
            return render(request, "accounts/forgot_password.html", {"email": email})

        request.session["pwd_reset_user_id"] = user.id
        try:
            _issue_otp(user)
        except Exception:
            messages.error(request, "We couldn't send the verification code. Please try again.")
            return render(request, "accounts/forgot_password.html", {"email": email})

        messages.info(request, "We sent a verification code to your email.")
        return redirect("reset_password")

    return render(request, "accounts/forgot_password.html")


def reset_password(request):
    """Step 2 of password reset: confirm the OTP and set a new password."""
    user_id = request.session.get("pwd_reset_user_id")
    if not user_id:
        messages.error(request, "Your reset session expired. Please start again.")
        return redirect("forgot_password")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        request.session.pop("pwd_reset_user_id", None)
        messages.error(request, "Account not found. Please start again.")
        return redirect("forgot_password")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "resend":
            remaining = _resend_remaining(user)
            if remaining > 0:
                messages.error(request, f"Please wait {remaining}s before requesting a new code.")
            else:
                try:
                    _issue_otp(user)
                    messages.success(request, "A new verification code has been sent.")
                except Exception:
                    messages.error(request, "We couldn't send the email right now. Please try again shortly.")
            return redirect("reset_password")

        entered = request.POST.get("otp")
        p1 = request.POST.get("new_password1") or ""
        p2 = request.POST.get("new_password2") or ""

        # Validate the password fields BEFORE consuming the OTP, so a typo in the
        # password doesn't burn the code and force a resend.
        if not p1 or not p2:
            messages.error(request, "Please enter and confirm your new password.")
        elif p1 != p2:
            messages.error(request, "Passwords do not match.")
        elif len(p1) < 8:
            messages.error(request, "Password must be at least 8 characters.")
        else:
            ok, error = _verify_code(user, entered)
            if not ok:
                messages.error(request, error)
            else:
                user.set_password(p1)
                # Resetting via an emailed code also proves they own the address.
                user.is_email_verified = True
                if not user.is_active:
                    user.is_active = True
                user.save()
                request.session.pop("pwd_reset_user_id", None)
                messages.success(request, "Password reset successfully! Please log in.")
                return redirect("login")

        return redirect("reset_password")

    context = {
        "masked_email": _mask_email(user.email),
        "resend_remaining": _resend_remaining(user),
        "expiry_minutes": getattr(settings, "OTP_EXPIRY_MINUTES", 10),
    }
    return render(request, "accounts/reset_password.html", context)
