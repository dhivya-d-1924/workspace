from django.db import models


class SystemSetting(models.Model):
    """Simple key/value store for platform-wide admin-configurable settings."""

    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict)
    description = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key

    @classmethod
    def get_value(cls, key, default=None):
        obj = cls.objects.filter(key=key).first()
        return obj.value if obj else default

    @classmethod
    def set_value(cls, key, value, description=""):
        obj, _ = cls.objects.update_or_create(
            key=key, defaults={"value": value, "description": description}
        )
        return obj
