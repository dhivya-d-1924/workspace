from django.contrib import admin

from .models import AIRequest


@admin.register(AIRequest)
class AIRequestAdmin(admin.ModelAdmin):
    list_display = ["feature", "user", "language", "status", "engine_used", "duration_ms", "created_at"]
    list_filter = ["feature", "status", "engine_used"]
    search_fields = ["user__username"]
