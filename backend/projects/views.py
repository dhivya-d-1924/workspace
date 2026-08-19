import io
import os
import zipfile

from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import ActivityLog, User
from .models import Comment, FileVersion, Project, ProjectFile, ProjectMember
from .permissions import IsProjectOwner, IsProjectOwnerOrMember
from .serializers import (
    CommentSerializer,
    FileVersionSerializer,
    ProjectDetailSerializer,
    ProjectFileSerializer,
    ProjectListSerializer,
    ProjectMemberSerializer,
)

EXT_LANGUAGE_MAP = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".java": "java", ".c": "c", ".cpp": "cpp", ".cs": "csharp",
    ".go": "go", ".rb": "ruby", ".php": "php", ".sql": "sql", ".html": "html", ".css": "html",
}


def log_activity(user, action_name, description, metadata=None, request=None):
    ActivityLog.objects.create(
        user=user, action=action_name, description=description, metadata=metadata or {},
        ip_address=getattr(request, "client_ip", None) if request else None,
    )


class ProjectViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsProjectOwnerOrMember]
    filterset_fields = ["language", "visibility", "is_archived"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "updated_at", "name"]

    def get_serializer_class(self):
        return ProjectDetailSerializer if self.action == "retrieve" else ProjectListSerializer

    def get_queryset(self):
        user = self.request.user
        return Project.objects.filter(
            Q(owner=user) | Q(members__user=user) | Q(visibility="public")
        ).distinct()

    def perform_create(self, serializer):
        project = serializer.save(owner=self.request.user)
        log_activity(self.request.user, "project_create", f"Created project '{project.name}'", request=self.request)

    def perform_update(self, serializer):
        project = serializer.save()
        log_activity(self.request.user, "project_update", f"Updated project '{project.name}'", request=self.request)

    def perform_destroy(self, instance):
        name = instance.name
        instance.delete()
        log_activity(self.request.user, "project_delete", f"Deleted project '{name}'", request=self.request)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """Downloads the whole project as a .zip archive."""
        project = self.get_object()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in project.files.all():
                zf.writestr(f.path, f.content)
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{project.name}.zip"'
        return response

    @action(detail=True, methods=["post"])
    def share(self, request, pk=None):
        """Adds a member to the project by username or email (Collaboration: Share project)."""
        project = self.get_object()
        if project.owner_id != request.user.id:
            return Response({"success": False, "message": "Only the owner can share this project."}, status=403)

        identifier = request.data.get("user")
        role = request.data.get("role", "viewer")
        if role not in dict(ProjectMember.ROLE_CHOICES):
            return Response({"success": False, "message": "Invalid role."}, status=400)

        target = User.objects.filter(Q(username=identifier) | Q(email=identifier)).first()
        if not target:
            return Response({"success": False, "message": "User not found."}, status=404)
        if target.id == project.owner_id:
            return Response({"success": False, "message": "Owner already has full access."}, status=400)

        member, created = ProjectMember.objects.update_or_create(
            project=project, user=target, defaults={"role": role, "invited_by": request.user}
        )
        log_activity(request.user, "share", f"Shared '{project.name}' with {target.username} ({role})", request=request)
        return Response(ProjectMemberSerializer(member).data, status=201 if created else 200)

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        project = self.get_object()
        return Response(ProjectMemberSerializer(project.members.all(), many=True).data)

    @action(detail=True, methods=["delete"], url_path="members/(?P<member_id>[^/.]+)")
    def remove_member(self, request, pk=None, member_id=None):
        project = self.get_object()
        if project.owner_id != request.user.id:
            return Response({"success": False, "message": "Only the owner can remove members."}, status=403)
        ProjectMember.objects.filter(project=project, id=member_id).delete()
        return Response({"success": True})


class ProjectFileViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectFileSerializer
    permission_classes = [IsAuthenticated, IsProjectOwnerOrMember]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs["project_pk"])

    def get_queryset(self):
        project = self.get_project()
        return ProjectFile.objects.filter(project=project)

    def perform_create(self, serializer):
        project = self.get_project()
        self.check_object_permissions(self.request, project)
        file_obj = serializer.save(project=project, created_by=self.request.user)
        FileVersion.objects.create(
            file=file_obj, content=file_obj.content, version_number=1,
            change_summary="Initial version", edited_by=self.request.user,
        )
        log_activity(self.request.user, "file_create", f"Created file '{file_obj.path}'", request=self.request)

    def perform_update(self, serializer):
        instance = self.get_object()
        old_content = instance.content
        file_obj = serializer.save()
        if file_obj.content != old_content:
            last_version = file_obj.versions.first()
            next_num = (last_version.version_number + 1) if last_version else 1
            FileVersion.objects.create(
                file=file_obj, content=file_obj.content, version_number=next_num,
                change_summary=self.request.data.get("change_summary", "Edited"),
                edited_by=self.request.user,
            )
        log_activity(self.request.user, "file_update", f"Updated file '{file_obj.path}'", request=self.request)

    def perform_destroy(self, instance):
        path = instance.path
        instance.delete()
        log_activity(self.request.user, "file_delete", f"Deleted file '{path}'", request=self.request)

    @action(detail=False, methods=["post"])
    def upload(self, request, project_pk=None):
        """Uploads one or more source files into the project (Code Workspace: Upload source files)."""
        project = self.get_project()
        self.check_object_permissions(request, project)

        uploaded = request.FILES.getlist("files") or ([request.FILES["file"]] if "file" in request.FILES else [])
        if not uploaded:
            return Response({"success": False, "message": "No files provided."}, status=400)

        from django.conf import settings
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        created, errors = [], []

        for f in uploaded:
            if f.size > max_bytes:
                errors.append(f"{f.name}: exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit.")
                continue
            ext = os.path.splitext(f.name)[1].lower()
            if ext and ext not in settings.ALLOWED_SOURCE_EXTENSIONS:
                errors.append(f"{f.name}: unsupported extension '{ext}'.")
                continue
            try:
                content = f.read().decode("utf-8")
            except UnicodeDecodeError:
                errors.append(f"{f.name}: file is not valid UTF-8 text.")
                continue

            file_obj, was_created = ProjectFile.objects.update_or_create(
                project=project, path=f.name,
                defaults={"content": content, "language": EXT_LANGUAGE_MAP.get(ext, "other"), "created_by": request.user},
            )
            last_version = file_obj.versions.first()
            FileVersion.objects.create(
                file=file_obj, content=content, version_number=(last_version.version_number + 1 if last_version else 1),
                change_summary="Uploaded", edited_by=request.user,
            )
            created.append(file_obj.path)

        log_activity(request.user, "file_upload", f"Uploaded {len(created)} file(s) to '{project.name}'", request=request)
        return Response({"success": True, "created": created, "errors": errors}, status=201 if created else 400)

    @action(detail=True, methods=["get"])
    def download(self, request, project_pk=None, pk=None):
        file_obj = self.get_object()
        response = HttpResponse(file_obj.content, content_type="text/plain; charset=utf-8")
        filename = os.path.basename(file_obj.path)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["get"])
    def versions(self, request, project_pk=None, pk=None):
        file_obj = self.get_object()
        return Response(FileVersionSerializer(file_obj.versions.all(), many=True).data)

    @action(detail=True, methods=["post"], url_path="restore/(?P<version_number>[0-9]+)")
    def restore(self, request, project_pk=None, pk=None, version_number=None):
        file_obj = self.get_object()
        version = get_object_or_404(FileVersion, file=file_obj, version_number=version_number)
        file_obj.content = version.content
        file_obj.save()
        last_version = file_obj.versions.first()
        FileVersion.objects.create(
            file=file_obj, content=file_obj.content, version_number=last_version.version_number + 1,
            change_summary=f"Restored to v{version_number}", edited_by=request.user,
        )
        return Response(ProjectFileSerializer(file_obj).data)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsProjectOwnerOrMember]

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs["project_pk"])

    def get_queryset(self):
        return Comment.objects.filter(project=self.get_project())

    def perform_create(self, serializer):
        project = self.get_project()
        self.check_object_permissions(self.request, project)
        comment = serializer.save(project=project, author=self.request.user)
        log_activity(self.request.user, "comment", f"Commented on '{project.name}'", request=self.request)
