# System Architecture
## AI-Powered CI/CD Build Failure Triage Assistant

**Version:** 1.0.0  
**Architectural Style:** Modular Microservice & Portable CLI / GitHub Action  

---

## 1. High-Level Architecture Overview

The **AI-Powered CI/CD Build Failure Triage Assistant** is engineered with a modular, layered pipeline architecture. It decouples log ingestion, security sanitization, classification heuristics, AI/LLM inference, and notification delivery.

```mermaid
flowchart TD
    subgraph Trigger_Layer ["1. Trigger & Ingestion Layer"]
        A1[GitHub Actions Failure Event] -->|workflow_run.completed| B1[Webhook Server FastAPI]
        A2[GitHub Action Step in Workflow] -->|CLI Entrypoint| B2[triage CLI Runner]
        A3[Developer Terminal / Stdin] -->|triage analyze log.txt| B2
        A4[Jenkins / External CI] -->|HTTP REST API| B1
    end

    subgraph Preprocessing_Layer ["2. Log Sanitization & Token Optimization"]
        B1 & B2 --> C1[ANSI Stripper & Line Normalizer]
        C1 --> C2[Regex Secret & Credential Redactor]
        C2 --> C3[Sliding Window Chunker & Stacktrace Extractor]
    end

    subgraph Hybrid_Triage_Engine ["3. Hybrid Triage & Classification Engine"]
        C3 --> D1[Tier 1: Heuristic Rule Engine]
        D1 -->|Confidence >= 0.95 & Simple Error| E1[Direct Report Generator]
        D1 -->|Complex Semantic Failure / Need Code Diff| D2[Tier 2: AI / LLM Deep Triage Engine]
        
        subgraph LLM_Providers ["LLM Provider Abstraction"]
            D2 --> P1[OpenAI GPT-4o / GPT-4o-mini]
            D2 --> P2[Google Gemini 2.0 / 1.5]
            D2 --> P3[Anthropic Claude 3.5 Sonnet]
            D2 --> P4[Local Ollama / DeepSeek / Llama 3]
            D2 --> P5[Mock Engine Offline CI]
        end
    end

    subgraph Synthesis_Layer ["4. Report Synthesis & Formatting"]
        D2 & E1 --> F1[Triage Report Pydantic Model]
        F1 --> G1[Markdown PR Formatter]
        F1 --> G2[GitHub Step Summary Builder]
        F1 --> G3[Slack Block Kit Formatter]
        F1 --> G4[Terminal Rich Console Formatter]
        F1 --> G5[JSON Report Exporter]
    end

    subgraph Delivery_Layer ["5. Delivery & Actionable Feedback"]
        G1 --> H1[GitHub REST API - PR Commenter]
        G2 --> H2[GitHub Actions $GITHUB_STEP_SUMMARY]
        G3 --> H3[Slack Incoming Webhook]
        G4 --> H4[Stdout / Interactive CLI]
        G5 --> H5[Artifact Storage / S3 / GCS]
    end
```

---

## 2. Core Architectural Components

### 2.1 Ingestion & Webhook Layer (`src/triage/integrations/`)
- **FastAPI Webhook Server (`webhook_server.py`)**:
  - Exposes `/webhook/github` endpoint verifying `X-Hub-Signature-256`.
  - Captures `workflow_run.completed` events with `conclusion == "failure"`.
  - Downloads workflow job logs using Octokit/PyGithub REST API.
- **CLI Runner (`cli.py`)**:
  - Standalone executable powered by `typer`/`click`.
  - Operates on local log files, pipes from stdin (`cat build.log | triage analyze`), or fetches logs directly via `--repo` and `--run-id`.

### 2.2 Sanitization & Reduction Subsystem (`src/triage/parser/`)
- **Sanitizer (`sanitizer.py`)**:
  - Regex-based ANSI escape code removal (`\x1b\[[0-9;]*[a-zA-Z]`).
  - Carriage return normalization and non-printable control character filtering.
- **Redactor (`redactor.py`)**:
  - Scans for high-entropy tokens and predefined regex signatures (AWS, GitHub, Slack, OpenAI, Bearer tokens, private keys).
  - Replaces matches with cryptographic placeholders (e.g. `[REDACTED_AWS_KEY]`) *before* logs enter memory buffers destined for LLMs.
- **Chunker & Stack Trace Extractor (`chunker.py`, `stacktrace_extractor.py`)**:
  - Employs **Reverse Tail Scanning**: Starts at EOF and walks backwards to identify the latest unhandled exception.
  - Multi-language regex library recognizing Python tracebacks, Java stack traces, NPM error tables, Go panic logs, Rust compile errors, and Docker build step crashes.
  - Generates a compact ~500–1,500 token window containing 50 context lines before the error and 150 lines of error details.

