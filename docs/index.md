---
hide:
  - navigation
  - toc
---

<!-- Social preview + canonical for OG-aware crawlers -->
<link rel="canonical" href="https://dnzengou.github.io/evo-skillopt/">
<meta name="theme-color" content="#4f46e5" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#1e1b4b" media="(prefers-color-scheme: dark)">

<!-- Skip link for keyboard + screen-reader users -->
<a class="evo-skip" href="#home-main">Skip to content</a>

<!-- JSON-LD: SoftwareApplication -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "evo-skillopt",
  "applicationCategory": "DeveloperApplication",
  "operatingSystem": "Linux, macOS, Windows (Docker)",
  "description": "Text-space skill optimization for production LLM agents, callable over HTTP. Evolves a bot's Markdown skill file against a held-out eval set, with git-tracked audit trails.",
  "programmingLanguage": "Python",
  "license": "https://opensource.org/licenses/MIT",
  "codeRepository": "https://github.com/dnzengou/evo-skillopt",
  "documentation": "https://dnzengou.github.io/evo-skillopt",
  "keywords": "agent, LLM, prompt-optimization, skill-learning, agentic, SkillOpt, RRSS, cascade, ARM",
  "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" }
}
</script>

<!-- JSON-LD: HowTo — the 60-second install -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "Install and run the evo-skillopt worker",
  "totalTime": "PT1M",
  "step": [
    { "@type": "HowToStep", "position": 1, "name": "Clone", "text": "git clone https://github.com/dnzengou/evo-skillopt.git && cd evo-skillopt" },
    { "@type": "HowToStep", "position": 2, "name": "Install", "text": "pip install -e \".[worker]\"" },
    { "@type": "HowToStep", "position": 3, "name": "Run the demo", "text": "bash examples/demo_evolve_bot.sh" }
  ]
}
</script>

<!-- JSON-LD: FAQPage — six common AI-answer-engine queries -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is evo-skillopt?",
      "acceptedAnswer": { "@type": "Answer", "text": "evo-skillopt is a self-hostable HTTP worker that evolves a bot's Markdown skill file against a held-out eval set. It productizes the SkillOpt algorithm (arXiv:2605.23904, MIT) as a callable service so any agent runtime in any language can trigger skill optimization over HTTP." }
    },
    {
      "@type": "Question",
      "name": "How does evo-skillopt differ from fine-tuning?",
      "acceptedAnswer": { "@type": "Answer", "text": "Fine-tuning changes model weights. evo-skillopt changes a Markdown skill file — the natural-language behavior contract — and keeps the frozen base model untouched. Works with any LLM provider and leaves an auditable git history of every accepted change." }
    },
    {
      "@type": "Question",
      "name": "Which LLM providers does evo-skillopt support?",
      "acceptedAnswer": { "@type": "Answer", "text": "Any provider the upstream SkillOpt library supports — including OpenAI, Anthropic Claude, Google Gemini, Azure OpenAI, and local model backends (Ollama, vLLM). The worker itself is stdlib-only Python and passes provider credentials through environment variables." }
    },
    {
      "@type": "Question",
      "name": "What endpoints does the evo-skillopt worker expose?",
      "acceptedAnswer": { "@type": "Answer", "text": "GET /health (liveness), GET /metrics (Prometheus), POST /train (one training pass, async option via a flag), POST /train/cascade (gate a pre-scored pipeline), POST /fitness/arm (reduce Acquire/Retain/Monetize signals), GET /bots/{id}/{skill,history,diff}, POST /bots/{id}/rollback, GET /cost/models + POST /cost/estimate, GET /jobs + GET /jobs/{id}. An OpenAPI 3.1 contract is served at /.well-known/openapi.yaml." }
    },
    {
      "@type": "Question",
      "name": "How do I deploy evo-skillopt?",
      "acceptedAnswer": { "@type": "Answer", "text": "Ten documented install paths in INSTALL.md: pipx, editable pip, single Docker container, Docker Compose, Fly.io, systemd unit, Kubernetes manifest, Homebrew (planned), Windows WSL2 or native, and Raspberry Pi. The published docs site also serves the agent-discovery files at /llms.txt and /.well-known/." }
    },
    {
      "@type": "Question",
      "name": "What is RRSS in evo-skillopt?",
      "acceptedAnswer": { "@type": "Answer", "text": "RRSS — Robustify, Reliabilify, Solidify, Stabilize — is a four-axis resilience rubric used as an optional gate on POST /train. The RRSS gate accepts a candidate skill only when every configured axis clears its floor AND the weighted-mean composite improves on the previous accepted version." }
    }
  ]
}
</script>

