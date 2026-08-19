from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ActivityLog, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "email", "role", "is_active_developer", "is_staff", "created_at"]
    list_filter = ["role", "is_active_developer", "is_staff"]
    fieldsets = UserAdmin.fieldsets + (
        ("Platform info", {"fields": ("role", "avatar_url", "bio", "job_title", "preferred_language", "is_active_developer")}),
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ["user", "action", "description", "created_at"]
    list_filter = ["action"]
    search_fields = ["user__username", "description"]
