from rest_framework.permissions import BasePermission


class IsPlatformAdmin(BasePermission):
    message = "Only platform administrators can access this resource."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)
