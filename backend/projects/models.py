from django.conf import settings
from django.db import models

LANGUAGE_CHOICES = (
    ("python", "Python"),
    ("javascript", "JavaScript"),
    ("typescript", "TypeScript"),
    ("java", "Java"),
    ("c", "C"),
    ("cpp", "C++"),
    ("csharp", "C#"),
    ("go", "Go"),
    ("ruby", "Ruby"),
    ("php", "PHP"),
    ("sql", "SQL"),
    ("html", "HTML/CSS"),
    ("other", "Other"),
)


class Project(models.Model):
    VISIBILITY_CHOICES = (("private", "Private"), ("shared", "Shared"), ("public", "Public"))

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default="python")
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default="private")
    is_archived = models.BooleanField(default=False)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ("owner", "name")
        indexes = [models.Index(fields=["owner", "-updated_at"])]

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

    def user_can_edit(self, user):
        if self.owner_id == user.id:
            return True
        return self.members.filter(user=user, role__in=["editor", "admin"]).exists()

    def user_can_view(self, user):
        if self.owner_id == user.id or self.visibility == "public":
            return True
        return self.members.filter(user=user).exists()


class ProjectFile(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="files")
    path = models.CharField(max_length=500, help_text="Relative path, e.g. src/main.py")
    content = models.TextField(blank=True, default="")
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default="python")
    size_bytes = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["path"]
        unique_together = ("project", "path")

    def __str__(self):
        return f"{self.project.name}/{self.path}"

    def save(self, *args, **kwargs):
        self.size_bytes = len(self.content.encode("utf-8"))
        super().save(*args, **kwargs)


class FileVersion(models.Model):
    """Snapshot of a file's content — powers 'Code version history'."""

    file = models.ForeignKey(ProjectFile, on_delete=models.CASCADE, related_name="versions")
    content = models.TextField(blank=True, default="")
    version_number = models.PositiveIntegerField()
    change_summary = models.CharField(max_length=255, blank=True, default="")
    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = ("file", "version_number")

    def __str__(self):
        return f"{self.file.path} v{self.version_number}"


class ProjectMember(models.Model):
    ROLE_CHOICES = (("viewer", "Viewer"), ("editor", "Editor"), ("admin", "Admin"))

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="viewer")
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "user")

    def __str__(self):
        return f"{self.user.username} -> {self.project.name} ({self.role})"


class Comment(models.Model):
    """Line-level or file-level review comments (Collaboration module)."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="comments")
    file = models.ForeignKey(ProjectFile, on_delete=models.CASCADE, related_name="comments", null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    line_number = models.PositiveIntegerField(null=True, blank=True)
    body = models.TextField()
    resolved = models.BooleanField(default=False)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.project.name}"


class CodeReview(models.Model):
    """Result of running the 'AI code review' feature over a file/project."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="reviews")
    file = models.ForeignKey(ProjectFile, on_delete=models.CASCADE, related_name="reviews", null=True, blank=True)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    summary = models.TextField(blank=True, default="")
    quality_score = models.FloatField(default=0)
    complexity_score = models.FloatField(default=0)
    security_issues = models.JSONField(default=list, blank=True)
    bugs_found = models.JSONField(default=list, blank=True)
    suggestions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review of {self.project.name} @ {self.created_at:%Y-%m-%d}"