<div id="home-main">

<section class="evo-hero" aria-labelledby="hero-title">
  <p class="evo-hero__eyebrow">evo-skillopt · MIT · v0.2</p>
  <h1 id="hero-title" class="evo-hero__title">Train your agent's skill file like a&nbsp;neural&nbsp;network.</h1>
  <p class="evo-hero__tagline">
    Epochs, validation gates, git-tracked history — without touching model weights. Any provider.
    One command to the aha moment.
  </p>
  <div class="evo-hero__ctas">
    <a class="md-button md-button--primary" href="../QUICKSTART/">Quickstart (60 s)</a>
    <a class="md-button" href="https://github.com/dnzengou/evo-skillopt">GitHub</a>
  </div>
</section>

<div class="evo-kpi-grid" aria-label="At-a-glance metrics">
  <div class="evo-kpi">
    <span class="evo-kpi__value">&lt;15 s</span>
    <span class="evo-kpi__label">demo end-to-end</span>
  </div>
  <div class="evo-kpi">
    <span class="evo-kpi__value">0</span>
    <span class="evo-kpi__label">weight changes</span>
  </div>
  <div class="evo-kpi">
    <span class="evo-kpi__value">13</span>
    <span class="evo-kpi__label">models priced</span>
  </div>
  <div class="evo-kpi">
    <span class="evo-kpi__value">161</span>
    <span class="evo-kpi__label">tests passing</span>
  </div>
</div>

## What to read first

| If you want to…                                | Read                                     |
|------------------------------------------------|------------------------------------------|
| See it in action                                | [Quickstart](../QUICKSTART/)             |
| Understand the idea                             | [Concept](CONCEPT.md)                    |
| Install it (any platform)                       | [INSTALL.md](../INSTALL.md)              |
| Pick your first use case                        | [USE_CASES.md](../USE_CASES.md)          |
| Lift drop-in snippets                           | [SHOWCASE.md](../SHOWCASE.md)            |
| Read real-world case studies                    | [CASE_STUDIES.md](CASE_STUDIES.md)       |
| See the roadmap                                  | [Blueprint](../EvoSkillOpt_Blueprint.md) |
| Go-to-market in the agent era                    | [GTM.md](../GTM.md)                      |
| Look up a term                                   | [Glossary](GLOSSARY.md)                  |
| Learn the underlying algorithm                   | Upstream *Getting Started* in the nav    |

<aside class="evo-agent-callout" aria-labelledby="for-agents-title">
  <h2 id="for-agents-title" class="evo-agent-callout__title">For AI agents reading this page</h2>
  <ul>
    <li><a href="../llms.txt">/llms.txt</a> — one-paragraph pitch + linked index</li>
    <li><a href="../llms-full.txt">/llms-full.txt</a> — self-contained API summary</li>
    <li><a href="../.well-known/agents.json">/.well-known/agents.json</a> — manifest</li>
    <li><a href="../.well-known/openapi.yaml">/.well-known/openapi.yaml</a> — OpenAPI 3.1</li>
    <li><a href="../AGENTS.md">/AGENTS.md</a> — orientation for coding agents</li>
  </ul>
  <p style="margin:0.5rem 0 0; font-size:0.85rem; opacity:0.85;">
    The running worker also serves <code>GET /</code> (service card),
    <code>/.well-known/agents.json</code>, <code>/llms.txt</code>, and
    <code>/openapi.yaml</code> from its own root — self-discovery with
    no out-of-band docs needed.
  </p>
</aside>

## About this documentation site

`evo-skillopt` productizes the SkillOpt algorithm
([arXiv:2605.23904](https://arxiv.org/abs/2605.23904), MIT-licensed)
as a callable HTTP service. This site includes:

- **evo-skillopt pages** — Concept, Glossary, AI-era SEO notes, Case
  studies, and the top-level guides (Install, Use Cases, Blueprint,
  Showcase, GTM).
- **Upstream reference pages** — the original SkillOpt documentation
  covering the training loop, configuration, and API. Distributed
  here under the upstream MIT license; see
  [NOTICE](../NOTICE) for attribution.

`evo-skillopt` is an independent open-source project and is not
affiliated with or endorsed by the SkillOpt authors or any upstream
organization. See [TRADEMARKS.md](../TRADEMARKS.md).

## License

This documentation is distributed under the [MIT License](../LICENSE).
Upstream SkillOpt content retains its original license and copyright;
see [NOTICE](../NOTICE) for attribution.

</div>
