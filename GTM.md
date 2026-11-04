# GTM.md — go-to-market for an agent-era product

A product-neutral playbook. Written as the strategy `evo-skillopt`
itself uses, documented so other projects can replicate it. Nothing
here depends on a specific vendor, venture, or growth stack.

> **The thesis.** In 2026, half the surface a technical product is
> discovered on is read by an LLM, not a human. The product that is
> parseable by an agent wins the agent's citation. The product that is
> cited by agents wins the funnel it costs nothing to re-fill.

---

## 1. What has changed

Buyers no longer land on your landing page cold. They land on:

- an LLM-generated answer in an AI search engine (Perplexity, ChatGPT
  Search, Google AI Overviews, Claude Search, Grok, Kagi Assistant, DuckAssist,
  You.com, Brave Leo)
- a coding assistant's tool-use tab (Claude Code, Cursor, Cline,
  Aider, Windsurf, JetBrains AI, Copilot Workspace)
- an agent-directed procurement flow (an LLM reading `agents.json`
  manifests to decide which API to call)

Three practical consequences for anyone building a developer-facing
product:

1. **Your GitHub repo IS a sales page.** Agents read it; buyers read
   the agent's summary of it. The first screen of `README.md` matters
   more than any blog post.
2. **Your docs site IS your sitemap.** Not for Google — for GPT. If
   an LLM can't route from `site_url` to a canonical answer in one
   fetch, the citation goes to a competitor who could.
3. **Your API IS your pitch deck.** An agent that can introspect your
   service in one `GET /` picks it over an API it has to bookmark
   and come back to with documentation in another tab.

## 2. The three audiences you now serve

| Audience | What they do | What they want | Where they look |
|----------|--------------|----------------|-----------------|
| Humans | Read, trial, decide | A clear one-screen pitch | README, landing page, HN, X |
| LLM answer engines | Cite in generated answers | Clean, machine-parseable summaries | `llms.txt`, JSON-LD, OpenGraph, structured FAQs |
| Agent runtimes | Call the API in a pipeline | Self-describing endpoints | `agents.json`, OpenAPI, service card, auth story |

Every piece of surface is in service of at least two of them. The
discipline is to not over-optimize for any one.

## 3. The agent-era SEO stack

Minimum viable surface for a developer-facing product shipping today:

