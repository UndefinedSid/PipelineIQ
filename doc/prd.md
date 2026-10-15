# Product Requirements Document (PRD)
## AI-Powered CI/CD Build Failure Triage Assistant

**Document Version:** 1.0.0  
**Status:** Approved / Ready for Implementation  
**Target Audience:** DevOps Engineers, Platform Engineers, SREs, Software Developers, Engineering Managers  

---

## 1. Executive Summary

### 1.1 The Problem
In modern software engineering, Continuous Integration and Continuous Deployment (CI/CD) pipelines execute thousands of builds and test suites daily. When a build fails:
- Developers are bombarded with raw logs containing **5,000 to 50,000+ lines** of terminal output, compiler noise, debug messages, and ANSI color codes.
- Diagnosing a failure requires manually scrolling, identifying the needle-in-the-haystack stack trace, determining the category of failure (e.g., compile error vs flaky test vs missing environment variable), and figuring out the fix.
- On average, engineers waste **15 to 45 minutes per failed build** on triage alone. In an engineering team of 50 developers, build failures consume hundreds of engineering hours every sprint.

### 1.2 The Solution
The **AI-Powered CI/CD Build Failure Triage Assistant** is an intelligent AIOps service and GitHub Action/Webhook system that automatically intercepts failed CI runs, extracts high-signal failure logs, classifies the root cause using a hybrid heuristic + Large Language Model (LLM) engine, and instantly posts a crystal-clear, structured triage summary with actionable fix recommendations directly to the GitHub Pull Request, Slack, or terminal.

---

## 2. Goals and Success Metrics

### 2.1 Key Objectives
1. **Automated Log Ingestion & Noise Reduction**: Strip ANSI codes, remove boilerplate runtime logs, redact sensitive secrets/tokens, and isolate the exact failure window.
2. **Hybrid Failure Classification**: Employ fast regex heuristics (<5ms) for common deterministic patterns (OOM, missing packages, syntax errors) and LLMs (OpenAI, Gemini, Ollama, Claude) for complex semantic failures.
3. **Actionable Root Cause Analysis (RCA)**: Generate human-friendly explanations, identify the breaking file and line, provide code diff suggestions, and produce local reproduction commands.
4. **Multi-Channel Delivery**: Deliver results via GitHub PR Comments, GitHub Action Step Summaries, Slack interactive Block Kit messages, and CLI tool outputs.
5. **Zero-Secret Leakage Guarantee**: 100% regex-based and heuristic secret masking prior to passing any log slice to external LLM APIs.

### 2.2 Success Metrics (KPIs)
| Metric | Baseline (Manual) | Target (With Assistant) |
|---|---|---|
| **Mean Time to Triage (MTTT)** | 20 minutes | **< 30 seconds** |
| **Log Noise Reduction** | 100% raw log (10 MB) | **> 95% reduction (< 10 KB sent to LLM)** |
| **Root Cause Classification Accuracy** | Variable | **> 92% accurate category identification** |
| **Token Cost Optimization** | Full log ($0.15/run) | **Tailored chunks (< $0.005/run)** |
| **Secret Redaction Rate** | 0% | **100% known credential patterns masked** |

---

## 3. User Personas & Use Cases

### 3.1 Personas
- **Developer (Dev)**: Wants to push code and get instant, clear feedback if the build breaks without having to read massive Jenkins / GitHub Action logs.
- **DevOps / Platform Engineer**: Wants to reduce CI runner compute costs and eliminate developer support tickets related to obscure pipeline failures.
- **Engineering Lead**: Wants visibility into frequent failure modes (e.g., identifying recurring flaky tests vs recurring dependency drift).

### 3.2 Key Use Cases
1. **GitHub PR Auto-Triage**: A developer opens a PR; CI tests fail; the assistant posts a rich PR comment detailing the failed test, the root cause exception, and a copy-paste code patch.
2. **Local Pre-Flight CLI Triage**: A developer runs `triage analyze --log-file=build.log` locally before pushing to understand why a test failed in a containerized environment.
3. **Team Slack Channel Alerts**: SRE/DevOps teams receive an immediate Slack alert when the `main` branch deployment fails, containing an executive summary and one-click rollback/re-run suggestions.
4. **Flaky Test Triage**: Differentiates between actual code regressions and transient network/infrastructure timeouts or flaky tests.

---

## 4. Functional Requirements

