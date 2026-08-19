import re

from django.contrib.auth import password_validation
from django.contrib.auth.models import update_last_login
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import ActivityLog, User

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.]{3,30}$")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password", "password_confirm"]

    def validate_username(self, value):
        if not USERNAME_RE.match(value):
            raise serializers.ValidationError(
                "Username must be 3-30 characters: letters, numbers, dot or underscore only."
            )
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        # Run Django's full password validation stack (length, common, numeric, similarity)
        password_validation.validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        ActivityLog.objects.create(user=user, action="register", description="Account created")
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    project_count = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "role",
            "avatar_url", "bio", "job_title", "preferred_language",
            "created_at", "project_count", "review_count",
        ]
        read_only_fields = ["id", "email", "role", "created_at"]

    def get_project_count(self, obj):
        return obj.projects.count()

    def get_review_count(self, obj):
        return obj.projects.aggregate_review_count() if hasattr(obj.projects, "aggregate_review_count") else 0


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate_new_password(self, value):
        password_validation.validate_password(value)
        return value


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = ["id", "action", "description", "metadata", "created_at"]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds user profile info to the JWT response and logs the login event."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        update_last_login(None, self.user)
        ActivityLog.objects.create(
            user=self.user,
            action="login",
            description="User logged in",
            ip_address=self.context["request"].client_ip if hasattr(self.context.get("request"), "client_ip") else None,
        )
        data["user"] = UserProfileSerializer(self.user).data
        return data
