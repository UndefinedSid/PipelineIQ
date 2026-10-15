"""Deterministic regex heuristic engine for 0ms classification."""

import re
from typing import List, Optional
from pydantic import BaseModel
from triage.models import ErrorCategory


class HeuristicMatch(BaseModel):
    category: ErrorCategory
    confidence: float
    summary: str
    suggested_fix: str
    reproduction_command: Optional[str] = None
    root_cause_file: Optional[str] = None
    root_cause_line: Optional[int] = None


class HeuristicRule:
    def __init__(
        self,
        category: ErrorCategory,
        patterns: List[re.Pattern],
        summary_template: str,
        fix_template: str,
        repro_command: Optional[str] = None,
        confidence: float = 0.95
    ):
        self.category = category
        self.patterns = patterns
        self.summary_template = summary_template
        self.fix_template = fix_template
        self.repro_command = repro_command
        self.confidence = confidence

    def match(self, text: str) -> Optional[HeuristicMatch]:
        for pattern in self.patterns:
            m = pattern.search(text)
            if m:
                groups = m.groupdict() if m.groupdict() else {}
                try:
                    summary = self.summary_template.format(**groups) if groups else self.summary_template
                    fix = self.fix_template.format(**groups) if groups else self.fix_template
                except KeyError:
                    summary = self.summary_template
                    fix = self.fix_template

                return HeuristicMatch(
                    category=self.category,
                    confidence=self.confidence,
                    summary=summary,
                    suggested_fix=fix,
                    reproduction_command=self.repro_command
                )
        return None


