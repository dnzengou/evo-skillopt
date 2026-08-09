# CLAUDE.md — SkillOpt Project Context

## Project
**SkillOpt** — train agent skills like neural networks (epochs, batch size, learning rates, validation gates) without touching model weights. Text-space optimizer for frozen LLM agents.

- **Paper:** arXiv:2605.23904
- **Docs:** https://microsoft.github.io/SkillOpt
- **Repo:** github.com/microsoft/SkillOpt (fork: dnzengou/SkillOpt)
- **License:** MIT

## Stack
| Layer | Tech |
|-------|------|
| Language | Python 3.10+ |
| LLM backends | Azure OpenAI, OpenAI-compatible, Anthropic Claude, Qwen (vLLM) |
| Web UI | Gradio (`skillopt_webui/`) |
| Docs | MkDocs Material → GitHub Pages |
| Static site | `index.html` (2739 lines, standalone, no build step) |
| Package | `pyproject.toml`, installable via `pip install -e .` |

## Repo Layout
```
SkillOpt/
├── scripts/           # train.py, eval_only.py — CLI entrypoints
├── skillopt/          # core library
│   ├── envs/          # benchmark environments (SearchQA, ALFWorld, DocVQA…)
│   └── prompts/       # LLM prompt templates
├── configs/           # per-benchmark YAML configs
├── ckpt/              # packaged pre-trained skills (.md files)
├── data/              # split dirs (not committed; user-provided)
├── docs/              # MkDocs source (markdown)
├── skillopt_webui/    # Gradio monitoring dashboard
├── index.html         # standalone project landing page (Microsoft/SkillOpt)
├── mkdocs.yml         # MkDocs config → deploys to GitHub Pages
├── CLOW.md            # Clow manual & reference (install / deploy / use / apps / API / troubleshoot)
├── MARKETING.md       # Clow bots ARM GTM strategy (branch: clow-bots-marketing-gtm)
├── Clow_GTM_Blueprint.md  # living roadmap for Clow GTM initiative
├── EvoMetaClaw.md     # SkillOpt × Clow moat: self-evolving bots
├── EvoSkillOpt.md     # private-repo brief: what evo-skillopt is, 5 use cases, roadmap
├── clow_landing.html  # production-ready standalone landing page (deploy to Vercel)
├── use_cases.html     # 3-bot showcase w/ live evolution feed (routes: /use-cases)
├── X_THREADS.md       # copy-paste X threads for @XTech73781
├── clow_bot_template.md   # starter skill template for bot publishers
├── EvoStack.md        # name-space cheat sheet: KafCa/KafCade/EvoSkillOpt/EvoMetaClaw/EvoForge/RRSS
├── bots/              # 3 ready-to-fork sample bots (marketplace at launch)
│   ├── telegram-summarizer/  # free tier
│   ├── discord-moderator/    # $3/mo
│   └── slack-standup/        # $5/mo
├── .github/workflows/ci.yml  # cargo check + clippy + node --check + py compile
├── api/               # Vercel Edge Functions (waitlist, og image)
├── vercel.json        # routing + security headers
├── DEPLOY.md          # 30-min go-live checklist
├── dashboard.html     # single-file ops dashboard (MRR, leads, evolution, findings)
├── scripts/
│   ├── train.py           # SkillOpt training entrypoint (existing)
│   ├── eval_only.py       # SkillOpt evaluation entrypoint (existing)
│   ├── skillopt_worker.py # HTTP bridge: evo-metaclaw ↔ train.py (stdlib only)
│   ├── smoke.sh           # one-command health probe for backend + worker
│   └── deploy_vercel.sh   # one-command Vercel deploy (assembles + ships)
└── clow-agents/       # Rust backend: gtm-engine + security-agent + evo-metaclaw
    └── backend/
        ├── shared/          # KafCa bus, auth, db, models, notify
        ├── gtm-engine/      # ICP scoring, deal pipeline, MRR forecast
        ├── security-agent/  # scan → Certified Secure badge
        └── evo-metaclaw/    # trajectory ingest, fitness, evolution gate, leaderboard
```

## Active Branch Context
**Branch:** `claude/clow-bots-marketing-gtm-p6nTm`
**Purpose:** Marketing & GTM strategy for the **Clow bots ecosystem** (https://clow-tau.vercel.app), a PicoClaw-powered AI agent economy, using the BizFlow ARM framework.

## Commands
```bash
pip install -e .                          # install
pip install -e ".[alfworld]"              # + ALFWorld
pip install -e ".[webui]"                 # + Gradio UI
python scripts/train.py --config configs/searchqa/default.yaml
python scripts/eval_only.py --config configs/searchqa/default.yaml --skill ckpt/searchqa/gpt5.5_skill.md
python -m skillopt_webui.app              # launch WebUI
mkdocs serve                              # local docs preview
mkdocs gh-deploy                          # deploy docs to GitHub Pages
```

## Conventions
- Skill docs are `.md` files; no code changes needed to update a skill
- Configs are YAML; each benchmark has its own `configs/<name>/default.yaml`
- Output runs auto-resume from last completed step (`runtime_state.json`)
- No secrets in source — API keys via env vars only
- devflow skill: use `B+P+D+Bl` pipeline for build-ship cycles
- bizflow skill: use `ARM` or `CG` pipeline for GTM/growth work

## Skills Installed
| Skill | Path | Trigger |
|-------|------|---------|
| bizflow | `~/.claude/skills/bizflow/SKILL.md` | ARM, bizflow, A/R/M/Ar/Sy/Op/Rp/Sc |
| devflow | `~/.claude/skills/devflow/SKILL.md` | B/I/Im/E/C/Bl/P/D/CI/Kf/RRSS |
