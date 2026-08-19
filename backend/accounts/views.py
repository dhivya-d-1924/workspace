from django.conf import settings
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from ai_engine.models import AIRequest
from projects.models import Project, CodeReview
from .models import ActivityLog, User
from .serializers import (
    ActivityLogSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UserProfileSerializer,
)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"success": True, "message": "Account created successfully.",
             "user": UserProfileSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """Blacklists the refresh token (requires token_blacklist app)."""

    def post(self, request):
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"success": False, "message": "Refresh token required."}, status=400)
            token = RefreshToken(refresh_token)
            token.blacklist()
            ActivityLog.objects.create(user=request.user, action="logout", description="User logged out")
            return Response({"success": True, "message": "Logged out."})
        except Exception as exc:  # noqa: BLE001
            return Response({"success": False, "message": str(exc)}, status=400)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"success": True, "message": "Password updated."})


class ActivityHistoryView(generics.ListAPIView):
    serializer_class = ActivityLogSerializer

    def get_queryset(self):
        return ActivityLog.objects.filter(user=self.request.user)[:100]


class DashboardView(APIView):
    """Aggregates everything the dashboard screen needs in a single call."""

    def get(self, request):
        user = request.user
        projects = Project.objects.filter(owner=user)
        recent_projects = projects.order_by("-updated_at")[:5]
        recent_reviews = CodeReview.objects.filter(project__owner=user).order_by("-created_at")[:5]
        ai_usage_today = AIRequest.objects.filter(
            user=user, created_at__date=timezone.now().date()
        ).count()

        return Response({
            "success": True,
            "stats": {
                "total_projects": projects.count(),
                "total_files": sum(p.files.count() for p in projects),
                "total_reviews": CodeReview.objects.filter(project__owner=user).count(),
                "ai_requests_today": ai_usage_today,
                "ai_daily_quota": settings.AI_DAILY_QUOTA_PER_USER,
            },
            "recent_projects": [
                {"id": p.id, "name": p.name, "language": p.language, "updated_at": p.updated_at}
                for p in recent_projects
            ],
            "recent_reviews": [
                {
                    "id": r.id, "project": r.project.name, "score": r.quality_score,
                    "summary": r.summary[:160], "created_at": r.created_at,
                }
                for r in recent_reviews
            ],
            "recent_activity": ActivityLogSerializer(
                ActivityLog.objects.filter(user=user)[:10], many=True
            ).data,
        })
