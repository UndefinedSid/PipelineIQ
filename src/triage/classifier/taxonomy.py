"""Taxonomy definitions and category helpers."""

from triage.models import ErrorCategory

# Category display metadata
CATEGORY_METADATA = {
    ErrorCategory.OUT_OF_MEMORY_OOM: {
        "badge": "🔴 CRITICAL - OOM",
        "emoji": "💥",
        "description": "Process killed due to insufficient memory (RAM/Heap exhausted)."
    },
    ErrorCategory.PERMISSION_SECRET_MISSING: {
        "badge": "🟠 AUTH & PERMISSION",
        "emoji": "🔒",
        "description": "Authentication failure, missing GitHub Secret, or 401/403 HTTP error."
    },
    ErrorCategory.DEPENDENCY_CONFLICT: {
        "badge": "🔵 DEPENDENCY ISSUE",
        "emoji": "📦",
        "description": "Missing module, package version incompatibility, or lockfile mismatch."
    },
    ErrorCategory.SYNTAX_COMPILE_ERROR: {
        "badge": "🟣 SYNTAX / COMPILE",
        "emoji": "⚡",
        "description": "Syntax error, type checking failure, or compiler error."
    },
    ErrorCategory.TEST_ASSERTION_FAILURE: {
        "badge": "🟡 TEST FAILURE",
        "emoji": "🧪",
        "description": "Unit or integration test assertion failed."
    },
    ErrorCategory.INFRA_TIMEOUT: {
        "badge": "⏳ TIMEOUT",
        "emoji": "⏱️",
        "description": "Job or network operation exceeded time limit."
    },
    ErrorCategory.LINT_FORMAT_SECURITY: {
        "badge": "🟢 LINT & SECURITY",
        "emoji": "🛡️",
        "description": "Linter, formatter, or security vulnerability scan failed."
    },
    ErrorCategory.FLAKY_TRANSIENT_FAILURE: {
        "badge": "🔄 FLAKY / TRANSIENT",
        "emoji": "🔀",
        "description": "Intermittent network reset or transient runner issue."
    },
    ErrorCategory.UNKNOWN_FAILURE: {
        "badge": "❓ UNKNOWN",
        "emoji": "🔍",
        "description": "Unclassified build failure."
    }
}
