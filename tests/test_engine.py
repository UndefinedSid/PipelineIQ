"""Unit tests for the end-to-end triage orchestrator engine."""

import pytest
from triage.engine import TriageEngine
from triage.models import ErrorCategory
from triage.llm.client import MockLLMClient


@pytest.mark.asyncio
async def test_engine_triage_log_mock():
    engine = TriageEngine(llm_client=MockLLMClient())
    sample_log = """
    2026-10-09 05:00:00 [INFO] Starting test suite
    tests/test_auth.py:42: AssertionError: assert False is True
    ##[error]Process completed with exit code 1.
    """

    report = await engine.triage_log(sample_log, failed_step_hint="Pytest Step")

    assert report.id.startswith("trg-")
    assert report.error_category == ErrorCategory.TEST_ASSERTION_FAILURE
    assert report.failed_step != ""
    assert report.context.total_log_lines > 0
    assert report.context.extracted_lines > 0


@pytest.mark.asyncio
async def test_engine_triage_force_heuristics():
    engine = TriageEngine(llm_client=MockLLMClient())
    sample_log = "Killed process 100\nOOMKilled: true\nexit code 137"

    report = await engine.triage_log(sample_log, failed_step_hint="Build Docker Image", force_heuristics=True)

    assert report.triage_mode == "HEURISTIC"
    assert report.error_category == ErrorCategory.OUT_OF_MEMORY_OOM
    assert report.confidence_score >= 0.95