### 4.1 Log Ingestion & Pre-processing
- **FR-1.1 (Multi-Source Support)**: Ingest logs from GitHub Actions REST API, raw file uploads, stdin pipe, or HTTP webhook payloads.
- **FR-1.2 (ANSI & Terminal Formatting Stripping)**: Strip all ANSI escape codes, terminal cursor movements, and control sequences.
- **FR-1.3 (Secret Masking)**: Mask AWS keys, GitHub Personal Access Tokens (PATs), JWT tokens, Bearer auth headers, API keys (`sk-...`), private keys, and environment variables matching `*_SECRET` / `*_KEY`.
- **FR-1.4 (High-Signal Log Chunking)**:
  - Implement a multi-stage sliding window and reverse-tail scan.
  - Scan backward from log termination to find stack traces, error markers (`FAILED`, `FATAL`, `Error:`, `Traceback (most recent call last):`, `npm ERR!`, `BUILD FAILED`).
  - Extract the critical 50–200 line failure context while preserving leading metadata (environment, command executed).

### 4.2 Error Classification & Taxonomy Engine
- **FR-2.1 (Taxonomy Categories)**:
  1. `SYNTAX_COMPILE_ERROR`: Code syntax, type checking, compiler failures (TypeScript, Rust, Java, Go, Python `SyntaxError`).
  2. `TEST_ASSERTION_FAILURE`: Unit / Integration test assertion errors (Pytest, JUnit, Jest, Mocha).
  3. `DEPENDENCY_CONFLICT`: Missing package, incompatible version, lockfile mismatch, npm/pip resolution failure.
  4. `OUT_OF_MEMORY_OOM`: Container killed (exit code 137), Java Heap Space, V8 Out of Memory.
  5. `INFRA_TIMEOUT`: Network timeout, slow runner, hung process exceeding time limit.
  6. `PERMISSION_SECRET_MISSING`: 401/403 API responses, missing credentials, Docker push unauthorized.
  7. `LINT_FORMAT_SECURITY`: Flake8, ESLint, Bandit, SonarQube, Trivy security CVE failures.
  8. `FLAKY_TRANSIENT_FAILURE`: Intermittent network hiccup, race condition, socket connection reset.
- **FR-2.2 (Heuristic Rule Engine)**: Deterministic regex and pattern matching executed first to achieve instant classification without LLM latency or cost where possible.

### 4.3 AI / LLM Deep Triage Engine
- **FR-3.1 (Multi-LLM Provider Support)**: Pluggable backends:
  - OpenAI (`gpt-4o`, `gpt-4o-mini`)
  - Google Gemini (`gemini-2.0-flash`, `gemini-1.5-pro`)
  - Anthropic (`claude-3-5-sonnet`)
  - Local / Ollama (`llama3`, `deepseek-r1`, `mistral`)
  - Mock Provider (Offline testing and CI dogfooding)
- **FR-3.2 (Structured JSON Schema Enforcement)**: Force LLM responses to adhere to a strict Pydantic model schema:
  - `error_category`: Categorical string matching taxonomy.
  - `summary`: 1-2 sentence executive explanation of what went wrong.
  - `failed_step`: Name of the pipeline stage / step that failed.
  - `root_cause_file`: File path where the bug originated (if applicable).
  - `root_cause_line`: Line number of the defect.
  - `suggested_fix`: Plain English explanation of how to fix it.
  - `code_diff`: Markdown diff showing `old_code` vs `new_code`.
  - `reproduction_command`: Exact shell command to test the fix locally.
  - `confidence_score`: Float between 0.0 and 1.0.

### 4.4 Delivery & Integrations
- **FR-4.1 (GitHub PR Commenter)**: Create or update PR comments with a collapsible, beautifully formatted Markdown summary.
- **FR-4.2 (GitHub Action Step Summary)**: Export the markdown report to `$GITHUB_STEP_SUMMARY`.
- **FR-4.3 (FastAPI Webhook Server)**: Listen to `workflow_run.completed` GitHub webhooks for autonomous organization-wide triaging.
- **FR-4.4 (Slack Notifier)**: Post rich Slack messages with error badges and action buttons.
- **FR-4.5 (Developer CLI)**: Interactive terminal output with rich tables and syntax-highlighted diffs.

---

## 5. Non-Functional Requirements (NFR)

- **Performance**: Heuristic analysis completed in < 10ms; Full LLM triage completed in < 3 seconds.
- **Reliability & Fallback**: If LLM API is unreachable or times out (after 5s), fallback gracefully to deterministic heuristic output with a note: `[Heuristic Mode: LLM Unavailable]`.
- **Security & Privacy**: Zero sensitive customer data sent to third-party endpoints. Mandatory secret redaction executed before log serialization.
- **Portability**: Packaged as a single lightweight Docker container, Python package (`pip install .`), and GitHub Action (`action.yml`).
- **Test Coverage**: Minimum 85% code coverage across log parsers, sanitizers, heuristic classifiers, and webhook endpoints.

---

## 6. Scope & Phasing

- **In Scope**: GitHub Actions log analysis, Pytest / Maven / NPM / Go / Docker / GCC / Rust log formats, GitHub PR comments, Slack notifications, CLI interface, Webhook server.
- **Out of Scope (v1.0)**: Automatic code modification and auto-committing fixes to the branch (requires human approval step in v1.0).
