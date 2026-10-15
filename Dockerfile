# Stage 1: Build & Dependencies
FROM python:3.11-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Minimal Production Runtime
FROM python:3.11-slim AS runner

WORKDIR /app
RUN groupadd -r triageuser && useradd -r -g triageuser triageuser

COPY --from=builder /root/.local /home/triageuser/.local
COPY --chown=triageuser:triageuser src/ ./src/
COPY --chown=triageuser:triageuser pyproject.toml README.md ./

ENV PATH=/home/triageuser/.local/bin:$PATH
ENV PYTHONPATH=/app/src:$PYTHONPATH

USER triageuser
EXPOSE 8080

CMD ["python", "-m", "uvicorn", "triage.integrations.webhook_server:app", "--host", "0.0.0.0", "--port", "8080"]
