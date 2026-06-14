

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, EmailOTP

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'mobile_number', 'is_email_verified', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'is_email_verified', 'date_joined']


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'otp', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'otp']
    readonly_fields = ['created_at']

 