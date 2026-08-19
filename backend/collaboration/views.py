from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import ActivityLog
from accounts.serializers import ActivityLogSerializer
from projects.models import CodeReview, Project
from projects.serializers import ProjectListSerializer


class SharedProjectsView(APIView):
    """Projects the current user collaborates on but doesn't own."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        projects = Project.objects.filter(members__user=request.user).exclude(owner=request.user).distinct()
        return Response({
            "success": True,
            "projects": ProjectListSerializer(projects, many=True, context={"request": request}).data,
        })


class ReviewHistoryView(APIView):
    """All AI code reviews across projects the user owns or is a member of."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        qs = CodeReview.objects.filter(
            Q(project__owner=request.user) | Q(project__members__user=request.user)
        ).distinct()
        if project_id:
            qs = qs.filter(project_id=project_id)

        data = [{
            "id": r.id,
            "project": r.project.name,
            "project_id": r.project_id,
            "file": r.file.path if r.file else None,
            "reviewer": r.reviewer.username if r.reviewer else None,
            "quality_score": r.quality_score,
            "complexity_score": r.complexity_score,
            "security_issue_count": len(r.security_issues or []),
            "bug_count": len(r.bugs_found or []),
            "summary": r.summary,
            "created_at": r.created_at,
        } for r in qs[:100]]

        return Response({"success": True, "reviews": data})


class TeamActivityView(APIView):
    """Activity feed for everyone collaborating on the user's projects (project owners see all activity)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        owned_project_ids = Project.objects.filter(owner=request.user).values_list("id", flat=True)

        if project_id and int(project_id) in list(owned_project_ids):
            project = Project.objects.get(id=project_id)
            member_ids = list(project.members.values_list("user_id", flat=True)) + [project.owner_id]
            qs = ActivityLog.objects.filter(user_id__in=member_ids)
        else:
            qs = ActivityLog.objects.filter(user=request.user)

        return Response({"success": True, "activity": ActivityLogSerializer(qs[:100], many=True).data})
