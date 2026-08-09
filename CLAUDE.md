# CLAUDE.md — evo-skillopt project context

## Project

**evo-skillopt** — text-space skill optimization for production LLM
agents, callable over HTTP. Wraps the SkillOpt algorithm
([arXiv:2605.23904](https://arxiv.org/abs/2605.23904), MIT) as a
minimal, self-hostable service.

- **License:** MIT (this project) + MIT (vendored SkillOpt)
- **Docs:** [`README.md`](./README.md), [`INSTALL.md`](./INSTALL.md), [`USE_CASES.md`](./USE_CASES.md)
- **Roadmap:** [`EvoSkillOpt_Blueprint.md`](./EvoSkillOpt_Blueprint.md) — read first before major work

## Stack

| Layer          | Tech                                                          |
|----------------|---------------------------------------------------------------|
| Language       | Python 3.10+ (Python 3.12 in container)                       |
| Worker         | Stdlib HTTP server (`http.server.ThreadingHTTPServer`)        |
| LLM backends   | OpenAI · Anthropic · Google · Azure OpenAI · local (Ollama, vLLM) |
| Packaging      | PEP 621 `pyproject.toml`, `pip install -e .`                  |
| Lint / format  | `ruff` (both linter and formatter)                            |
| Tests          | `pytest`                                                      |
| Container      | Multi-stage Debian slim, non-root, tini init                  |
| Compose        | `worker/docker-compose.yml` (self-host)                       |
| Cloud          | Fly.io (`worker/fly.toml`); works on Railway/Render/K8s       |
| Optional UI    | Gradio dashboard (`skillopt_webui/`)                          |
| CI             | GitHub Actions — py compile, ruff, pytest, docker build       |

## Repo layout

```
evo-skillopt/
├── worker/           # HTTP service — Dockerfile, compose, fly.toml
├── skillopt/         # vendored SkillOpt library (MIT · upstream)
├── scripts/          # train.py · eval_only.py · run_*.sh · smoke.sh
├── configs/          # per-benchmark configs (YAML)
├── ckpt/             # reference pre-trained skills (.md)
├── examples/         # 3 runnable bot examples (skill + eval)
├── docs/             # MkDocs source + concept + glossary
├── skillopt_webui/   # optional Gradio dashboard
├── skillopt-assets/  # docs images
├── .github/workflows/ci.yml
├── pyproject.toml
├── requirements.txt
└── EvoSkillOpt_Blueprint.md
```

## Commands

```bash
# Install
pip install -e .                          # library only
pip install -e ".[worker]"                # + worker deps (prometheus etc.)
pip install -e ".[dev]"                   # + ruff + pytest
pip install -e ".[webui]"                 # + Gradio UI

# Run the worker (local dev)
WORKER_TOKEN=dev-token python3 worker/skillopt_worker.py

# Container (compose)
cp .env.example .env
docker compose -f worker/docker-compose.yml --env-file .env up --build -d

# Training / evaluation (SkillOpt upstream entrypoints)
python scripts/train.py --config configs/searchqa/default.yaml
python scripts/eval_only.py --config configs/searchqa/default.yaml \
       --skill ckpt/searchqa/gpt5.5_skill.md

# Optional Gradio dashboard
python -m skillopt_webui.app

# Docs
mkdocs serve
mkdocs gh-deploy

# CI-equivalent local checks
python -m py_compile worker/skillopt_worker.py
ruff check .
pytest -q
bash scripts/smoke.sh
```

## Conventions

- **Skills are `.md` files.** Human-readable behavior contracts. Never
  a binary format, never a code change to iterate.
- **Configs are YAML.** Each benchmark or profile lives at
  `configs/<name>/default.yaml`.
- **Auto-resume.** Runs pick up from `runtime_state.json` if interrupted.
- **No secrets in source.** Provider API keys via env only —
  see [`.env.example`](./.env.example).
- **Bearer auth on `/train`** when `WORKER_TOKEN` is set. Dev mode
  skips auth when the var is empty.
- **Product-neutral.** This repo hosts a general-purpose OSS product; no
  proprietary product / venture branding lives here. See
  [`TRADEMARKS.md`](./TRADEMARKS.md).

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) and
[`EvoSkillOpt_Blueprint.md § 13`](./EvoSkillOpt_Blueprint.md#13-change-management).

## Legal

- [`LICENSE`](./LICENSE) — MIT
- [`NOTICE`](./NOTICE) — third-party attributions
- [`TRADEMARKS.md`](./TRADEMARKS.md) — no affiliation with upstream
- [`DISCLAIMER.md`](./DISCLAIMER.md) — no-warranty statement
- [`SECURITY.md`](./SECURITY.md) — vulnerability reports
