import time

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from accounts.models import ActivityLog
from projects.models import CodeReview, Project, ProjectFile
from . import analyzers, generators
from .ai_client import enrich_with_llm
from .models import AIRequest
from .serializers import (
    CodeInputSerializer,
    ConvertCodeInputSerializer,
    ErrorExplainInputSerializer,
    GenerateCodeInputSerializer,
    SQLGenerateInputSerializer,
)


class AIFeatureThrottle(UserRateThrottle):
    scope = "ai_feature"


class BaseAIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIFeatureThrottle]
    feature_name = "explain_code"
    input_serializer_class = CodeInputSerializer
    use_llm_enrichment = True

    def resolve_project_and_file(self, validated_data):
        project = None
        file_obj = None
        project_id = validated_data.get("project_id")
        file_id = validated_data.get("file_id")
        if project_id:
            project = Project.objects.filter(id=project_id).first()
            if project and not project.user_can_view(self.request.user):
                project = None
        if file_id and project:
            file_obj = ProjectFile.objects.filter(id=file_id, project=project).first()
        return project, file_obj

    def run_feature(self, code, language, validated_data):
        raise NotImplementedError

    def post(self, request):
        serializer = self.input_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        started = time.monotonic()
        status_val, error_message, result = "success", "", {}
        try:
            result = self.run_feature(data.get("code", ""), data.get("language", "python"), data)
        except Exception as exc:  # noqa: BLE001
            status_val, error_message = "error", str(exc)
            result = {"error": error_message}

        duration_ms = int((time.monotonic() - started) * 1000)
        project, file_obj = (None, None)
        if hasattr(self, "input_serializer_class") and "project_id" in data:
            project, file_obj = self.resolve_project_and_file(data)

        engine_used = result.pop("engine_used", "heuristic") if isinstance(result, dict) else "heuristic"

        AIRequest.objects.create(
            user=request.user, project=project, file=file_obj, feature=self.feature_name,
            language=data.get("language", ""), input_summary=(data.get("code") or data.get("prompt") or data.get("error_message", ""))[:255],
            output=result if isinstance(result, dict) else {"result": result},
            status=status_val, error_message=error_message[:500], engine_used=engine_used, duration_ms=duration_ms,
        )
        ActivityLog.objects.create(
            user=request.user, action="ai_request", description=f"Used AI feature: {self.feature_name}",
            metadata={"feature": self.feature_name}, ip_address=getattr(request, "client_ip", None),
        )

        http_status = status.HTTP_200_OK if status_val == "success" else status.HTTP_422_UNPROCESSABLE_ENTITY
        return Response({"success": status_val == "success", "feature": self.feature_name, "duration_ms": duration_ms, "result": result}, status=http_status)


class ExplainCodeView(BaseAIView):
    feature_name = "explain_code"

    def run_feature(self, code, language, data):
        result = generators.explain_code(code, language)
        if self.use_llm_enrichment:
            result = enrich_with_llm("explain_code", code, language, result)
        return result


class FindBugsView(BaseAIView):
    feature_name = "find_bugs"

    def run_feature(self, code, language, data):
        result = generators.find_bugs(code, language)
        return enrich_with_llm("find_bugs", code, language, result) if self.use_llm_enrichment else result


class FixBugsView(BaseAIView):
    feature_name = "fix_bugs"

    def run_feature(self, code, language, data):
        return generators.fix_bugs(code, language)


class OptimizeCodeView(BaseAIView):
    feature_name = "optimize_code"

    def run_feature(self, code, language, data):
        result = generators.optimize_code(code, language)
        return enrich_with_llm("optimize_code", code, language, result) if self.use_llm_enrichment else result


class GenerateCodeView(BaseAIView):
    feature_name = "generate_code"
    input_serializer_class = GenerateCodeInputSerializer

    def run_feature(self, code, language, data):
        return generators.generate_code(data["prompt"], data.get("language", "python"))


