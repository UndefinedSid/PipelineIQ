"""Unit tests for secret and credential redaction."""

from triage.parser.redactor import redact_secrets


def test_redact_aws_keys():
    text = "Deploying to AWS using AKIAIOSFODNN7EXAMPLE key"
    redacted = redact_secrets(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "[REDACTED_AWS_KEY]" in redacted


def test_redact_github_token():
    text = "Authenticating with ghp_1234567890abcdefghijklmnopqrstuvwxyz..."
    redacted = redact_secrets(text)
    assert "ghp_1234567890" not in redacted
    assert "[REDACTED_GITHUB_TOKEN]" in redacted


def test_redact_api_keys_and_bearer_tokens():
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0 and sk-abcdef1234567890abcdef1234567890"
    redacted = redact_secrets(text)
    assert "Bearer [REDACTED_BEARER_TOKEN]" in redacted
    assert "[REDACTED_API_KEY]" in redacted


def test_redact_password_in_url():
    text = "Cloning repository from https://gituser:supersecretpass123@github.com/org/repo.git"
    redacted = redact_secrets(text)
    assert "supersecretpass123" not in redacted
    assert "https://gituser:[REDACTED_PASSWORD]@github.com/org/repo.git" in redacted
