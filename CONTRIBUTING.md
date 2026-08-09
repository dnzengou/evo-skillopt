# Contributing to evo-skillopt

Thanks for your interest! Contributions of all kinds are welcome —
issues, docs, examples, tests, and code.

## Getting started

```bash
git clone https://github.com/dnzengou/evo-skillopt.git
cd evo-skillopt
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev,worker]'
```

## How to contribute

### 🐛 Bug reports

Open a GitHub issue with:

- Repro steps (smallest possible)
- Expected vs actual behavior
- Your config file (**strip API keys and any personal data first**)
- Version of Python, evo-skillopt, and any relevant provider SDKs

### 🔧 Add a use case

New use cases go in `docs/use-cases/<slug>.md` following the template
in [`USE_CASES.md`](./USE_CASES.md). Ship a minimal example under
`examples/<slug>/` with `skills/main.md`, `eval/held_out.json`, and
`bot.yaml`.

### 🧪 Add or improve a benchmark

The upstream SkillOpt library ships with several benchmarks under
`skillopt/envs/`. New benchmarks that live in this repo should:

- Live under `skillopt/envs/<name>/` (mirroring the upstream layout).
- Ship a matching `configs/<name>/default.yaml`.
- Include a small reference skill in `ckpt/<name>/`.

### 🤖 Add an LLM backend

Extend `skillopt/model/` following the pattern used for existing
backends (OpenAI, Anthropic, Azure, Qwen). Document env vars in
[`.env.example`](./.env.example) and [`worker/README.md`](./worker/README.md).

### 📝 Improve documentation

```bash
pip install -e '.[docs]'
mkdocs serve      # http://localhost:8000
```

## Pull-request process

1. Fork the repo and create a feature branch off `main`
   (`feature/<topic>` or `develop/<topic>`).
2. Make your change with tests / docs alongside.
3. Run local checks:

   ```bash
   ruff check .
   python -m py_compile worker/skillopt_worker.py
   pytest -q                # once tests are in place
   bash scripts/smoke.sh    # if you have a worker running
   ```

4. Update [`CHANGELOG.md`](./CHANGELOG.md) under `[Unreleased]`.
5. If you shipped a capability listed in
   [`EvoSkillOpt_Blueprint.md § 5`](./EvoSkillOpt_Blueprint.md#5-capabilities),
   tick the `⬜` → `✅` in the same PR.
6. Submit the PR with a clear description of *why* the change is needed.

## Code style

- Follow patterns already in the codebase.
- Use type hints on public function signatures.
- Keep docstrings short — one line for most functions is fine.
- Ruff is authoritative for lint (`ruff check .`) and format
  (`ruff format .`).

## Commit conventions

Use short, imperative commit subjects:

```
feat: add rollback endpoint
fix: guard against empty history.json
docs: expand install guide for Windows
chore: bump ruff to 0.6
```

## Code of conduct

By participating you agree to the [Code of Conduct](./CODE_OF_CONDUCT.md).

## License

By contributing you agree that your contributions are licensed under
the [MIT License](./LICENSE) — the same as the rest of the project.
See also [`NOTICE`](./NOTICE) for upstream attribution requirements.
