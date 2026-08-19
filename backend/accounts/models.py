from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user so we can extend it with product-specific fields."""

    ROLE_CHOICES = (
        ("developer", "Developer"),
        ("admin", "Admin"),
    )

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="developer")
    avatar_url = models.URLField(blank=True, default="")
    bio = models.TextField(blank=True, default="")
    job_title = models.CharField(max_length=120, blank=True, default="")
    preferred_language = models.CharField(max_length=40, blank=True, default="python")
    is_active_developer = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        indexes = [models.Index(fields=["email"]), models.Index(fields=["role"])]

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return self.role == "admin" or self.is_superuser


class ActivityLog(models.Model):
    """Tracks meaningful actions for the dashboard's 'activity history' feed."""

    ACTION_CHOICES = (
        ("login", "Login"),
        ("logout", "Logout"),
        ("register", "Registered"),
        ("project_create", "Created project"),
        ("project_update", "Updated project"),
        ("project_delete", "Deleted project"),
        ("file_create", "Created file"),
        ("file_update", "Updated file"),
        ("file_delete", "Deleted file"),
        ("file_upload", "Uploaded file"),
        ("ai_request", "Used AI feature"),
        ("share", "Shared project"),
        ("comment", "Added comment"),
        ("other", "Other"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_logs")
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, default="other")
    description = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.user.username} - {self.action} @ {self.created_at:%Y-%m-%d %H:%M}"
