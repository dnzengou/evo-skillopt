# agent-seo-kit — the agent-era SEO surface, extracted

**What this is:** a copy-paste kit that gives any open-source project
the same agents-detectable posture `evo-skillopt` ships with. Humans,
LLM answer engines, and agent runtimes all find the project from a
single `curl` at the canonical URLs.

**Why it exists:** in 2026, half the funnel for a developer product
is read by an LLM, not a human. Projects that are parseable by an
agent win the citation; projects that are not lose it silently.
[`GTM.md`](../../GTM.md) has the full thesis; this directory has the
working artifacts.

**What ships:**

| File | Purpose | Convention |
|---|---|---|
| `templates/AGENTS.md` | Repo orientation for coding agents | [agents.md](https://agents.md) |
| `templates/llms.txt` | Short crawl aid pointing to canonical entry points | [llmstxt.org](https://llmstxt.org/) |
| `templates/llms-full.txt` | Self-contained summary for LLMs that read one file | llms.txt |
| `templates/.well-known/agents.json` | Machine-readable manifest | agents.md draft |
| `templates/.well-known/openapi.yaml` | OpenAPI 3.1 contract skeleton | [OpenAPI](https://spec.openapis.org/oas/v3.1.0) |
| `templates/robots.txt` | AI-crawler allow-list | — |
| `templates/CITATION.cff` | Citation metadata | [CFF](https://citation-file-format.github.io/) |
| `templates/README-jsonld.html` | `SoftwareApplication` + `HowTo` + `FAQPage` JSON-LD snippets | schema.org |
| `scaffold.sh` | Drop the templates into a target project with one command | — |
| `verify.sh` | Probe every agent-SEO surface locally and against a live URL | — |

## Use it in 30 seconds

```bash
# From any project root:
curl -fsSL https://raw.githubusercontent.com/dnzengou/evo-skillopt/main/tools/agent-seo-kit/scaffold.sh | \
  bash -s -- --name "my-project" --owner "myuser" --repo "my-project"

# Verify:
bash .agent-seo-verify.sh
```

Or clone the repo locally and run:

```bash
cd my-project
PROJECT_NAME="my-project" PROJECT_OWNER="myuser" PROJECT_REPO="my-project" \
  bash /path/to/evo-skillopt/tools/agent-seo-kit/scaffold.sh
```

The scaffold:

1. Copies template files to the target project root, filling in the
   `{{project}}` / `{{owner}}` / `{{repo}}` / `{{description}}`
   placeholders.
2. Writes a `verify.sh` the project can run (or wire into CI) to
   confirm every agent-SEO file is present, well-formed, and reachable.
3. Prints a 5-line checklist of what to manually customize per project
   (endpoints, keywords, license).

## What each artifact buys you

- **`AGENTS.md`** — the single file a coding agent loads to understand
  how to work with your repo (tests, conventions, do-not-touch).
  The agent spends tokens reading this instead of guessing.
- **`llms.txt`** — a well-known entry point every LLM answer engine
  checks for at the site root. 1 paragraph + a linked index.
- **`.well-known/agents.json`** — a JSON manifest an agent runtime
  can parse to know what endpoints your service exposes, what each
  does, and what's authenticated vs. open.
- **`openapi.yaml`** — the industry-standard HTTP contract. Lets any
  OpenAI/Anthropic/Claude Code/Cursor-style agent generate a working
  client in-session.
- **JSON-LD in README** — gets your project into AI answer-engine
  rich results when someone asks "what tool should I use for X?"
- **`robots.txt`** — explicitly allow the AI crawlers you want to be
  found by (GPTBot, ClaudeBot, Google-Extended, PerplexityBot, etc.).

## Not in scope

- Human-facing marketing (press kits, logos, landing-page copy). The
  kit optimizes *technical* discoverability; see [`GTM.md`](../../GTM.md)
  for channel strategy.
- Hosting / CDN config. The kit assumes you already serve your
  repo + docs over HTTP; it doesn't opine on where.
- Analytics. Add Plausible / Fathom / a logs pipeline separately.

## License

MIT — same as the parent `evo-skillopt` project. Take it, fork it,
drop it into private work; no attribution required. If you find
improvements that generalize, a PR back to
`github.com/dnzengou/evo-skillopt` is appreciated but not expected.

## Further reading

- [`GTM.md`](../../GTM.md) — full agent-era GTM playbook
- [`docs/AI_SEO.md`](../../docs/AI_SEO.md) — implementation notes
  (why both repo-root + docs-site copies, what agents cite you with)
- [`verify.sh`](./verify.sh) — the probe script the kit drops into
  the target project
