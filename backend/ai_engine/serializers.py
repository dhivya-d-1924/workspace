from rest_framework import serializers

from .models import AIRequest

LANGUAGES = [
    "python", "javascript", "typescript", "java", "c", "cpp", "csharp",
    "go", "ruby", "php", "sql", "html", "other",
]


class CodeInputSerializer(serializers.Serializer):
    code = serializers.CharField(allow_blank=False, trim_whitespace=False)
    language = serializers.ChoiceField(choices=LANGUAGES, default="python")
    project_id = serializers.IntegerField(required=False, allow_null=True)
    file_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_code(self, value):
        if not value.strip():
            raise serializers.ValidationError("Code cannot be empty.")
        if len(value) > 200_000:
            raise serializers.ValidationError("Code is too large for analysis (max ~200,000 characters).")
        return value


class GenerateCodeInputSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=2000)
    language = serializers.ChoiceField(choices=LANGUAGES, default="python")

    def validate_prompt(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Please describe what you want in a bit more detail (5+ characters).")
        return value


class ConvertCodeInputSerializer(serializers.Serializer):
    code = serializers.CharField()
    source_language = serializers.ChoiceField(choices=LANGUAGES)
    target_language = serializers.ChoiceField(choices=LANGUAGES)

    def validate(self, attrs):
        if attrs["source_language"] == attrs["target_language"]:
            raise serializers.ValidationError("Source and target language must be different.")
        return attrs


class SQLGenerateInputSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=1000)
    schema = serializers.DictField(child=serializers.ListField(child=serializers.CharField()), required=False)


class ErrorExplainInputSerializer(serializers.Serializer):
    error_message = serializers.CharField(max_length=5000)
    language = serializers.ChoiceField(choices=LANGUAGES, default="python")


class AIRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIRequest
        fields = ["id", "feature", "language", "input_summary", "status", "engine_used", "duration_ms", "created_at"]
