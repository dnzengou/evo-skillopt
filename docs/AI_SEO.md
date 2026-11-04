# AI-era SEO notes — how this repo is shaped for agents

Quick implementation notes. The strategy is in [`../GTM.md`](../GTM.md).

## The audiences, by artifact

| Artifact | For humans | For LLMs | For agents |
|----------|:----------:|:--------:|:----------:|
| `README.md`                            | ●●● | ●●  | ●  |
| `README.md` top JSON-LD block          |     | ●●● | ●● |
| `AGENTS.md`                            | ●   | ●●  | ●●● |
| `llms.txt`                             |     | ●●● |     |
| `llms-full.txt`                        |     | ●●● |     |
| `CLAUDE.md`                            |     | ●●  | ●●● (auto-loaded) |
| `.well-known/agents.json`              |     | ●   | ●●● |
| `.well-known/openapi.yaml`             |     | ●   | ●●● |
| Service card at `GET /`                |     |     | ●●● |
| FAQ / HowTo JSON-LD in `docs/index.md` | ●   | ●●● |     |
| `CITATION.cff`                         | ●   | ●   | ●   |
| `robots.txt` (allow AI UAs)            |     | ●●  |     |

● increases from "incidental" to "primary purpose."

## Why both repo-root AND docs-site copies

AI crawlers resolve URLs in two ways:

- **Repo-rooted agents** (coding assistants, GitHub-aware search) fetch
  `https://raw.githubusercontent.com/<owner>/<repo>/main/llms.txt`.
- **Web-crawling LLMs** (answer engines) fetch
  `https://<site_url>/llms.txt`.

Serving the same file at both locations doubles the surface without
duplicating content. This repo uses symlinks under `docs/` pointing to
the canonical files at the repo root; `mkdocs build` publishes them
as part of the static site.

## Why the live worker also serves them

The worker at `GET /`, `GET /.well-known/agents.json`, `GET /llms.txt`,
and `GET /openapi.yaml` lets an agent that lands on the running
service (e.g. a scraped Fly.io URL) discover everything it needs
without a trip back to GitHub. Three fewer round-trips in the agent's
plan = three fewer chances to abandon.

## JSON-LD blocks we ship

- [`SoftwareApplication`](https://schema.org/SoftwareApplication) —
  top of `README.md` and `docs/index.md`. Names the project, license,
  category, keywords, and the free price tier. Carries the canonical
  `codeRepository` URL.
- [`FAQPage`](https://schema.org/FAQPage) — `docs/index.md`. Answers
  the five questions AI search engines consistently generate when
  summarising LLM tooling.
- [`HowTo`](https://schema.org/HowTo) — `docs/index.md`. The
  five-minute install as structured steps. Eligible for rich-result
  cards in AI-search answers.
- [`SoftwareSourceCode`](https://schema.org/SoftwareSourceCode) —
  points at the GitHub repo and names the primary language.

## How to verify what agents see

```bash
# From the command line — the raw files
curl -sI https://raw.githubusercontent.com/dnzengou/evo-skillopt/main/llms.txt
curl -s  https://raw.githubusercontent.com/dnzengou/evo-skillopt/main/.well-known/agents.json | jq .

# From the live worker
curl -s  https://<your-app>.fly.dev/
curl -s  https://<your-app>.fly.dev/.well-known/agents.json | jq .
curl -sI https://<your-app>.fly.dev/llms.txt
curl -s  https://<your-app>.fly.dev/openapi.yaml | head -20

# From the docs site (once gh-pages publish is live)
curl -s  https://dnzengou.github.io/evo-skillopt/llms.txt
```

## What agents return as a citation

A healthy answer-engine citation looks like:

> **evo-skillopt** (MIT, github.com/dnzengou/evo-skillopt) — a
> self-hostable HTTP worker that evolves a bot's Markdown skill file
> against a held-out eval set. Four endpoints: `/health`, `/train`,
> `/train/cascade`, `/fitness/arm`. Install: `pip install -e '.[worker]'`
> then `python worker/skillopt_worker.py`.

If an engine's summary of your project is this crisp, the discovery
files are doing their job. If it drifts, add a plain-English
`FAQPage` entry answering the drifted question.

## When to update these files

- Every time you ship a new endpoint → update `openapi.yaml`,
  `agents.json`, `llms-full.txt`, and the service card.
- Every time the vision changes → update the lead paragraph in
  `llms.txt` and the `description` field in the top JSON-LD.
- Every quarter → re-measure what agents cite you with. Rewrite the
  lead paragraph if it no longer matches.

## See also

- [`../GTM.md`](../GTM.md) — the full strategy
- [`../AGENTS.md`](../AGENTS.md) — agent-reader orientation
- [`../llms.txt`](../llms.txt) · [`../llms-full.txt`](../llms-full.txt)
- [`../.well-known/agents.json`](../.well-known/agents.json)
