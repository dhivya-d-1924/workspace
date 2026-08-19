import os

from django.conf import settings
from rest_framework import serializers

from .models import Comment, FileVersion, Project, ProjectFile, ProjectMember

RESERVED_PATH_CHARS = set('<>:"|?*')


class ProjectFileSlimSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectFile
        fields = ["id", "path", "language", "size_bytes", "updated_at"]


class ProjectFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectFile
        fields = ["id", "project", "path", "content", "language", "size_bytes", "created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "project", "size_bytes", "created_by", "created_at", "updated_at"]

    def validate_path(self, value):
        value = value.strip().lstrip("/")
        if not value:
            raise serializers.ValidationError("File path cannot be empty.")
        if len(value) > 500:
            raise serializers.ValidationError("File path is too long.")
        if any(c in RESERVED_PATH_CHARS for c in value):
            raise serializers.ValidationError('Path contains invalid characters: <>:"|?*')
        if ".." in value.split("/"):
            raise serializers.ValidationError("Path traversal ('..') is not allowed.")
        ext = os.path.splitext(value)[1].lower()
        if ext and ext not in settings.ALLOWED_SOURCE_EXTENSIONS:
            raise serializers.ValidationError(f"Unsupported file extension '{ext}'.")
        return value

    def validate_content(self, value):
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(value.encode("utf-8")) > max_bytes:
            raise serializers.ValidationError(f"File exceeds max size of {settings.MAX_UPLOAD_SIZE_MB}MB.")
        return value


class FileVersionSerializer(serializers.ModelSerializer):
    edited_by_username = serializers.CharField(source="edited_by.username", read_only=True)

    class Meta:
        model = FileVersion
        fields = ["id", "version_number", "change_summary", "edited_by_username", "content", "created_at"]


class ProjectMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = ProjectMember
        fields = ["id", "user", "username", "email", "role", "joined_at"]
        read_only_fields = ["id", "joined_at"]


class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id", "project", "file", "author", "author_username", "line_number",
            "body", "resolved", "parent", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "project", "author", "created_at", "updated_at"]

    def validate_body(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Comment cannot be empty.")
        if len(value) > 3000:
            raise serializers.ValidationError("Comment is too long (max 3000 characters).")
        return value


class ProjectListSerializer(serializers.ModelSerializer):
    file_count = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    role = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "name", "description", "language", "visibility", "is_archived",
            "tags", "owner", "owner_username", "file_count", "role", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]

    def get_file_count(self, obj):
        return obj.files.count()

    def get_role(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        if obj.owner_id == request.user.id:
            return "owner"
        membership = obj.members.filter(user=request.user).first()
        return membership.role if membership else None

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Project name must be at least 2 characters.")
        if len(value) > 150:
            raise serializers.ValidationError("Project name is too long.")
        return value


class ProjectDetailSerializer(ProjectListSerializer):
    files = ProjectFileSlimSerializer(many=True, read_only=True)
    members = ProjectMemberSerializer(many=True, read_only=True)

    class Meta(ProjectListSerializer.Meta):
        fields = ProjectListSerializer.Meta.fields + ["files", "members"]
