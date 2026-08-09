# Disclaimer

`evo-skillopt` is free and open-source software provided **"AS IS"**,
without warranty of any kind, express or implied, including but not
limited to the warranties of merchantability, fitness for a particular
purpose, and noninfringement. See [`LICENSE`](./LICENSE) for the
full MIT text.

## No warranty of training outcomes

`evo-skillopt` orchestrates a training loop that mutates natural-language
skill files. The quality, safety, and correctness of the skills it
produces depend entirely on:

- The upstream **SkillOpt** algorithm and its behavior on your data.
- The **held-out evaluation set** you supply.
- The **LLM backend** you connect to and its outputs.
- The **signals** you wire into `POST /train`.

No warranty is made that evolved skills will:

- Improve on their predecessors on every run.
- Match your business, ethical, or regulatory constraints out of the box.
- Be free of undesirable behaviors, biases, or hallucinations.

You are responsible for validating the outputs of this system before
deploying them to real users.

## Not for high-stakes autonomous decisions

Do **not** use `evo-skillopt` — or the skills it produces — as the
sole decision-maker in any of the following without a human in the
loop and appropriate safeguards:

- Medical diagnosis, treatment, or dosing decisions
- Legal advice or the drafting of binding legal documents
- Financial advice, credit decisions, insurance underwriting
- Employment decisions (hiring, firing, promotion, compensation)
- Immigration or benefits eligibility
- Safety-critical systems (industrial control, vehicle control, etc.)
- Any use that is illegal in your jurisdiction

The **HITL review queue** planned for v0.3 (see
[`EvoSkillOpt_Blueprint.md § 5`](./EvoSkillOpt_Blueprint.md#5-capabilities))
is designed to help make some of these use cases tractable, but it
does not remove your responsibility to design an appropriate review
process.

## Third-party services

`evo-skillopt` makes outbound calls to whichever LLM backends you
configure (OpenAI, Anthropic, Google, Azure OpenAI, local models,
etc.). You are responsible for:

- Complying with the terms of service of each provider you use.
- Handling and storing API keys securely (see [`SECURITY.md`](./SECURITY.md)).
- The cost of tokens consumed during training runs.
- The privacy of any data you send to a hosted provider.

## Data protection

If the signals or evaluation examples you send to `POST /train`
contain personal data as defined by GDPR, CCPA, PIPEDA, or any
comparable regime, you are the data controller. You are responsible
for lawful basis, retention, redaction, and any required user notice.

## Not affiliated with upstream

See [`TRADEMARKS.md`](./TRADEMARKS.md) for the full non-affiliation
statement regarding upstream SkillOpt and any named third parties.

## Reporting concerns

Security or safety concerns → [`SECURITY.md`](./SECURITY.md).
Trademark / branding concerns → [`TRADEMARKS.md`](./TRADEMARKS.md).
Everything else → open a GitHub issue.