class HeuristicEngine:
    """Pre-compiled rule set for fast deterministic categorization."""

    def __init__(self):
        self.rules: List[HeuristicRule] = [
            # 1. Out of Memory (OOM)
            HeuristicRule(
                category=ErrorCategory.OUT_OF_MEMORY_OOM,
                patterns=[
                    re.compile(r"exit code 137", re.IGNORECASE),
                    re.compile(r"OOMKilled:\s*true", re.IGNORECASE),
                    re.compile(r"JavaScript heap out of memory", re.IGNORECASE),
                    re.compile(r"java\.lang\.OutOfMemoryError", re.IGNORECASE),
                    re.compile(r"Killed process \d+ \([\w\-]+\) total-vm:\d+", re.IGNORECASE),
                ],
                summary_template="Process was terminated by the Linux OOM-Killer (Out of Memory) or exceeded heap memory limits.",
                fix_template="Increase memory allocation for the job/runner (e.g. NODE_OPTIONS='--max-old-space-size=4096' or upgrade GitHub runner instance).",
                repro_command="docker run --memory=4g <image_name>",
                confidence=0.98
            ),

            # 2. Permission & Missing Secrets
            HeuristicRule(
                category=ErrorCategory.PERMISSION_SECRET_MISSING,
                patterns=[
                    re.compile(r"401 Unauthorized", re.IGNORECASE),
                    re.compile(r"403 Forbidden", re.IGNORECASE),
                    re.compile(r"Permission denied \(publickey\)", re.IGNORECASE),
                    re.compile(r"AccessDeniedException", re.IGNORECASE),
                    re.compile(r"docker login failed", re.IGNORECASE),
                ],
                summary_template="CI job encountered an authorization/permission denial (HTTP 401/403 or invalid credentials).",
                fix_template="Verify that all required environment secrets (e.g., GITHUB_TOKEN, DOCKERHUB_TOKEN, API keys) are configured under repository Settings -> Secrets.",
                repro_command=None,
                confidence=0.95
            ),

            # 3. Dependency Conflict & Missing Modules
            HeuristicRule(
                category=ErrorCategory.DEPENDENCY_CONFLICT,
                patterns=[
                    re.compile(r"ModuleNotFoundError: No module named ['\"](?P<mod>[^'\"]+)['\"]"),
                    re.compile(r"npm ERR! code ERESOLVE"),
                    re.compile(r"Could not find a version that satisfies the requirement (?P<mod>[\w\-\.]+)"),
                    re.compile(r"Cannot find module '(?P<mod>[^']+)'"),
                    re.compile(r"go: (?P<mod>[^:]+): cannot find module"),
                ],
                summary_template="Missing dependency or package version resolution conflict.",
                fix_template="Add the missing package to requirements.txt / package.json / go.mod or run lockfile reconciliation.",
                repro_command="pip install -r requirements.txt || npm install",
                confidence=0.92
            ),

            # 4. Syntax & Compile Errors
            HeuristicRule(
                category=ErrorCategory.SYNTAX_COMPILE_ERROR,
                patterns=[
                    re.compile(r"SyntaxError: (?P<msg>[^\n]+)"),
                    re.compile(r"error TS\d+:"),
                    re.compile(r"javac: error"),
                    re.compile(r"rustc: error:"),
                    re.compile(r"cannot find symbol\s+symbol:\s+class"),
                ],
                summary_template="Compilation or syntax check failed due to invalid language tokens or type mismatch.",
                fix_template="Check the source file for typos, invalid syntax tokens, or missing imports.",
                repro_command="npm run build || python -m py_compile <file>",
                confidence=0.95
            ),

            # 5. Infrastructure & Timeouts
            HeuristicRule(
                category=ErrorCategory.INFRA_TIMEOUT,
                patterns=[
                    re.compile(r"The operation was canceled after \d+ minutes"),
                    re.compile(r"ETIMEDOUT"),
                    re.compile(r"Connection timed out"),
                    re.compile(r"DeadlineExceeded"),
                ],
                summary_template="The workflow exceeded its maximum allowed execution timeout or network request hung.",
                fix_template="Increase job 'timeout-minutes' in workflow yaml, check for infinite loops in test suites, or verify external network availability.",
                repro_command=None,
                confidence=0.90
            ),

            # 6. Linting & Security Tools
            HeuristicRule(
                category=ErrorCategory.LINT_FORMAT_SECURITY,
                patterns=[
                    re.compile(r"flake8.*found \d+ errors"),
                    re.compile(r"ESLint:.*found \d+ errors"),
                    re.compile(r"Bandit.*High severity"),
                    re.compile(r"Trivy.*CRITICAL"),
                    re.compile(r"black --check failed"),
                ],
                summary_template="Code quality, formatting, or security scanner failed policy thresholds.",
                fix_template="Run code formatters/linters locally (`black .`, `npm run lint:fix`) and resolve security CVEs.",
                repro_command="flake8 . || npm run lint",
                confidence=0.95
            ),

            # 7. Flaky & Transient Network Failures
            HeuristicRule(
                category=ErrorCategory.FLAKY_TRANSIENT_FAILURE,
                patterns=[
                    re.compile(r"Connection reset by peer", re.IGNORECASE),
                    re.compile(r"ECONNRESET", re.IGNORECASE),
                    re.compile(r"502 Bad Gateway", re.IGNORECASE),
                    re.compile(r"503 Service Unavailable", re.IGNORECASE),
                ],
                summary_template="Encountered transient infrastructure or socket connection disruption.",
                fix_template="Re-run the failed GitHub Actions job. If recurring, add retry logic to network requests.",
                repro_command=None,
                confidence=0.88
            ),

            # 8. Test Assertion Failures
            HeuristicRule(
                category=ErrorCategory.TEST_ASSERTION_FAILURE,
                patterns=[
                    re.compile(r"=== FAILURES ==="),
                    re.compile(r"AssertionError:"),
                    re.compile(r"pytest\.fail"),
                    re.compile(r"FAIL: test_"),
                    re.compile(r"Expected: .* Received: .*"),
                ],
                summary_template="Automated unit or integration test assertion failed.",
                fix_template="Inspect the failing assertion in the test suite and align implementation logic or fixtures.",
                repro_command="pytest -v || npm test",
                confidence=0.90
            ),
        ]

    def classify(self, text: str) -> Optional[HeuristicMatch]:
        """Runs the rule matcher in strict priority sequence."""
        for rule in self.rules:
            match = rule.match(text)
            if match:
                return match
        return None
