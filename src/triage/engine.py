"""Core Triage Orchestrator Engine."""

import logging
import uuid
from typing import Optional
from triage.config import settings
from triage.models import TriageReport, ErrorContext, CodeFix, ErrorCategory
from triage.parser.sanitizer import sanitize_log
from triage.parser.redactor import redact_secrets
from triage.parser.chunker import extract_high_signal_window
from triage.parser.stacktrace_extractor import extract_stacktrace
from triage.classifier.heuristic_engine import HeuristicEngine
from triage.llm.client import get_llm_client, BaseLLMClient

logger = logging.getLogger("triage.engine")


class TriageEngine:
    """Orchestrates the entire end-to-end triage pipeline."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.heuristic_engine = HeuristicEngine()
        self.llm_client = llm_client or get_llm_client()

    async def triage_log(
        self,
        raw_log: str,
        failed_step_hint: str = "Unknown Pipeline Step",
        force_heuristics: bool = False
    ) -> TriageReport:
        """
        Executes the two-tier triage pipeline on a raw CI log.

        Steps:
        1. Sanitize ANSI codes and normalize newlines.
        2. Redact passwords, secrets, AWS keys, and tokens.
        3. Extract the high-signal reverse-tail window.
        4. Extract runtime-specific stack traces.
        5. Run Tier 1 Heuristic rule matcher.
        6. If applicable, run Tier 2 AI/LLM deep triage with automatic fallback.
        7. Synthesize and return the final TriageReport.
        """
        report_id = f"trg-{uuid.uuid4().hex[:8]}"

        # Step 1 & 2: Sanitize & Redact
        clean_text = sanitize_log(raw_log)
        safe_text = redact_secrets(clean_text)

        # Step 3 & 4: Chunker & Stacktrace
        snippet, total_lines, extracted_lines = extract_high_signal_window(
            safe_text,
            max_lines=settings.MAX_LOG_WINDOW_LINES,
            context_before=settings.CONTEXT_BEFORE_ERROR
        )
        stacktrace = extract_stacktrace(snippet)

        context = ErrorContext(
            failed_step=failed_step_hint,
            raw_error_snippet=snippet,
            extracted_stacktrace=stacktrace or "",
            total_log_lines=total_lines,
            extracted_lines=extracted_lines
        )

        # Step 5: Tier 1 Fast Heuristics
        heuristic_match = self.heuristic_engine.classify(snippet)

        # Check if we should skip LLM (deterministic high confidence or offline forced)
        if force_heuristics or (heuristic_match and heuristic_match.confidence >= 0.98 and settings.LLM_PROVIDER == "mock"):
            logger.info("Using Tier 1 Heuristic result (Deterministic / Fast-Path)")
            return TriageReport(
                id=report_id,
                error_category=heuristic_match.category,
                confidence_score=heuristic_match.confidence,
                summary=heuristic_match.summary,
                failed_step=failed_step_hint,
                root_cause_file=heuristic_match.root_cause_file,
                root_cause_line=heuristic_match.root_cause_line,
                suggested_fix=heuristic_match.suggested_fix,
                reproduction_command=heuristic_match.reproduction_command,
                triage_mode="HEURISTIC",
                context=context
            )

        # Step 6: Tier 2 AI Deep Triage with Automatic Fallback Circuit
        try:
            logger.info(f"Invoking LLM Triage ({settings.LLM_PROVIDER})...")
            llm_output = await self.llm_client.triage(
                log_snippet=snippet,
                failed_step_hint=failed_step_hint
            )

            code_fix = None
            if llm_output.code_diff:
                code_fix = CodeFix(
                    file_path=llm_output.root_cause_file,
                    line_number=llm_output.root_cause_line,
                    unified_diff=llm_output.code_diff
                )

            return TriageReport(
                id=report_id,
                error_category=llm_output.error_category,
                confidence_score=llm_output.confidence_score,
                summary=llm_output.summary,
                failed_step=llm_output.failed_step or failed_step_hint,
                root_cause_file=llm_output.root_cause_file,
                root_cause_line=llm_output.root_cause_line,
                suggested_fix=llm_output.suggested_fix,
                code_fix=code_fix,
                reproduction_command=llm_output.reproduction_command,
                triage_mode="AI_LLM",
                context=context
            )

        except Exception as e:
            logger.warning(f"LLM triage failed or timed out: {e}. Falling back to Tier 1 Heuristics.")

            # Graceful Fallback
            category = heuristic_match.category if heuristic_match else ErrorCategory.UNKNOWN_FAILURE
            summary = heuristic_match.summary if heuristic_match else "Build failed due to unclassified error in CI runner."
            fix = heuristic_match.suggested_fix if heuristic_match else "Inspect recent code changes and terminal stack traces."
            repro = heuristic_match.reproduction_command if heuristic_match else None
            conf = heuristic_match.confidence if heuristic_match else 0.70

            return TriageReport(
                id=report_id,
                error_category=category,
                confidence_score=conf,
                summary=summary,
                failed_step=failed_step_hint,
                root_cause_file=heuristic_match.root_cause_file if heuristic_match else None,
                root_cause_line=heuristic_match.root_cause_line if heuristic_match else None,
                suggested_fix=fix,
                reproduction_command=repro,
                triage_mode="HEURISTIC_FALLBACK",
                context=context
            )
