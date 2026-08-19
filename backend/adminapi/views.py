from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from ai_engine.models import AIRequest
from projects.models import CodeReview, Project, ProjectFile
from .models import SystemSetting
from .permissions import IsPlatformAdmin
from .serializers import AdminUserSerializer, AdminUserUpdateSerializer, SystemSettingSerializer


class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = AdminUserSerializer
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "email"]

    def get_queryset(self):
        return User.objects.all().order_by("-date_joined")


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    queryset = User.objects.all()

    def get_serializer_class(self):
        return AdminUserUpdateSerializer if self.request.method in ("PUT", "PATCH") else AdminUserSerializer

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.id == request.user.id:
            return Response({"success": False, "message": "You cannot delete your own account here."}, status=400)
        user.is_active = False
        user.save()
        return Response({"success": True, "message": "User deactivated."})


class AdminProjectListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    filterset_fields = ["language", "visibility", "is_archived"]
    search_fields = ["name", "owner__username"]

    def get_queryset(self):
        return Project.objects.all().order_by("-updated_at")

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        data = [{
            "id": p.id, "name": p.name, "owner": p.owner.username, "language": p.language,
            "visibility": p.visibility, "is_archived": p.is_archived, "file_count": p.files.count(),
            "member_count": p.members.count(), "created_at": p.created_at, "updated_at": p.updated_at,
        } for p in (page or qs)]
        return self.get_paginated_response(data) if page is not None else Response(data)


class AdminProjectActionView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request, pk):
        action = request.data.get("action")
        project = Project.objects.filter(pk=pk).first()
        if not project:
            return Response({"success": False, "message": "Project not found."}, status=404)

        if action == "archive":
            project.is_archived = True
            project.save()
        elif action == "unarchive":
            project.is_archived = False
            project.save()
        elif action == "delete":
            project.delete()
            return Response({"success": True, "message": "Project deleted."})
        else:
            return Response({"success": False, "message": "Unknown action."}, status=400)

        return Response({"success": True, "message": f"Project {action}d."})


class AIUsageStatisticsView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        since = timezone.now() - timedelta(days=days)
        qs = AIRequest.objects.filter(created_at__gte=since)

        by_feature = list(qs.values("feature").annotate(count=Count("id")).order_by("-count"))
        by_status = list(qs.values("status").annotate(count=Count("id")))
        by_engine = list(qs.values("engine_used").annotate(count=Count("id")))
        top_users = list(
            qs.values("user__username").annotate(count=Count("id")).order_by("-count")[:10]
        )
        daily = list(
            qs.extra(select={"day": "DATE(created_at)"}).values("day").annotate(count=Count("id")).order_by("day")
        )
        avg_duration = qs.aggregate(avg=Avg("duration_ms"))["avg"] or 0

        return Response({
            "success": True,
            "range_days": days,
            "total_requests": qs.count(),
            "average_duration_ms": round(avg_duration, 1),
            "by_feature": by_feature,
            "by_status": by_status,
            "by_engine": by_engine,
            "top_users": top_users,
            "daily_counts": daily,
        })


class ReviewStatisticsView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        qs = CodeReview.objects.all()
        agg = qs.aggregate(avg_quality=Avg("quality_score"), avg_complexity=Avg("complexity_score"))
        grade_buckets = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for score in qs.values_list("quality_score", flat=True):
            if score >= 90:
                grade_buckets["A"] += 1
            elif score >= 80:
                grade_buckets["B"] += 1
            elif score >= 70:
                grade_buckets["C"] += 1
            elif score >= 60:
                grade_buckets["D"] += 1
            else:
                grade_buckets["F"] += 1

        top_reviewed_projects = list(
            qs.values("project__name").annotate(count=Count("id"), avg_score=Avg("quality_score")).order_by("-count")[:10]
        )

        return Response({
            "success": True,
            "total_reviews": qs.count(),
            "average_quality_score": round(agg["avg_quality"] or 0, 1),
            "average_complexity": round(agg["avg_complexity"] or 0, 1),
            "grade_distribution": grade_buckets,
            "top_reviewed_projects": top_reviewed_projects,
        })


class SystemSettingsView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        settings_qs = SystemSetting.objects.all()
        return Response({"success": True, "settings": SystemSettingSerializer(settings_qs, many=True).data})

    def post(self, request):
        serializer = SystemSettingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = SystemSetting.set_value(
            serializer.validated_data["key"], serializer.validated_data["value"],
            serializer.validated_data.get("description", ""),
        )
        return Response(SystemSettingSerializer(obj).data, status=status.HTTP_201_CREATED)


class AdminOverviewView(APIView):
    """One-shot summary for the admin landing page."""
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        return Response({
            "success": True,
            "total_users": User.objects.count(),
            "active_users_7d": User.objects.filter(last_login__gte=timezone.now() - timedelta(days=7)).count(),
            "total_projects": Project.objects.count(),
            "total_files": ProjectFile.objects.count(),
            "total_ai_requests": AIRequest.objects.count(),
            "total_reviews": CodeReview.objects.count(),
            "requests_today": AIRequest.objects.filter(created_at__date=timezone.now().date()).count(),
        })
