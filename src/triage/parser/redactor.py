"""Secret and credential redactor for security compliance."""

import re
from typing import List, Tuple

# Pre-compiled high-precision secret patterns
REDACTION_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # AWS Access Key ID
    (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "[REDACTED_AWS_KEY]"),
    # AWS Secret Access Key
    (re.compile(r"(?i)aws_secret_access_key\s*=\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"), "aws_secret_access_key=[REDACTED_AWS_SECRET]"),
    # GitHub Tokens (ghp, gho, ghu, ghs, ghr)
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,255})\b"), "[REDACTED_GITHUB_TOKEN]"),
    # OpenAI and generic API Keys
    (re.compile(r"\b(sk-(?:proj-)?[a-zA-Z0-9_-]{32,64})\b"), "[REDACTED_API_KEY]"),
    # Slack Webhooks
    (re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9]+/[A-Za-z0-9]+/[A-Za-z0-9]+"), "[REDACTED_SLACK_WEBHOOK]"),
    # Bearer Tokens
    (re.compile(r"\bBearer\s+([A-Za-z0-9\-._~+/]+=*)\b", re.IGNORECASE), "Bearer [REDACTED_BEARER_TOKEN]"),
    # PEM Private Keys
    (re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|DSA|PRIVATE) KEY-----[\s\S]*?-----END [^\n]+-----"), "[REDACTED_PRIVATE_KEY]"),
    # URL credentials: https://user:password@example.com
    (re.compile(r"(https?://[^:]+:)([^@]+)(@)"), r"\1[REDACTED_PASSWORD]\3"),
    # Common secret environment variable assignments in logs
    (re.compile(r"(?i)(password|secret|token|api_key|private_key)\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?"), r"\1=[REDACTED_SECRET_VALUE]"),
]


def redact_secrets(log_text: str) -> str:
    """Masks secrets and credentials in the log before passing to LLMs."""
    if not log_text:
        return ""

    sanitized = log_text
    for pattern, replacement in REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized
