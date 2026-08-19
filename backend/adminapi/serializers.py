from rest_framework import serializers

from accounts.models import User
from .models import SystemSetting


class AdminUserSerializer(serializers.ModelSerializer):
    project_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "role", "is_active", "is_active_developer",
            "is_staff", "date_joined", "last_login", "project_count",
        ]

    def get_project_count(self, obj):
        return obj.projects.count()


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["role", "is_active", "is_active_developer"]

    def validate_role(self, value):
        if value not in dict(User.ROLE_CHOICES):
            raise serializers.ValidationError("Invalid role.")
        return value


class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = ["id", "key", "value", "description", "updated_at"]
        read_only_fields = ["id", "updated_at"]

    def validate_key(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Key cannot be empty.")
        return value
