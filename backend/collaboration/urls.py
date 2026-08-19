from django.urls import path

from . import views

urlpatterns = [
    path("shared-projects/", views.SharedProjectsView.as_view(), name="shared-projects"),
    path("review-history/", views.ReviewHistoryView.as_view(), name="review-history"),
    path("activity/", views.TeamActivityView.as_view(), name="team-activity"),
]
