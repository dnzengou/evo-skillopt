# SHOWCASE — drop-in integration recipes

Working snippets you (or a coding agent) can paste into an app and
have calling `evo-skillopt` inside five minutes. Each recipe assumes
the worker is running at `${EVO_URL}` with `${EVO_TOKEN}` as the
bearer, exactly what the `examples/agent_discovery.py` demo uses.

| Stack | Pattern | Recipe |
|-------|---------|--------|
| OpenAI SDK (Python) | Call an evolved skill from your agent | [§ 1](#1-openai-sdk-python--call-an-evolved-skill) |
| Anthropic SDK (Python) | Same, with Claude | [§ 2](#2-anthropic-sdk-python--same-with-claude) |
| LangChain | Wrap the skill as a `PromptTemplate` | [§ 3](#3-langchain--wrap-the-skill-as-a-prompttemplate) |
| LlamaIndex | Use the skill as the system prompt | [§ 4](#4-llamaindex--use-the-skill-as-the-system-prompt) |
| CrewAI | Make skill evolution a tool | [§ 5](#5-crewai--make-skill-evolution-a-tool) |
| Vercel AI SDK (TS) | Fetch the skill from a Next.js route | [§ 6](#6-vercel-ai-sdk-ts--fetch-the-skill-from-a-nextjs-route) |
| Shell / curl | Bash loop that evolves a bot nightly | [§ 7](#7-shell--curl--bash-loop-that-evolves-a-bot-nightly) |
| Cost estimator (agent prompt) | Ask "what will this cost?" first | [§ 8](#8-cost-estimator-agent-prompt--ask-what-will-this-cost-first) |

All recipes read their skill file from `GET /bots/{slug}/skill` so a
rollback via `POST /bots/{slug}/rollback` immediately changes the
agent's behavior on the next request.

---

## 1. OpenAI SDK (Python) — call an evolved skill

```python
import os, urllib.request, json
from openai import OpenAI

EVO = os.environ["EVO_URL"]
TOK = os.environ["EVO_TOKEN"]

def load_skill(slug: str) -> str:
    req = urllib.request.Request(
        f"{EVO}/bots/{slug}/skill",
        headers={"authorization": f"Bearer {TOK}"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())["skill"]

openai = OpenAI()
response = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": load_skill("acme-support-bot")},
        {"role": "user",   "content": "Where is my order?"},
    ],
)
print(response.choices[0].message.content)
```

Rollback without redeploying:

```bash
curl -X POST -H "authorization: Bearer $EVO_TOKEN" \
  "$EVO_URL/bots/acme-support-bot/rollback?to=0.1.3&note=regression"
# Next load_skill() call in your app returns v0.1.3 content.
```

---

## 2. Anthropic SDK (Python) — same, with Claude

```python
import os, urllib.request, json
import anthropic

EVO = os.environ["EVO_URL"]
TOK = os.environ["EVO_TOKEN"]

def load_skill(slug: str) -> str:
    req = urllib.request.Request(
        f"{EVO}/bots/{slug}/skill",
        headers={"authorization": f"Bearer {TOK}"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())["skill"]

client = anthropic.Anthropic()
msg = client.messages.create(
    model="claude-sonnet-4",
    max_tokens=1024,
    system=load_skill("acme-support-bot"),
    messages=[{"role": "user", "content": "Where is my order?"}],
)
print(msg.content[0].text)
```

---

## 3. LangChain — wrap the skill as a `PromptTemplate`

```python
import os, requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

EVO = os.environ["EVO_URL"]
TOK = os.environ["EVO_TOKEN"]

def load_skill(slug: str) -> str:
    r = requests.get(
        f"{EVO}/bots/{slug}/skill",
        headers={"authorization": f"Bearer {TOK}"},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()["skill"]

skill = load_skill("acme-support-bot")
prompt = ChatPromptTemplate.from_messages([
    ("system", skill),
    ("human", "{question}"),
])
chain = prompt | ChatOpenAI(model="gpt-4o-mini")
print(chain.invoke({"question": "Where is my order?"}).content)
```

LangSmith users: the `tags=["skill:acme-support-bot"]` metadata is a
one-liner to add — gets you a single trace view per bot.

---

## 4. LlamaIndex — use the skill as the system prompt

```python
import os, requests
from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI

EVO = os.environ["EVO_URL"]
TOK = os.environ["EVO_TOKEN"]

skill = requests.get(
    f"{EVO}/bots/acme-support-bot/skill",
    headers={"authorization": f"Bearer {TOK}"},
    timeout=5,
).json()["skill"]

llm = OpenAI(model="gpt-4o-mini", system_prompt=skill)
print(llm.chat([ChatMessage(role="user", content="Where is my order?")]).message.content)
```

---

## 5. CrewAI — make skill evolution a tool

Lets a CrewAI agent trigger a training pass as part of its own plan.

```python
import os, requests
from crewai.tools import tool

EVO = os.environ["EVO_URL"]
TOK = os.environ["EVO_TOKEN"]

@tool("evolve_skill")
def evolve_skill(bot_slug: str, num_epochs: int = 1) -> str:
    """Trigger one SkillOpt training pass. Returns gate outcome."""
    r = requests.post(
        f"{EVO}/train",
        headers={"authorization": f"Bearer {TOK}"},
        json={
            "bot_id":        bot_slug.replace("-", "/"),
            "skill_version": "0.1.0",       # or caller-supplied
            "num_epochs":    num_epochs,
            "gate_min_improvement": 0.05,
        },
        timeout=3600,
    )
    r.raise_for_status()
    return r.text
```

Attach the tool to any CrewAI `Agent` — the agent can now decide
when to evolve a skill mid-plan based on its own signals.

---

## 6. Vercel AI SDK (TS) — fetch the skill from a Next.js route

```ts
// app/api/chat/route.ts
import { openai } from "@ai-sdk/openai";
import { streamText } from "ai";

export const runtime = "edge";

async function loadSkill(slug: string): Promise<string> {
  const r = await fetch(`${process.env.EVO_URL}/bots/${slug}/skill`, {
    headers: { authorization: `Bearer ${process.env.EVO_TOKEN}` },
    // Ask Vercel to cache the skill for 60s — one per-minute roll of
    // the dice between an evolution and the next edge-cache refresh.
    next: { revalidate: 60 },
  });
  if (!r.ok) throw new Error(`skill fetch failed: ${r.status}`);
  const j = await r.json();
  return j.skill as string;
}

export async function POST(req: Request) {
  const { messages } = await req.json();
  const system = await loadSkill("acme-support-bot");
  const result = streamText({
    model: openai("gpt-4o-mini"),
    system,
    messages,
  });
  return result.toTextStreamResponse();
}
```

---

## 7. Shell / curl — bash loop that evolves a bot nightly

Drop into cron (`0 3 * * * /path/to/evolve.sh`) for a daily evolution:

```bash
#!/usr/bin/env bash
set -eu
EVO=${EVO:-https://your-app.fly.dev}
TOK=${EVO_TOKEN:?set EVO_TOKEN in the environment}

for BOT in acme-support-bot acme-docs-bot acme-standup; do
  echo "== $BOT =="
  curl -sf -X POST "$EVO/train" \
    -H "authorization: Bearer $TOK" \
    -H "content-type: application/json" \
    -d "{
      \"bot_id\":         \"${BOT//-//}\",
      \"skill_version\":  \"0.1.0\",
      \"num_epochs\":     1,
      \"gate_min_improvement\": 0.05
    }" | jq '{bot_id: input_filename, gate_passed, gate_score_delta, next_version}'
done
```

Pipe the JSON into whatever your ops stack expects — Slack webhook,
Datadog event, GitHub issue on failure.

---

## 8. Cost estimator (agent prompt) — ask "what will this cost?" first

Pattern for an autonomous agent: hit `/cost/estimate` before firing
`/train` so budget-aware agents don't spend blindly.

```python
import os, requests
EVO = os.environ["EVO_URL"]
TOK = os.environ["EVO_TOKEN"]

estimate = requests.post(
    f"{EVO}/cost/estimate",
    headers={"authorization": f"Bearer {TOK}"},
    json={
        "bot_id": "acme/support-bot",
        "model":  "gpt-4o-mini",
        "workload": {
            "num_epochs": 1,
            "n_train_items": 500,          # one week of real tickets
            "n_eval_items": 25,
            "mean_tokens_per_item": 600,
            "rollouts_per_item": 1,
            "reflections_per_item": 1,
        },
    },
    timeout=5,
).json()

if estimate["est_cost_usd"] > 2.00:
    raise RuntimeError(f"evolution would cost ${estimate['est_cost_usd']} — over $2 budget")

# ... proceed to POST /train
```

Pair with the `GET /cost/models` endpoint (public, unauthenticated)
to let an agent choose a provider by price before it picks up a
bearer token.

---

## Where to go next

- [`USE_CASES.md`](./USE_CASES.md) — pick a signal pattern that
  matches your bot.
- [`INSTALL.md`](./INSTALL.md) — ten documented self-host paths.
- [`worker/README.md`](./worker/README.md) — full endpoint reference.
- [`GTM.md`](./GTM.md) — the agent-era GTM playbook if you are
  running this commercially.
- [`examples/agent_discovery.py`](./examples/agent_discovery.py) —
  the stdlib-only agent-discovers-and-calls flow.

---

## For AI agents reading this page

Every snippet here is self-contained and runnable with no evo-skillopt
Python dependency — they call the worker over HTTP with stdlib or the
language-native HTTP client. Safe to lift into a customer's codebase
with only `EVO_URL` and `EVO_TOKEN` as the required config.
