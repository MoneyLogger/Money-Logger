from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username',)

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')


def forgot_password(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password1 = request.POST.get("new_password1")
        password2 = request.POST.get("new_password2")

        if not username:
            messages.error(request, "Please enter your username.")
            return render(request, "accounts/forgot_password.html")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, "No account found with that username.")
            return render(request, "accounts/forgot_password.html")

        if not password1 or not password2:
            messages.error(request, "Please enter and confirm your new password.")
            return render(request, "accounts/forgot_password.html", {"username": username})

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, "accounts/forgot_password.html", {"username": username})

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "accounts/forgot_password.html", {"username": username})

        user.set_password(password1)
        user.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Password reset successfully! Please log in.")
        return redirect("login")

    return render(request, "accounts/forgot_password.html")