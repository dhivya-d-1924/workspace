from django.urls import include, path
from rest_framework_nested import routers

from . import views

router = routers.SimpleRouter()
router.register(r"", views.ProjectViewSet, basename="project")

projects_router = routers.NestedSimpleRouter(router, r"", lookup="project")
projects_router.register(r"files", views.ProjectFileViewSet, basename="project-files")
projects_router.register(r"comments", views.CommentViewSet, basename="project-comments")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(projects_router.urls)),
]
