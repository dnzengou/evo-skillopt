---
hide:
  - navigation
---

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
| Learn the underlying algorithm                           | Upstream *Getting Started* + *Core Concepts* in the nav |

---

## About this documentation site

`evo-skillopt` productizes the SkillOpt algorithm
([arXiv:2605.23904](https://arxiv.org/abs/2605.23904), MIT-licensed)
as a callable HTTP service. This documentation site includes:

- **evo-skillopt pages** — Concept, Glossary, and the top-level
  guides (Install, Use Cases, Blueprint).
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
