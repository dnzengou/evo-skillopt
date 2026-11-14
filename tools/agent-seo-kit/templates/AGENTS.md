# AGENTS.md — orientation for AI coding agents

This file is written for AI agents (coding assistants, LLM-powered
reviewers, autonomous crawlers) working with this repository. If you
are a human, `README.md` is the right entry point.

This file follows the [AGENTS.md convention](https://agents.md).

## What this project is

`{{project}}` — {{description}}

See `llms.txt` for the one-paragraph version and your `README.md` for
the human-facing overview.

## Where the code is

| Area                   | Path                              | Agent-editable? |
|------------------------|-----------------------------------|-----------------|
| (fill in per project)  |                                   |                 |

## How to run the checks a human reviewer runs

```bash
# Fill in per project — e.g.:
# pytest -q
# ruff check .
# npm test
```

CI runs the same (`.github/workflows/`). A green pre-commit run
locally is a strong signal CI will pass.

## Conventions worth knowing

- (fill in per project — formatting, commit style, branch naming)

## HTTP surface (if this project exposes one)

Machine-readable OpenAPI 3.1 contract: `.well-known/openapi.yaml`.
Discovery manifest: `.well-known/agents.json`.

## Things to leave alone

- (fill in per project — vendored dirs, generated code, etc.)

## When in doubt

Open the file, read the module docstring, and run the project's test
command.
