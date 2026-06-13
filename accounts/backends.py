from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """
    Authenticate using the email address instead of the username.

    Django's AuthenticationForm passes whatever was typed in the login form as
    `username`, so we treat that value as an email here. `username` remains the
    model's USERNAME_FIELD; this backend only changes how credentials are looked
    up. Kept alongside the default ModelBackend so admin/username login and
    allauth still work.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        email = kwargs.get("email") or username
        if email is None or password is None:
            return None
        try:
            user = UserModel.objects.get(email__iexact=email)
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce timing differences
            # between "no such email" and "wrong password".
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
