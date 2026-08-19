from django.contrib import admin

from .models import Comment, CodeReview, FileVersion, Project, ProjectFile, ProjectMember

admin.site.register(Project)
admin.site.register(ProjectFile)
admin.site.register(FileVersion)
admin.site.register(ProjectMember)
admin.site.register(Comment)
admin.site.register(CodeReview)
