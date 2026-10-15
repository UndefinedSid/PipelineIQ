"""Unit tests for the LLM client and prompt handling."""

import pytest
from triage.llm.client import MockLLMClient, clean_json_response
from triage.llm.prompts import build_triage_prompt
from triage.models import ErrorCategory


def test_clean_json_response():
    markdown_wrapped = "```json\n{\"error_category\": \"OUT_OF_MEMORY_OOM\", \"confidence_score\": 0.9, \"summary\": \"OOM\", \"failed_step\": \"test\", \"suggested_fix\": \"fix\"}\n```"
    cleaned = clean_json_response(markdown_wrapped)
    assert cleaned.startswith("{")
    assert cleaned.endswith("}")


def test_build_triage_prompt():
    prompt = build_triage_prompt("Test error snippet", failed_step_hint="Pytest step")
    assert "Pytest step" in prompt
    assert "Test error snippet" in prompt
    assert "SYNTAX_COMPILE_ERROR" in prompt


@pytest.mark.asyncio
async def test_mock_llm_triage_oom():
    client = MockLLMClient()
    res = await client.triage("exit code 137: memory exhausted")
    assert res.error_category == ErrorCategory.OUT_OF_MEMORY_OOM
    assert res.confidence_score >= 0.90
    assert "memory" in res.summary.lower()


@pytest.mark.asyncio
async def test_mock_llm_triage_assertion():
    client = MockLLMClient()
    res = await client.triage("AssertionError: assert False is True in pytest")
    assert res.error_category == ErrorCategory.TEST_ASSERTION_FAILURE
    assert res.code_diff is not None
