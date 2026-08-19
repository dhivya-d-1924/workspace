from django.urls import path

from . import views

urlpatterns = [
    path("explain/", views.ExplainCodeView.as_view(), name="ai-explain"),
    path("find-bugs/", views.FindBugsView.as_view(), name="ai-find-bugs"),
    path("fix-bugs/", views.FixBugsView.as_view(), name="ai-fix-bugs"),
    path("optimize/", views.OptimizeCodeView.as_view(), name="ai-optimize"),
    path("generate-code/", views.GenerateCodeView.as_view(), name="ai-generate-code"),
    path("convert/", views.ConvertCodeView.as_view(), name="ai-convert"),
    path("generate-comments/", views.GenerateCommentsView.as_view(), name="ai-generate-comments"),
    path("generate-docs/", views.GenerateDocumentationView.as_view(), name="ai-generate-docs"),
    path("generate-tests/", views.GenerateTestsView.as_view(), name="ai-generate-tests"),
    path("generate-sql/", views.GenerateSQLView.as_view(), name="ai-generate-sql"),
    path("explain-error/", views.ExplainErrorView.as_view(), name="ai-explain-error"),
    path("security-scan/", views.SecurityScanView.as_view(), name="ai-security-scan"),
    path("quality-score/", views.QualityScoreView.as_view(), name="ai-quality-score"),
    path("complexity/", views.ComplexityAnalysisView.as_view(), name="ai-complexity"),
    path("code-review/", views.CodeReviewView.as_view(), name="ai-code-review"),
    path("history/", views.AIUsageHistoryView.as_view(), name="ai-history"),
]
