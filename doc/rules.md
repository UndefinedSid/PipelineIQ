# System & Triage Rules
## AI-Powered CI/CD Build Failure Triage Assistant

**Version:** 1.0.0  
**Scope:** Operational Rules, Sanitization Rules, Heuristic Priority, LLM Guardrails & Security Compliance

---

## 1. Log Ingestion & Token Optimization Rules

### 1.1 Reverse Tail Scanning (Rule TR-01)
- CI logs can range from 10,000 to 100,000 lines. The root cause is almost always in the **last 200–500 lines** or near the last occurrence of fatal keywords.
- **Rule**: Never pass raw uncompressed logs to an LLM.
- **Execution**:
  1. Scan log from end to start to find the primary error anchor (`FAILED`, `Error:`, `Traceback`, `npm ERR!`, `BUILD FAILED`, `panic:`).
  2. Extract a sliding window of **50 lines before** the anchor (context) and **150 lines after** the anchor (stack trace/details).
  3. Cap the final payload to **maximum 4,000 characters** (~1,000 tokens) to guarantee blazing fast inference and minimal API cost (< $0.002 per triage).

### 1.2 ANSI & Terminal Strip Rules (Rule TR-02)
- All terminal color escape codes (e.g. `\x1b[31m`, `\x1b[0m`, `\033[...m`) MUST be stripped using strict regex before parsing.
- Carriage returns (`\r\n` -> `\n`, `\r` overwrites) must be normalized.

---

## 2. Security & Redaction Rules (Rule SEC-01)

### 2.1 Mandatory Pre-LLM Masking
Before any log slice is stored, logged, or dispatched to an LLM provider, it must pass through the Redactor pipeline.

| Secret Type | Pattern / Identifier | Replacement Token |
|---|---|---|
| **AWS Access Key** | `AKIA[0-9A-Z]{16}` | `[REDACTED_AWS_KEY]` |
| **AWS Secret Key** | `(?i)aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{40}` | `[REDACTED_AWS_SECRET]` |
| **GitHub Token** | `gh[pousr]_[A-Za-z0-9_]{36,255}` | `[REDACTED_GITHUB_TOKEN]` |
| **OpenAI / API Key** | `sk-[a-zA-Z0-9]{32,64}` or `sk-proj-[a-zA-Z0-9_-]{40,}` | `[REDACTED_API_KEY]` |
| **Generic Bearer Token** | `Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*` | `Bearer [REDACTED_TOKEN]` |
| **Private Keys** | `-----BEGIN (RSA\|OPENSSH\|PRIVATE) KEY-----[\s\S]*?-----END ...-----` | `[REDACTED_PRIVATE_KEY]` |
| **Password in URI** | `https?://[^:]+:([^@]+)@` | `https://user:[REDACTED_PASSWORD]@` |

### 2.2 Env Var Sanitization
- Lines matching patterns such as `export SECRET_.*=...`, `PASSWORD=...`, `AUTH_TOKEN=...` must have their values replaced with `[REDACTED_ENV_VALUE]`.

---

## 3. Heuristic Priority & Error Taxonomy Rules

The assistant follows a **Two-Tier Hybrid Triage Architecture**:
1. **Tier 1 (Instant Heuristics - 0ms, 0 Cost)**: Deterministic regex evaluation for high-frequency common errors.
2. **Tier 2 (AI Semantic Triage - LLM)**: Deep reasoning for subtle logic bugs, complex multi-file test failures, and customized code patch generation.

### 3.1 Taxonomy Classification Hierarchy (Rule CL-01)

When evaluating failure patterns, classify in the following strict precedence order:

1. **`OUT_OF_MEMORY_OOM`**:
   - Matches: `exit code 137`, `OOMKilled: true`, `JavaScript heap out of memory`, `java.lang.OutOfMemoryError`, `Killed process .* (oom-killer)`.