### 2.3 Hybrid Classification Engine (`src/triage/classifier/`)
- **Deterministic Heuristic Engine (`heuristic_engine.py`)**:
  - Implements rapid regex-based classification (OOM, lockfile conflicts, 401/403 permissions, missing modules).
  - Assigns an initial error category and confidence score in < 5ms.
- **LLM Reasoning Client (`llm/client.py` & `llm/prompts.py`)**:
  - Implements a unified `BaseLLMClient` with concrete adapters for OpenAI, Gemini, Claude, and Ollama.
  - Enforces JSON output using schema definitions or response format flags.
  - Prompts are optimized with few-shot examples for generating concise root causes, unified code diffs, and local reproduction commands.

```mermaid
sequenceDiagram
    autonumber
    actor Developer
    participant GitHub as GitHub Actions CI
    participant Triage as Triage Assistant Service
    participant LLM as LLM Provider (OpenAI/Gemini/Ollama)
    participant PR as GitHub Pull Request

    Developer->>GitHub: Push commit / Open PR
    GitHub->>GitHub: Run Build & Test Pipeline (FAILED)
    GitHub->>Triage: Webhook (workflow_run failure) or Action Step
    Triage->>GitHub: Fetch failed job logs
    Triage->>Triage: Strip ANSI + Redact Secrets
    Triage->>Triage: Extract High-Signal Stack Trace Window
    Triage->>Triage: Run Tier 1 Fast Heuristics
    alt Heuristic High Confidence & Simple Fix
        Triage->>Triage: Generate Deterministic Report
    else Semantic Complex Error
        Triage->>LLM: Send Cleaned Log Context + JSON Prompt
        LLM-->>Triage: Return Structured RCA, Diff & Fix Plan
    end
    Triage->>Triage: Synthesize Markdown Report
    Triage->>PR: Post / Update Collapsible PR Comment
    Triage->>GitHub: Update GitHub Step Summary
    Developer->>PR: View instant RCA & apply suggested fix!
```

---

## 3. Data Model & Contract Architecture

### 3.1 Domain Models (`src/triage/models.py`)

```mermaid
classDiagram
    class ErrorCategory {
        <<enumeration>>
        SYNTAX_COMPILE_ERROR
        TEST_ASSERTION_FAILURE
        DEPENDENCY_CONFLICT
        OUT_OF_MEMORY_OOM
        INFRA_TIMEOUT
        PERMISSION_SECRET_MISSING
        LINT_FORMAT_SECURITY
        FLAKY_TRANSIENT_FAILURE
        UNKNOWN_FAILURE
    }

    class CodeFix {
        +string file_path
        +int line_number
        +string old_code
        +string new_code
        +string unified_diff
    }

    class ErrorContext {
        +string failed_step
        +string command
        +string raw_error_snippet
        +string extracted_stacktrace
        +int line_count
    }

    class TriageReport {
        +string id
        +ErrorCategory error_category
        +float confidence_score
        +string summary
        +string failed_step
        +string root_cause_file
        +int root_cause_line
        +string suggested_fix
        +CodeFix code_fix
        +string reproduction_command
        +string triage_mode
        +ErrorContext context
        +datetime timestamp
        +to_markdown() string
        +to_slack_blocks() dict
    }

    TriageReport *-- ErrorCategory
    TriageReport *-- CodeFix
    TriageReport *-- ErrorContext
```

---

## 4. Security & Privacy Architecture

1. **Zero Secret Egress**: All logs undergo in-memory sanitization before the LLM prompt is assembled.
2. **Stateless Processing**: The core triage engine does not persist raw customer log data to disk unless explicitly configured for local caching.
3. **Least Privilege Principle**: GitHub App or Personal Access Token requires minimal scopes:
   - `actions:read` (to fetch workflow run logs)
   - `pull_requests:write` (to post/update PR comments)
   - `checks:write` (optional for check-run annotations)
4. **Offline Isolation**: Fully compatible with local air-gapped on-premise deployments using local Ollama / vLLM instances.

---

## 5. Deployment Topologies

The assistant supports 3 primary deployment models:

| Topology | Use Case | Mechanism | Latency |
|---|---|---|---|
| **1. GitHub Action Step** | Per-repository automated CI step | Runs inside the workflow container (`uses: ./action.yml`) | ~5-10s |
| **2. Centralized Webhook Service** | Organization-wide automated triage | Deployed on Docker / K8s / Cloud Run receiving webhooks | ~3-8s |
| **3. CLI Developer Tool** | Local workstation / Debugging | Installed via `pip install .` or binary | < 2s |
