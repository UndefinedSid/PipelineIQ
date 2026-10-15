"""Domain models and Pydantic schemas for CI/CD Failure Triage."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ErrorCategory(str, Enum):
    SYNTAX_COMPILE_ERROR = "SYNTAX_COMPILE_ERROR"
    TEST_ASSERTION_FAILURE = "TEST_ASSERTION_FAILURE"
    DEPENDENCY_CONFLICT = "DEPENDENCY_CONFLICT"
    OUT_OF_MEMORY_OOM = "OUT_OF_MEMORY_OOM"
    INFRA_TIMEOUT = "INFRA_TIMEOUT"
    PERMISSION_SECRET_MISSING = "PERMISSION_SECRET_MISSING"
    LINT_FORMAT_SECURITY = "LINT_FORMAT_SECURITY"
    FLAKY_TRANSIENT_FAILURE = "FLAKY_TRANSIENT_FAILURE"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


class CodeFix(BaseModel):
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    old_code: Optional[str] = None
    new_code: Optional[str] = None
    unified_diff: Optional[str] = None


class ErrorContext(BaseModel):
    failed_step: str = "Unknown Pipeline Step"
    command: Optional[str] = None
    raw_error_snippet: str = ""
    extracted_stacktrace: str = ""
    total_log_lines: int = 0
    extracted_lines: int = 0


class LLMTriageOutput(BaseModel):
    error_category: ErrorCategory
    confidence_score: float = Field(ge=0.0, le=1.0)
    summary: str
    failed_step: str
    root_cause_file: Optional[str] = None
    root_cause_line: Optional[int] = None
    suggested_fix: str
    code_diff: Optional[str] = None
    reproduction_command: Optional[str] = None


class TriageReport(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_category: ErrorCategory
    confidence_score: float = 1.0
    summary: str
    failed_step: str
    root_cause_file: Optional[str] = None
    root_cause_line: Optional[int] = None
    suggested_fix: str
    code_fix: Optional[CodeFix] = None
    reproduction_command: Optional[str] = None
    triage_mode: str = "AI_LLM"  # "AI_LLM", "HEURISTIC", "HEURISTIC_FALLBACK"
    context: ErrorContext
    metadata: Dict[str, Any] = Field(default_factory=dict)
