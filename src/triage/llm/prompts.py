"""Prompt templates and structured schema definitions for LLM Triage."""

import json

TRIAGE_SYSTEM_PROMPT = """You are a Principal DevOps, Site Reliability, and Software Engineer.
Your job is to analyze failed CI/CD build logs, diagnose the exact root cause, categorize the failure, and produce an actionable fix with a code diff.

CRITICAL RULES:
1. Always return a single, valid JSON object strictly matching the provided JSON schema.
2. Do not include markdown code block formatting (like ```json ... ```) in your raw output. Output only the raw JSON string.
3. Be concise and accurate. Do not hallucinate file paths or line numbers not referenced in the log.
4. If a file or line number is not identifiable from the log, use null.
5. In 'code_diff', provide a realistic Unified Diff (- old, + new) if the fix is obvious from the stack trace.
6. The 'error_category' MUST be one of:
   - "SYNTAX_COMPILE_ERROR"
   - "TEST_ASSERTION_FAILURE"
   - "DEPENDENCY_CONFLICT"
   - "OUT_OF_MEMORY_OOM"
   - "INFRA_TIMEOUT"
   - "PERMISSION_SECRET_MISSING"
   - "LINT_FORMAT_SECURITY"
   - "FLAKY_TRANSIENT_FAILURE"
   - "UNKNOWN_FAILURE"
"""

JSON_SCHEMA_DEFINITION = {
    "type": "object",
    "properties": {
        "error_category": {
            "type": "string",
            "enum": [
                "SYNTAX_COMPILE_ERROR",
                "TEST_ASSERTION_FAILURE",
                "DEPENDENCY_CONFLICT",
                "OUT_OF_MEMORY_OOM",
                "INFRA_TIMEOUT",
                "PERMISSION_SECRET_MISSING",
                "LINT_FORMAT_SECURITY",
                "FLAKY_TRANSIENT_FAILURE",
                "UNKNOWN_FAILURE"
            ]
        },
        "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "summary": {"type": "string", "description": "1-2 sentence executive explanation of the root cause."},
        "failed_step": {"type": "string", "description": "The pipeline step or command that failed."},
        "root_cause_file": {"type": ["string", "null"], "description": "File path where the defect originated."},
        "root_cause_line": {"type": ["integer", "null"], "description": "Line number of the failure."},
        "suggested_fix": {"type": "string", "description": "Plain English explanation of the fix."},
        "code_diff": {"type": ["string", "null"], "description": "Unified diff showing fix."},
        "reproduction_command": {"type": ["string", "null"], "description": "Command to run locally."}
    },
    "required": ["error_category", "confidence_score", "summary", "failed_step", "suggested_fix"]
}


def build_triage_prompt(sanitized_log_snippet: str, failed_step_hint: str = "Unknown") -> str:
    """Builds the user prompt for the LLM."""
    return f"""Analyze the following sanitized CI/CD build failure log snippet:

Failed Step Context: {failed_step_hint}

Log Snippet:
----------------------------------------
{sanitized_log_snippet}
----------------------------------------

Output a strict JSON object complying with this schema:
{json.dumps(JSON_SCHEMA_DEFINITION, indent=2)}
"""
