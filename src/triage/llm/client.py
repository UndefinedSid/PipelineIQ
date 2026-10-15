"""Unified LLM client interface and provider adapters."""

import abc
import json
import logging
import re
from typing import Optional
import httpx
from triage.config import settings
from triage.models import LLMTriageOutput, ErrorCategory
from triage.llm.prompts import TRIAGE_SYSTEM_PROMPT, build_triage_prompt

logger = logging.getLogger("triage.llm")


def clean_json_response(raw_text: str) -> str:
    """Removes markdown code fences if LLM wrapped JSON in ```json ... ```."""
    text = raw_text.strip()
    if text.startswith("```"):
        # Remove opening ``` or ```json
        text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
        # Remove closing ```
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


class BaseLLMClient(abc.ABC):
    """Abstract base class for LLM triage providers."""

    @abc.abstractmethod
    async def triage(self, log_snippet: str, failed_step_hint: str = "Unknown") -> LLMTriageOutput:
        """Analyzes log snippet and returns structured LLMTriageOutput."""
        pass


class MockLLMClient(BaseLLMClient):
    """Offline Mock LLM client for testing and CI without external API keys."""

    async def triage(self, log_snippet: str, failed_step_hint: str = "Unknown") -> LLMTriageOutput:
        snippet_lower = log_snippet.lower()
        if "exit code 137" in snippet_lower or "oom" in snippet_lower:
            return LLMTriageOutput(
                error_category=ErrorCategory.OUT_OF_MEMORY_OOM,
                confidence_score=0.96,
                summary="Build runner killed due to process memory exhaustion (OOM exit code 137).",
                failed_step="Docker Build & Test",
                root_cause_file=None,
                root_cause_line=None,
                suggested_fix="Increase container memory allocation in workflow YAML or optimize Docker heap space.",
                code_diff=None,
                reproduction_command="docker build -m 4g ."
            )
        elif "modulenotfounderror" in snippet_lower or "eresolve" in snippet_lower:
            return LLMTriageOutput(
                error_category=ErrorCategory.DEPENDENCY_CONFLICT,
                confidence_score=0.94,
                summary="Missing package dependency or version resolution conflict during install step.",
                failed_step="Install Dependencies",
                root_cause_file="requirements.txt",
                root_cause_line=1,
                suggested_fix="Add missing package to requirements.txt or run npm install --legacy-peer-deps.",
                code_diff="+ pytest-cov>=4.0.0\n",
                reproduction_command="pip install -r requirements.txt"
            )
        elif "assertionerror" in snippet_lower or "pytest" in snippet_lower:
            return LLMTriageOutput(
                error_category=ErrorCategory.TEST_ASSERTION_FAILURE,
                confidence_score=0.95,
                summary="Unit test assertion failed due to mismatch between expected and actual return values.",
                failed_step="Run Unit Tests",
                root_cause_file="tests/test_auth.py",
                root_cause_line=42,
                suggested_fix="Align returned status payload with expected test assertions.",
                code_diff="""--- a/app/auth.py
+++ b/app/auth.py
@@ -40,3 +40,3 @@
-    return {"status": "pending"}
+    return {"status": "success", "is_valid": True}
""",
                reproduction_command="pytest tests/test_auth.py -v"
            )
        else:
            return LLMTriageOutput(
                error_category=ErrorCategory.UNKNOWN_FAILURE,
                confidence_score=0.85,
                summary="Generic build step execution failure detected in log output.",
                failed_step=failed_step_hint,
                root_cause_file=None,
                root_cause_line=None,
                suggested_fix="Inspect error logs around the failed step.",
                code_diff=None,
                reproduction_command=None
            )


class OpenAILLMClient(BaseLLMClient):
    """OpenAI GPT-4o / GPT-4o-mini provider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAILLMClient")

    async def triage(self, log_snippet: str, failed_step_hint: str = "Unknown") -> LLMTriageOutput:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key, timeout=settings.LLM_TIMEOUT_SECONDS)
        prompt = build_triage_prompt(log_snippet, failed_step_hint)

        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        content = response.choices[0].message.content or "{}"
        cleaned = clean_json_response(content)
        data = json.loads(cleaned)
        return LLMTriageOutput.model_validate(data)


class OllamaLLMClient(BaseLLMClient):
    """Local Ollama instance provider (llama3, deepseek, mistral)."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL

    async def triage(self, log_snippet: str, failed_step_hint: str = "Unknown") -> LLMTriageOutput:
        prompt = build_triage_prompt(log_snippet, failed_step_hint)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "format": "json"
        }

        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data_resp = resp.json()
            content = data_resp.get("message", {}).get("content", "{}")
            cleaned = clean_json_response(content)
            data = json.loads(cleaned)
            return LLMTriageOutput.model_validate(data)


def get_llm_client(provider_name: Optional[str] = None) -> BaseLLMClient:
    """Factory method to resolve the configured LLM client."""
    provider = (provider_name or settings.LLM_PROVIDER).lower()
    if provider == "openai":
        return OpenAILLMClient()
    elif provider == "ollama":
        return OllamaLLMClient()
    elif provider == "mock":
        return MockLLMClient()
    else:
        logger.warning(f"Unknown LLM provider '{provider}', falling back to MockLLMClient")
        return MockLLMClient()
