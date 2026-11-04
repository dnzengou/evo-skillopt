# <short, imperative title: what does this PR do>

## Why

<1-3 sentences on the motivation. Reference an issue if there is one.>

## What changed

- <bullet per logical change>
- <keep it scannable>

## Agent-visible surface changes (if any)

<If this PR adds, removes, or renames an HTTP endpoint, an .md file
at repo root, or anything under .well-known/, update:>

- [ ] `AGENTS.md` endpoint table
- [ ] `llms.txt` and `llms-full.txt`
- [ ] `.well-known/agents.json`
- [ ] `.well-known/openapi.yaml`
- [ ] `worker/skillopt_worker.py` service card (`SERVICE_CARD` + routing)

<If this PR doesn't touch the agent surface, delete this section.>

## Checklist

- [ ] `ruff check .` passes
- [ ] `pytest -q` passes
- [ ] `python -m py_compile worker/*.py` succeeds
- [ ] Changelog entry under `[Unreleased]` in `CHANGELOG.md`
- [ ] Capability ticked in `EvoSkillOpt_Blueprint.md § 5` if applicable

## Test plan

- <what you ran locally>
- <what should be green on CI>
