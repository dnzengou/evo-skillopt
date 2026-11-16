# syntax=docker/dockerfile:1.7

# ─── build stage ──────────────────────────────────────────────────────
FROM python:3.12-slim AS build

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
      git ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy SkillOpt source (present as vendored dir OR git submodule)
COPY skillopt/ /build/skillopt/
COPY pyproject.toml /build/pyproject.toml
COPY requirements.txt /build/requirements.txt

# Install into an isolated venv for a slim final image.
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -e /build \
 && /opt/venv/bin/pip install --no-cache-dir prometheus-client==0.20.0

# ─── runtime stage ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates tini git \
    && rm -rf /var/lib/apt/lists/* \
 && groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

# Copy venv + code from build stage
COPY --from=build /opt/venv /opt/venv
COPY --from=build /build/skillopt /app/skillopt
# Whole worker/ dir — needed for rrss_gate/cascade/arm_signals imports
COPY worker/ /app/worker/
COPY scripts /app/scripts
COPY configs /app/configs

# Agent-discovery files served from the live worker so AI agents hitting
# the service blind can self-discover capabilities, endpoints, and docs.
COPY llms.txt       /app/llms.txt
COPY llms-full.txt  /app/llms-full.txt
COPY AGENTS.md      /app/AGENTS.md
COPY .well-known/   /app/.well-known/

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OUTPUT_ROOT=/data/outputs \
    SKILL_STORE_ROOT=/data/bots \
    SKILL_STORE_USE_GIT=1 \
    JOB_QUEUE_DB=/data/jobs.db \
    JOB_QUEUE_WORKERS=2 \
    TRAIN_SCRIPT=/app/scripts/train.py \
    DISCOVERY_ROOT=/app \
    PORT=9000

RUN mkdir -p /data/outputs /data/bots && chown -R app:app /data /app

USER app
EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:9000/health',timeout=3).status==200 else 1)"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "/app/worker/skillopt_worker.py"]
