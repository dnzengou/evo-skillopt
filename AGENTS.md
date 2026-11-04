# AGENTS.md — orientation for AI coding agents

This file is written for AI agents (coding assistants, LLM-powered
reviewers, autonomous crawlers) working with this repository. If you
are a human, [`README.md`](./README.md) and
[`CONTRIBUTING.md`](./CONTRIBUTING.md) are the right entry points.

This file follows the emerging [AGENTS.md convention](https://agents.md)
— one top-level file, short, mechanical. It supplements, not replaces,
[`CLAUDE.md`](./CLAUDE.md) (the project-context file some agents will
load automatically).

## What this project is

`evo-skillopt` — a self-hostable HTTP worker that evolves a bot's
Markdown "skill" file against a held-out eval set. See
[`llms.txt`](./llms.txt) for the one-paragraph version and
[`EvoSkillOpt_Blueprint.md`](./EvoSkillOpt_Blueprint.md) for the full
picture.

## Where the code is

| Area                   | Path                              | Agent-editable? |
|------------------------|-----------------------------------|-----------------|
| HTTP worker            | `worker/`                         | yes             |
| Worker extensions      | `worker/{rrss_gate,cascade,arm_signals,rrss_from_history}.py` | yes |
| CLI / batch scripts    | `scripts/`                        | yes             |
| YAML configs           | `configs/`                        | yes             |
| Example bots           | `examples/`                       | yes             |
| Tests                  | `tests/`                          | yes             |
| Project docs           | `docs/`, root `*.md`              | yes             |
| Vendored SkillOpt core | `skillopt/`                       | **no** — upstream, MIT. Ruff is configured to skip it. |
| Optional dashboard     | `skillopt_webui/`                 | yes             |

## How to run the checks a human reviewer runs

```bash
pip install -e ".[dev]"
ruff check .
pytest -q
python -m py_compile worker/*.py scripts/*.py
bash scripts/smoke.sh                  # end-to-end smoke
```

CI runs the same (`.github/workflows/ci.yml`). A green pre-commit run
locally is a strong signal CI will pass.

## Conventions worth knowing

- **Skills are Markdown.** The learnable parameter of this system. Never
  swap in a binary format or hard-code the behavior in Python.
- **Configs are YAML.** One per benchmark or profile:
  `configs/<name>/default.yaml`.
- **Product-neutral.** No proprietary / venture branding in-repo. See
  [`CLAUDE.md`](./CLAUDE.md) and [`TRADEMARKS.md`](./TRADEMARKS.md).
- **Comments.** Default to zero. Only write one when the *why* is
  non-obvious. Never narrate the task or the fix.
- **Commits.** Follow the pattern in `git log` — type-scoped, concise,
  no decorative emoji. Co-authorship footer when authored by an agent.
- **Branches.** Agent-driven work goes on
  `claude/<slug>-<nonce>` branches. Open a PR only when asked.

## HTTP surface (so you don't have to grep for it)

Machine-readable OpenAPI 3.1 contract: [`.well-known/openapi.yaml`](./.well-known/openapi.yaml).

| Method | Path                           | Auth   | Pure? | Notes                                        |
|--------|--------------------------------|--------|-------|----------------------------------------------|
| GET    | `/`                            | none   | yes   | service card JSON (name, endpoints, docs)    |
| GET    | `/health`                      | none   | yes   | liveness probe                               |
| GET    | `/metrics`                     | none   | yes   | Prometheus exposition (503 w/o `[worker]`)   |
| GET    | `/.well-known/agents.json`     | none   | yes   | machine-readable capabilities manifest       |
| GET    | `/.well-known/openapi.yaml`    | none   | yes   | OpenAPI 3.1 contract                         |
| GET    | `/openapi.yaml`                | none   | yes   | alias of `/.well-known/openapi.yaml`         |
| GET    | `/llms.txt`                    | none   | yes   | llms.txt-convention LLM crawl aid            |
| GET    | `/llms-full.txt`               | none   | yes   | full self-contained LLM summary              |
| GET    | `/AGENTS.md`                   | none   | yes   | this file (for agents lacking repo access)   |
| POST   | `/train`                       | bearer | no    | shells out to `scripts/train.py`             |
| POST   | `/train/cascade`               | bearer | yes   | aggregate pre-scored stages                  |
| POST   | `/fitness/arm`                 | bearer | yes   | reduce ARM signals to fitness                |

Bearer auth is required on POST endpoints when `WORKER_TOKEN` is set
(dev mode = empty token = no auth). Discovery GETs are always
unauthenticated — they're the first thing an agent that just
discovered the service should hit.

## Things to leave alone

- `skillopt/` — vendored upstream. If a change seems needed there, make
  it in a `worker/` extension instead and import. Ruff excludes this
  directory for a reason.
- `ckpt/` — reference skills from the paper. Treat as fixtures.
- `.github/workflows/ci.yml` — safe to extend, but don't rename jobs
  without updating the branch-protection rule.

## When in doubt

Open the file, read the module docstring, and run `pytest -q`. If a
test file exists under `tests/test_<module>.py`, that's the ground
truth for the module's contract.
