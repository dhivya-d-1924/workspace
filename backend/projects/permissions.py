from rest_framework import permissions


class IsProjectOwnerOrMember(permissions.BasePermission):
    """Read access for members/public, write access for owner + editors/admins."""

    def has_object_permission(self, request, view, obj):
        project = obj if hasattr(obj, "user_can_view") else obj.project
        if request.method in permissions.SAFE_METHODS:
            return project.user_can_view(request.user)
        return project.user_can_edit(request.user)


class IsProjectOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        project = obj if hasattr(obj, "owner") else obj.project
        return project.owner_id == request.user.id