| Artifact | Purpose | Convention |
|----------|---------|------------|
| `README.md` with JSON-LD | Human overview + schema.org `SoftwareApplication` | [schema.org](https://schema.org/) |
| `AGENTS.md` | One-page orientation for coding agents | [agents.md](https://agents.md) |
| `llms.txt` | Short, linked index of entry points | [llmstxt.org](https://llmstxt.org/) |
| `llms-full.txt` | Self-contained summary for LLMs that read one file | llms.txt |
| `.well-known/agents.json` | Machine-readable capabilities manifest | emerging; draft at agents.md |
| `.well-known/openapi.yaml` | OpenAPI 3.1 contract | [OpenAPI](https://spec.openapis.org/oas/v3.1.0) |
| `CITATION.cff` | How to cite you (academic + agent reference) | [CFF](https://citation-file-format.github.io/) |
| `robots.txt` | Explicit allow-list of agent user-agents | — |
| Service card at `GET /` | Live introspection on the running service | — |
| FAQ / HowTo JSON-LD in docs | Rich-result eligibility in AI answer engines | schema.org |

evo-skillopt ships every one of these. The commit history on this
repo is the reference implementation.

## 4. The content loop (produce → distribute → measure)

### 4.1 Produce

Three content formats carry disproportionate weight:

- **The 150-word summary.** One paragraph that captures the product
  in a form an LLM will quote verbatim. Lives at the top of
  `llms.txt` and in the JSON-LD `description` field.
- **The "1-2-3 install" block.** Three shell commands that work. Must
  work on a first-run laptop with no prior config. If it takes four
  commands, cut one.
- **The use-case catalog with ROI math.** One row per pattern:
  what, signal, cadence, cost/benefit. Lives at
  [`USE_CASES.md`](./USE_CASES.md).

Everything else is a refinement of these three.

### 4.2 Distribute

The channel mix a developer-facing product can actually service:

| Channel | Agent-reachable? | Human-reachable? | Effort / week |
|---------|------------------|------------------|---------------|
| GitHub (repo activity, releases) | yes | yes | 2 h |
| Docs site (MkDocs → gh-pages) | yes | yes | 1 h |
| Hacker News (launch, Show HN) | yes, via Algolia | yes | 2 h / launch |
| Dev.to / Hashnode | yes | yes | 1 h / post |
| Weekly release post on X + LinkedIn | partial | yes | 1 h |
| Agent registries (as they emerge) | yes | partial | 0.5 h / month |
| Podcast appearances | no | yes | 2 h / appearance |

Note that **no paid channel** appears in this list. Paid acquisition
for a free MIT tool returns nothing you can measure in the first six
months. The leverage is in writing once and being cited by agents
every day forever.

### 4.3 Measure

Four meters, read weekly:

- **Agent citation rate.** How often an AI answer engine names your
  project in a response for the queries you care about. Measured by
  asking the question in each engine and counting. Tedious but real.
- **GHCR / PyPI / npm pulls.** Deployment is the acquisition signal.
- **`.well-known/agents.json` request rate.** Only agents hit this.
  Rising = your pitch is reaching them.
- **GitHub stars + issues.** Leading indicator for community trust.

Not a meter: "impressions." If you can't name the LLM that cited you,
you weren't cited.

## 5. Discovery: the agent's first fetch

An LLM crawling your project with no prior knowledge should get
everything it needs from one of these entry points:

1. `GET https://your-repo/llms.txt` — one paragraph + a linked index.
2. `GET https://your-service/` — live JSON service card.
3. `GET https://your-service/.well-known/agents.json` — machine-readable
   capabilities manifest.
4. `GET https://your-service/.well-known/openapi.yaml` — endpoint
   contract.

The failure mode you are trying to avoid: the agent reads your docs
site, extracts the API surface, tries a call, hits a cryptic 404,
retries once, and gives up with a summary that says "this project
looked promising but we couldn't verify the API." That summary
survives in its vector store for months.

Prevent it by making the live service self-discover. The
`evo-skillopt` worker serves `agents.json`, `openapi.yaml`,
`llms.txt`, and `AGENTS.md` from itself — no out-of-band docs
required.

## 6. The commercial follow-through

Nothing in the agent-SEO stack generates revenue by itself. It lowers
the cost of every downstream funnel:

| Funnel step | Without agent-SEO | With agent-SEO |
|-------------|-------------------|----------------|
| First awareness | Marketing push | An agent names you in an answer |
| Evaluation | Buyer reads 6 competing landing pages | Buyer's coding agent reads your OpenAPI |
| Trial | "Will this integrate?" | Agent prototypes the call in-session |
| Deploy | Human writes integration code | Agent writes it from `agents.json` |
| Expand | AE books a call | Buyer's team adopts the second use case because the first survived agent-driven refactors |

The leverage compounds. One well-formed `llms.txt` is cited for
months. One missing OpenAPI is a lost deal nobody tells you about.

## 7. Where a commercial layer plugs in (without contaminating the core)

`evo-skillopt` is MIT. The commercial playbook — if you choose to run
one on top — lives in a separate repo so the open core stays
contributor-friendly. Suggested shape:

| Tier | Scope | Price anchor |
|------|-------|--------------|
| Self-host | Free · MIT · the OSS worker + examples | $0 |
| Managed solo | 1 tenant · 1 bot · weekly evolution · hosted worker | $19/mo |
| Managed team | 5 bots · daily cadence · private eval sets · dashboard | $99/mo |
| Managed growth | 50 bots · A/B deploy · reward-model gate · HITL queue | $499/mo |
| Enterprise | Federated meta-skills · SSO · compliance · on-prem · SLA | custom |

Pricing anchors: observability tools ~$40/seat, eval frameworks ~$100/seat,
prompt versioning ~$50/seat. evo-skillopt covers the union + closes the
loop — defensible at 2× on the Team tier.

These numbers are examples. The point is only that the OSS repo owes
nothing to the business model and every commercial decision belongs
on the other side of the wall.

## 8. First 30 days

If you're copying this playbook, do these in order:

### Week 1 — surface

- [ ] Add `llms.txt`, `llms-full.txt`, `AGENTS.md` at repo root.
- [ ] Add `.well-known/agents.json` and `.well-known/openapi.yaml`.
- [ ] Add JSON-LD `SoftwareApplication` block at the top of `README.md`.
- [ ] Add a `GET /` service card to the running service.
- [ ] Ensure `site_url` in docs config points at a live URL.

### Week 2 — publish

- [ ] Ship MkDocs (or your docs tool) to GitHub Pages behind a CI
      workflow. Serve `llms.txt` and `.well-known/` from the docs site.
- [ ] Verify the discovery files at the site URL with `curl`.
- [ ] Verify the service URL serves the same files from its own root.
- [ ] Register with agent registries that exist in your category.

### Week 3 — write

- [ ] One "Show HN" post. No marketing, just what the thing does.
- [ ] One dev.to or hashnode post with a concrete use case + ROI math.
- [ ] One weekly release post on X and LinkedIn. Tag the project
      properly so it stays in search.

### Week 4 — measure

- [ ] Ask your target queries in each AI engine. Record citation rate.
- [ ] Count installs (pip, docker, ghcr).
- [ ] Decide next month: more surface, or more content? (For a repo
      with < 500 stars, usually more content.)

## 9. Anti-patterns

- **Writing for Google and hoping agents follow.** Agents parse
  structure, not keyword density. Shipping schema.org before
  shipping SEO copy wins the ranking twice.
- **Behind-paywall docs.** An LLM that cannot reach your docs
  cannot cite them. A free tier of docs behind a login costs you
  more than a free tier of software behind a login.
- **"Contact sales" as the top CTA.** For a developer product in
  2026, this is a filter that keeps the agents out, not the buyers.
- **Over-branding the manifest.** `agents.json` is read by a machine.
  Put the capabilities in it, not the brand voice.
- **One-shot launches.** Your first HN post is not the moment the
  agent-era funnel starts. The 50th commit is.

## 10. What to measure to know this is working

Three leading indicators, in order of sensitivity:

1. **`/.well-known/agents.json` request rate** — rises before stars do.
2. **Unsolicited "we found you via <AI engine>" in issues or Slack**
   — the acquisition story for the next 12 months.
3. **GitHub star velocity** — lags the above by 2-6 weeks, but
   most legible to third parties.

If none of the three move after three months of disciplined content,
the thesis isn't holding in your category yet. That's useful
information. Don't commit to a strategy; commit to a loop.

---

## See also

- [`AGENTS.md`](./AGENTS.md) — the agents-oriented repo map
- [`llms.txt`](./llms.txt) and [`llms-full.txt`](./llms-full.txt)
  — the LLM crawl aids used here
- [`.well-known/agents.json`](./.well-known/agents.json) — the manifest
- [`docs/AI_SEO.md`](./docs/AI_SEO.md) — implementation notes
- [`USE_CASES.md`](./USE_CASES.md) — the ROI math buyers want
- [`EvoSkillOpt_Blueprint.md`](./EvoSkillOpt_Blueprint.md) — the
  living roadmap
