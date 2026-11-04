# evo-skillopt

<!--
Machine-readable project card (schema.org JSON-LD) for LLM-powered
search and agent crawlers. Human readers can skip to "What this is".
-->
<!-- llms.txt: ./llms.txt | agents manifest: ./.well-known/agents.json | AI-agent orientation: ./AGENTS.md -->

<!-- JSON-LD: schema.org/SoftwareApplication -->
```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "evo-skillopt",
  "applicationCategory": "DeveloperApplication",
  "operatingSystem": "Linux, macOS, Windows (Docker)",
  "description": "Text-space skill optimization for production LLM agents, callable over HTTP. Evolves a bot's Markdown skill file against a held-out eval set with git-tracked audit trails.",
  "programmingLanguage": "Python",
  "license": "https://opensource.org/licenses/MIT",
  "codeRepository": "https://github.com/dnzengou/evo-skillopt",
  "documentation": "https://dnzengou.github.io/evo-skillopt",
  "keywords": "agent, LLM, prompt-optimization, skill-learning, agentic, SkillOpt, RRSS, cascade, ARM",
  "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" }
}
```

> **Text-space skill optimization for production LLM agents.**
> Train your agent's Markdown skill file like a neural network — epochs,
> batch size, learning rates, validation gates — without touching model
> weights. Ships behind a small HTTP service any runtime can call.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/dnzengou/evo-skillopt/actions/workflows/ci.yml/badge.svg)](https://github.com/dnzengou/evo-skillopt/actions/workflows/ci.yml)

---

## What this is

`evo-skillopt` productizes the **SkillOpt** algorithm ([arXiv:2605.23904](https://arxiv.org/abs/2605.23904), MIT-licensed) as a callable service.

Every AI agent product ships a v1.0 system prompt and iterates via ad-hoc
prompt tweaks. evo-skillopt turns that loop into disciplined training:

- **Skill = Markdown file.** Human-readable behavior contract.
- **Training loop = rollout → reflect → aggregate → select → update → gate.**
- **Gate = held-out eval set.** If a new skill doesn't beat the previous one, we roll back.
- **Zero weight changes.** Works with any frozen LLM (OpenAI, Anthropic, Google, Azure, local).
- **Git-tracked audit trail.** Every skill version is a commit.

## What this is *not*

- A new training algorithm — SkillOpt itself is the upstream project.
- A new LLM.
- A prompt-engineering IDE.
- An eval framework alone — evals are the gate, not the point.

## Quick start (5 minutes)

```bash
# 1. Clone
git clone https://github.com/dnzengou/evo-skillopt.git
cd evo-skillopt

# 2. Install
pip install -e ".[worker]"

# 3. Run the worker
WORKER_TOKEN=dev-token python3 worker/skillopt_worker.py &

# 4. Verify
curl http://localhost:9000/health
# → {"service":"skillopt-worker","status":"ok"}
```

See [`INSTALL.md`](./INSTALL.md) for platform-specific installers (pipx,
Homebrew, Docker, systemd, Fly.io, Kubernetes).

## Architecture

```
   your agent runtime          evo-skillopt worker           SkillOpt core
   (any language)              (Python HTTP · stdlib)        (vendored MIT)
        │                            │                             │
        │ POST /train ──────────────►│                             │
        │                            │ subprocess: train.py ──────►│
        │                            │                             │  rollout
        │                            │                             │  reflect
        │                            │                             │  aggregate
        │                            │                             │  select
        │                            │                             │  update
        │                            │                             │  gate
        │                            │◄────── history.json ────────│
        │◄──────── JSON ─────────────│  (delta, next_version)      │
```

## Documentation

| File                                                  | What                                                    |
|-------------------------------------------------------|---------------------------------------------------------|
| [`INSTALL.md`](./INSTALL.md)                          | Standalone install — desktop, server, cloud, container  |
| [`RELEASING.md`](./RELEASING.md)                      | Cut a new release (PyPI via OIDC + GitHub Release)      |
| [`USE_CASES.md`](./USE_CASES.md)                      | Low-hanging-fruit patterns with ROI math                |
| [`GTM.md`](./GTM.md)                                  | Go-to-market in the agent era — playbook, channels, metrics |
| [`EvoSkillOpt_Blueprint.md`](./EvoSkillOpt_Blueprint.md) | Living roadmap · capabilities · KPIs · v0.1 → v1.0   |
| [`docs/CONCEPT.md`](./docs/CONCEPT.md)                | Core concept in depth                                   |
| [`docs/GLOSSARY.md`](./docs/GLOSSARY.md)              | Terminology                                             |
| [`docs/AI_SEO.md`](./docs/AI_SEO.md)                  | Agent-era SEO implementation notes                      |
| [`worker/README.md`](./worker/README.md)              | Worker operations reference                             |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md)                | How to contribute                                       |
| [`SECURITY.md`](./SECURITY.md)                        | How to report vulnerabilities                           |
| [`AGENTS.md`](./AGENTS.md)                            | Orientation written for AI coding agents                |
| [`llms.txt`](./llms.txt)                              | Short LLM-navigable project card ([llmstxt.org](https://llmstxt.org/)) |
| [`llms-full.txt`](./llms-full.txt)                    | Full LLM-navigable summary with inline API spec         |
| [`.well-known/agents.json`](./.well-known/agents.json) | Machine-readable manifest of endpoints and concepts    |
| [`.well-known/openapi.yaml`](./.well-known/openapi.yaml) | OpenAPI 3.1 spec for the worker's HTTP endpoints      |
| [`CITATION.cff`](./CITATION.cff)                      | Citation metadata (CFF 1.2)                             |
| [`NOTICE`](./NOTICE)                                  | Third-party attributions                                |
| [`TRADEMARKS.md`](./TRADEMARKS.md)                    | Trademark & branding notice                             |
| [`DISCLAIMER.md`](./DISCLAIMER.md)                    | No-warranty statement                                   |

## For AI agents

Any agent landing on this project — a coding assistant, an LLM
answer engine, or an autonomous runtime — can self-discover it in
one fetch. Both the GitHub repo and the **live worker** serve the
same canonical artifacts:

| Agent-discovery path                        | From GitHub | From live worker | From docs site |
|---------------------------------------------|:-----------:|:----------------:|:--------------:|
| `AGENTS.md`                                 | ✓           | `GET /AGENTS.md` | ✓              |
| `llms.txt`                                  | ✓           | `GET /llms.txt`  | ✓              |
| `llms-full.txt`                             | ✓           | `GET /llms-full.txt` | ✓          |
| `.well-known/agents.json`                   | ✓           | `GET /.well-known/agents.json` | ✓ |
| `.well-known/openapi.yaml`                  | ✓           | `GET /.well-known/openapi.yaml` | ✓ |
| Service card (name, endpoints, docs URL)    |             | `GET /`          |                |

See [`GTM.md`](./GTM.md) for the thinking behind this and
[`docs/AI_SEO.md`](./docs/AI_SEO.md) for implementation notes.

## Structure

```
evo-skillopt/
├── worker/               # HTTP service — Dockerfile, fly.toml, compose
│   └── skillopt_worker.py
├── skillopt/             # vendored SkillOpt library (MIT · upstream)
├── scripts/              # train.py · eval_only.py · smoke.sh
├── configs/              # per-benchmark training configs (YAML)
├── ckpt/                 # packaged reference skills (.md)
├── examples/             # runnable example bots (skill + eval only)
│   ├── telegram-summarizer/
│   ├── discord-moderator/
│   └── slack-standup/
├── docs/                 # concept · glossary · MkDocs source
├── skillopt_webui/       # optional Gradio monitoring dashboard
├── .github/workflows/    # CI — py compile · docker build · shellcheck
├── pyproject.toml        # modern packaging (PEP 621) + ruff + pytest
└── EvoSkillOpt_Blueprint.md   # living roadmap — read first
```

## Contributing

Read [`EvoSkillOpt_Blueprint.md § 13`](./EvoSkillOpt_Blueprint.md#13-change-management)
before opening a PR.

## License

MIT — see [`LICENSE`](./LICENSE) and [`NOTICE`](./NOTICE) for third-party
attributions.

## Attribution

This project depends on and vendors the SkillOpt reference implementation
([arXiv:2605.23904](https://arxiv.org/abs/2605.23904)). See [`NOTICE`](./NOTICE)
for full attribution and license text.

`evo-skillopt` is an independent open-source project. It is not affiliated
with, endorsed by, or sponsored by any upstream project or its authors.
See [`TRADEMARKS.md`](./TRADEMARKS.md).
