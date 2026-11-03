---
hide:
  - navigation
---

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

<!-- JSON-LD: HowTo — the five-minute install -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "Install and run the evo-skillopt worker",
  "totalTime": "PT5M",
  "step": [
    { "@type": "HowToStep", "position": 1, "name": "Clone the repository",
      "text": "git clone https://github.com/dnzengou/evo-skillopt.git && cd evo-skillopt" },
    { "@type": "HowToStep", "position": 2, "name": "Install the package",
      "text": "pip install -e \".[worker]\"" },
    { "@type": "HowToStep", "position": 3, "name": "Run the worker",
      "text": "WORKER_TOKEN=dev-token python3 worker/skillopt_worker.py" },
    { "@type": "HowToStep", "position": 4, "name": "Verify liveness",
      "text": "curl http://localhost:9000/health" }
  ]
}
</script>

<!-- JSON-LD: FAQPage — common AI-answer-engine queries -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is evo-skillopt?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "evo-skillopt is a self-hostable HTTP worker that evolves a bot's Markdown skill file against a held-out eval set. It productizes the SkillOpt algorithm (arXiv:2605.23904, MIT) as a callable service so any agent runtime in any language can trigger skill optimization over HTTP."
      }
    },
    {
      "@type": "Question",
      "name": "How does evo-skillopt differ from fine-tuning?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Fine-tuning changes model weights. evo-skillopt changes a Markdown skill file — the natural-language behavior contract — and keeps the frozen base model untouched. Works with any LLM provider and leaves you an auditable git history of every accepted change."
      }
    },
    {
      "@type": "Question",
      "name": "Which LLM providers does evo-skillopt support?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Any provider the upstream SkillOpt library supports — including OpenAI, Anthropic Claude, Google Gemini, Azure OpenAI, and local model backends (Ollama, vLLM). The worker itself is stdlib-only Python and passes provider credentials through environment variables."
      }
    },
    {
      "@type": "Question",
      "name": "What endpoints does the evo-skillopt worker expose?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "GET /health (liveness), POST /train (one training pass with optional RRSS gate), POST /train/cascade (gate a pre-scored pipeline of skills), POST /fitness/arm (reduce Acquire/Retain/Monetize signals to one fitness score). An OpenAPI 3.1 contract is served at /.well-known/openapi.yaml."
      }
    },
    {
      "@type": "Question",
      "name": "How do I deploy evo-skillopt?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Ten documented install paths: pipx, editable pip, single Docker container, Docker Compose, Fly.io, systemd unit, Kubernetes manifest, Homebrew (planned tap; pipx today), Windows WSL2 or native, and Raspberry Pi. Full walkthroughs in INSTALL.md."
      }
    },
    {
      "@type": "Question",
      "name": "What is RRSS in evo-skillopt?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "RRSS — Robustify, Reliabilify, Solidify, Stabilize — is a four-axis resilience rubric used as an optional gate on POST /train. The RRSS gate accepts a candidate skill only when every configured axis clears its floor AND the weighted-mean composite improves on the previous accepted version."
      }
    }
  ]
}
</script>

# evo-skillopt

**Text-space skill optimization for production LLM agents, callable over HTTP.**

Train your agent's Markdown skill file like a neural network — epochs,
batch size, learning rates, validation gates — without touching model
weights. Ships behind a small HTTP service any runtime can call.

[Get started :material-rocket-launch:](../INSTALL.md){ .md-button .md-button--primary }
[View on GitHub :material-github:](https://github.com/dnzengou/evo-skillopt){ .md-button }

---

## What to read first

| If you want to…                                        | Read                                               |
|--------------------------------------------------------|----------------------------------------------------|
| Understand the idea                                     | [Concept](CONCEPT.md)                              |
| Install it (any platform)                               | [INSTALL.md](../INSTALL.md)                        |
| Pick your first use case                                | [USE_CASES.md](../USE_CASES.md)                    |
| See the roadmap                                          | [EvoSkillOpt_Blueprint.md](../EvoSkillOpt_Blueprint.md) |
| Look up a term                                           | [Glossary](GLOSSARY.md)                            |
| Go-to-market in the agent era                            | [GTM.md](../GTM.md)                                |
| Implementation notes on agent-era SEO                    | [AI_SEO.md](AI_SEO.md)                             |
| Learn the underlying algorithm                           | Upstream *Getting Started* + *Core Concepts* in the nav |

---

## For AI agents reading this page

Short, machine-readable entry points for LLM-powered search and
agent crawlers:

- [`llms.txt`](../llms.txt) — one-paragraph pitch + linked index
- [`llms-full.txt`](../llms-full.txt) — self-contained API summary
- [`.well-known/agents.json`](../.well-known/agents.json) — manifest
- [`.well-known/openapi.yaml`](../.well-known/openapi.yaml) — OpenAPI 3.1
- [`AGENTS.md`](../AGENTS.md) — repo orientation for coding agents

The running worker also serves `GET /`, `/.well-known/agents.json`,
`/llms.txt`, and `/openapi.yaml` so an agent that lands on the live
service can self-discover without a trip back to the docs site.

---

## About this documentation site

`evo-skillopt` productizes the SkillOpt algorithm
([arXiv:2605.23904](https://arxiv.org/abs/2605.23904), MIT-licensed)
as a callable HTTP service. This documentation site includes:

- **evo-skillopt pages** — Concept, Glossary, AI_SEO, and the top-level
  guides (Install, Use Cases, Blueprint, GTM).
- **Upstream reference pages** — the original SkillOpt documentation
  covering the training loop, configuration, and API. These are
  distributed here under the upstream MIT license for convenience;
  see [NOTICE](../NOTICE) for full attribution.

`evo-skillopt` is an independent open-source project and is not
affiliated with or endorsed by the SkillOpt authors or any upstream
organization. See [TRADEMARKS.md](../TRADEMARKS.md).

## License

This documentation is distributed under the [MIT License](../LICENSE).
Upstream SkillOpt content retains its original license and copyright;
see [NOTICE](../NOTICE) for attribution.