2. **`PERMISSION_SECRET_MISSING`**:
   - Matches: `HTTP 401 Unauthorized`, `HTTP 403 Forbidden`, `Permission denied (publickey)`, `AccessDeniedException`, `Docker login failed`.
3. **`DEPENDENCY_CONFLICT`**:
   - Matches: `ModuleNotFoundError: No module named`, `npm ERR! ERESOLVE`, `Could not resolve dependencies`, `pip._internal.exceptions.DistributionNotFound`, `Cannot find module`, `go: cannot find module`.
4. **`SYNTAX_COMPILE_ERROR`**:
   - Matches: `SyntaxError:`, `TypeScript error TS`, `javac: error`, `rustc: error:`, `cannot find symbol`, `g++: fatal error:`.
5. **`TEST_ASSERTION_FAILURE`**:
   - Matches: `pytest.fail`, `AssertionError:`, `FAILURES`, `junit.framework.AssertionFailedError`, `Expected: .* Received: .*`.
6. **`INFRA_TIMEOUT`**:
   - Matches: `The operation was canceled after .* minutes`, `Connection timed out`, `ETIMEDOUT`, `DeadlineExceeded`.
7. **`LINT_FORMAT_SECURITY`**:
   - Matches: `flake8: error`, `ESLint: found errors`, `Bandit: High severity issue`, `Trivy: CRITICAL vulnerability`.
8. **`FLAKY_TRANSIENT_FAILURE`**:
   - Matches: `Connection reset by peer`, `ECONNRESET`, `502 Bad Gateway`, `503 Service Unavailable`.

---

## 4. LLM Prompt & Guardrail Rules

### 4.1 Strict JSON Output (Rule LLM-01)
- The LLM MUST be instructed to return ONLY valid JSON matching the specified Pydantic schema without markdown formatting blocks (or wrapped in clean ```json blocks).
- If the LLM returns invalid JSON or halluncinates, the parser must retry once with json mode repair, and if it fails again, fallback to Tier 1 heuristic triage.

### 4.2 Hallucination & Code Patch Guardrails (Rule LLM-02)
- **Rule**: Never invent file names that do not appear in the log or git diff.
- **Rule**: If the exact line number is unknown, set `root_cause_line: null`.
- **Rule**: The `code_diff` must contain real syntax and strictly adhere to standard Unified Diff format (`- old` / `+ new`).
- **Rule**: Suggest only safe, verified local reproduction commands (e.g. `pytest tests/test_auth.py -k test_login` instead of destructive commands).

---

## 5. Delivery & GitHub Interaction Rules

### 5.1 Single Comment Update Rule (Rule GH-01)
- The GitHub PR bot must avoid spamming multiple comments.
- It must search for an existing comment containing the signature marker:
  `<!-- AI_CI_TRIAGE_ASSISTANT_BOT_COMMENT -->`
- If found, it updates the existing comment; otherwise, it posts a new comment.

### 5.2 Collapsible Logs & Clean Formatting (Rule GH-02)
- Always place the raw extracted stack trace inside an HTML `<details><summary>🔍 Extracted Stack Trace</summary> ... </details>` block to keep the PR clean and readable.
- Highlight the error category with an appropriate badge (e.g., 🔴 `CRITICAL - OUT_OF_MEMORY`, 🟡 `TEST_ASSERTION_FAILURE`, 🔵 `DEPENDENCY_CONFLICT`).

---

## 6. Resilience & Fallback Rules (Rule RES-01)

1. **Timeout Rule**: Any external LLM request must have a strict timeout of **8 seconds**.
2. **Offline Mode**: If `OPENAI_API_KEY` or `GEMINI_API_KEY` is not set, the system automatically runs in high-precision Heuristic Mode without raising unhandled exceptions.
3. **Graceful Exit**: The triage assistant process must never exit with a non-zero code unless explicitly configured in strict CI mode (`--fail-on-error`), so that CI pipelines do not fail because of the triage tool itself.