class ConvertCodeView(BaseAIView):
    feature_name = "convert_code"
    input_serializer_class = ConvertCodeInputSerializer

    def run_feature(self, code, language, data):
        return generators.convert_code(data["code"], data["source_language"], data["target_language"])


class GenerateCommentsView(BaseAIView):
    feature_name = "generate_comments"

    def run_feature(self, code, language, data):
        return generators.generate_comments(code, language)


class GenerateDocumentationView(BaseAIView):
    feature_name = "generate_documentation"

    def run_feature(self, code, language, data):
        return generators.generate_documentation(code, language)


class GenerateTestsView(BaseAIView):
    feature_name = "generate_tests"

    def run_feature(self, code, language, data):
        return generators.generate_test_cases(code, language)


class GenerateSQLView(BaseAIView):
    feature_name = "generate_sql"
    input_serializer_class = SQLGenerateInputSerializer

    def run_feature(self, code, language, data):
        return generators.generate_sql(data["prompt"], data.get("schema"))


class ExplainErrorView(BaseAIView):
    feature_name = "explain_error"
    input_serializer_class = ErrorExplainInputSerializer

    def run_feature(self, code, language, data):
        return generators.explain_error(data["error_message"], data.get("language", "python"))


class SecurityScanView(BaseAIView):
    feature_name = "security_scan"

    def run_feature(self, code, language, data):
        issues = analyzers.scan_secrets_and_security(code)
        by_severity = {}
        for i in issues:
            by_severity[i["severity"]] = by_severity.get(i["severity"], 0) + 1
        result = {"issues": issues, "total": len(issues), "by_severity": by_severity}
        return enrich_with_llm("security_scan", code, language, result) if self.use_llm_enrichment else result


class QualityScoreView(BaseAIView):
    feature_name = "quality_score"

    def run_feature(self, code, language, data):
        bugs = generators.find_bugs(code, language)["bugs"]
        security = analyzers.scan_secrets_and_security(code)
        complexity = analyzers.python_complexity(code) if language == "python" else analyzers.generic_complexity(code, language)
        return analyzers.quality_score(code, language, bugs=bugs, security_issues=security, complexity=complexity)


class ComplexityAnalysisView(BaseAIView):
    feature_name = "complexity_analysis"

    def run_feature(self, code, language, data):
        return analyzers.python_complexity(code) if language == "python" else analyzers.generic_complexity(code, language)


class CodeReviewView(BaseAIView):
    """Aggregates every static-analysis dimension into one persisted CodeReview."""
    feature_name = "code_review"

    def run_feature(self, code, language, data):
        bugs = generators.find_bugs(code, language)["bugs"]
        security = analyzers.scan_secrets_and_security(code)
        complexity = analyzers.python_complexity(code) if language == "python" else analyzers.generic_complexity(code, language)
        quality = analyzers.quality_score(code, language, bugs=bugs, security_issues=security, complexity=complexity)
        optimize = generators.optimize_code(code, language)
        explanation = generators.explain_code(code, language)

        review = {
            "quality_score": quality["score"],
            "grade": quality["grade"],
            "quality_breakdown": quality["breakdown"],
            "complexity": complexity,
            "bugs": bugs,
            "security_issues": security,
            "optimization_suggestions": optimize["suggestions"],
            "summary": quality["notes"],
            "explanation": explanation.get("summary", ""),
        }
        result = enrich_with_llm("code_review", code, language, review) if self.use_llm_enrichment else review

        project, file_obj = self.resolve_project_and_file(data)
        if project:
            CodeReview.objects.create(
                project=project, file=file_obj, reviewer=self.request.user,
                summary=result.get("ai_narrative") or " ".join(quality["notes"]),
                quality_score=quality["score"], complexity_score=complexity.get("average_complexity", 0),
                security_issues=security, bugs_found=bugs, suggestions=optimize["suggestions"],
            )
        return result


class AIUsageHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        requests_qs = AIRequest.objects.filter(user=request.user)[:50]
        from .serializers import AIRequestSerializer
        return Response({"success": True, "history": AIRequestSerializer(requests_qs, many=True).data})
