from django.conf import settings
from django.db import models

FEATURE_CHOICES = (
    ("explain_code", "Explain code"),
    ("find_bugs", "Find bugs"),
    ("fix_bugs", "Fix bugs"),
    ("optimize_code", "Optimize code"),
    ("generate_code", "Generate code"),
    ("convert_code", "Convert code"),
    ("generate_comments", "Generate comments"),
    ("generate_documentation", "Generate documentation"),
    ("generate_tests", "Generate test cases"),
    ("generate_sql", "Generate SQL"),
    ("explain_error", "Explain error message"),
    ("security_scan", "Detect security issues"),
    ("quality_score", "Code quality score"),
    ("complexity_analysis", "Complexity analysis"),
    ("code_review", "AI code review"),
)


class AIRequest(models.Model):
    STATUS_CHOICES = (("success", "Success"), ("error", "Error"))

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_requests")
    project = models.ForeignKey("projects.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_requests")
    file = models.ForeignKey("projects.ProjectFile", on_delete=models.SET_NULL, null=True, blank=True)
    feature = models.CharField(max_length=30, choices=FEATURE_CHOICES)
    language = models.CharField(max_length=20, blank=True, default="")
    input_summary = models.CharField(max_length=255, blank=True, default="")
    output = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="success")
    error_message = models.CharField(max_length=500, blank=True, default="")
    engine_used = models.CharField(max_length=20, default="heuristic")  # heuristic | llm
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"]), models.Index(fields=["feature"])]

    def __str__(self):
        return f"{self.feature} by {self.user.username} @ {self.created_at:%Y-%m-%d %H:%M}"
