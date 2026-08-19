from django.urls import path

from . import views

urlpatterns = [
    path("overview/", views.AdminOverviewView.as_view(), name="admin-overview"),
    path("users/", views.AdminUserListView.as_view(), name="admin-users"),
    path("users/<int:pk>/", views.AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("projects/", views.AdminProjectListView.as_view(), name="admin-projects"),
    path("projects/<int:pk>/action/", views.AdminProjectActionView.as_view(), name="admin-project-action"),
    path("stats/ai-usage/", views.AIUsageStatisticsView.as_view(), name="admin-ai-usage"),
    path("stats/reviews/", views.ReviewStatisticsView.as_view(), name="admin-review-stats"),
    path("settings/", views.SystemSettingsView.as_view(), name="admin-settings"),
]
