"""Planning-time cost estimator — pre-run token + dollar estimate.

Operators asking "what will this evolution cost?" get an answer without
running it. The estimator is pure arithmetic plus a built-in price
registry; both can be overridden at call time.

The estimator does NOT measure actual tokens consumed. That requires
hooking the vendored SkillOpt's LLM client, which is out of scope for
the worker extension layer. For post-run truth, read your provider's
usage dashboard; the estimator's job is to be in the right order of
magnitude so an operator can budget before launching.

Public API
----------
    MODELS                           : dict[str, ModelPrice]
    ModelPrice(name, input_per_1k, output_per_1k, provider, updated_at)
    Workload(num_epochs, n_train_items, n_eval_items,
             mean_tokens_per_item, rollouts_per_item,
             reflections_per_item, output_token_ratio)
    estimate_cost(workload, model=…, prices=None) -> Estimate
    list_models() -> list[dict]

Provider price registry is a snapshot — update it in a PR when
provider prices change. Call-site overrides take precedence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Price registry — update when provider prices change. Values are USD per
# 1,000 tokens. Keep models alphabetical; prefer provider-canonical IDs.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelPrice:
    """USD per 1M tokens for one model (provider-page convention)."""

    name: str
    input_per_1m: float
    output_per_1m: float
    provider: str
    updated_at: str   # "YYYY-MM" — one-line provenance for this entry

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provider": self.provider,
            "input_per_1m_usd": self.input_per_1m,
            "output_per_1m_usd": self.output_per_1m,
            "updated_at": self.updated_at,
        }


# Snapshot of public per-1M-token pricing as of early 2026 for the
# provider-ID strings callers commonly pass. The per-1M-token convention
# matches every provider's pricing page; multiply by `tokens / 1_000_000`
# to get dollars. This table is deliberately short — the estimator is a
# budgeting tool, not a billing engine. Extend in a PR when a provider
# ships new models; override per-call via `prices=…`.
MODELS: dict[str, ModelPrice] = {
    # OpenAI
    "gpt-4o": ModelPrice("gpt-4o", 2.50, 10.00, "openai", "2026-01"),
    "gpt-4o-mini": ModelPrice("gpt-4o-mini", 0.15, 0.60, "openai", "2026-01"),
    "gpt-4.1": ModelPrice("gpt-4.1", 3.00, 12.00, "openai", "2026-01"),
    "gpt-4.1-mini": ModelPrice("gpt-4.1-mini", 0.40, 1.60, "openai", "2026-01"),
    "o4-mini": ModelPrice("o4-mini", 1.10, 4.40, "openai", "2026-01"),
    # Anthropic
    "claude-3-5-sonnet": ModelPrice("claude-3-5-sonnet", 3.00, 15.00, "anthropic", "2026-01"),
    "claude-3-5-haiku": ModelPrice("claude-3-5-haiku", 0.80, 4.00, "anthropic", "2026-01"),
    "claude-opus-4": ModelPrice("claude-opus-4", 15.00, 75.00, "anthropic", "2026-01"),
    "claude-sonnet-4": ModelPrice("claude-sonnet-4", 3.00, 15.00, "anthropic", "2026-01"),
    "claude-haiku-4": ModelPrice("claude-haiku-4", 0.80, 4.00, "anthropic", "2026-01"),
    # Google
    "gemini-1.5-pro": ModelPrice("gemini-1.5-pro", 1.25, 5.00, "google", "2026-01"),
    "gemini-1.5-flash": ModelPrice("gemini-1.5-flash", 0.075, 0.30, "google", "2026-01"),
    "gemini-2.5-pro": ModelPrice("gemini-2.5-pro", 2.50, 10.00, "google", "2026-01"),
    # Local / self-hosted — zero per-token cost, non-zero hardware cost
    "local": ModelPrice("local", 0.0, 0.0, "self-hosted", "2026-01"),
}


# ---------------------------------------------------------------------------
# Workload spec and estimate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Workload:
    """A pre-run description of what the SkillOpt loop will consume.

    Attributes are per-epoch unless otherwise noted. ``num_epochs``
    multiplies the totals.

    Defaults match a modest customer-support bot's weekly evolution.
    """

    num_epochs: int = 1
    n_train_items: int = 100
    n_eval_items: int = 25
    mean_tokens_per_item: int = 500
    rollouts_per_item: int = 1
    reflections_per_item: int = 1
    output_token_ratio: float = 0.4   # output tokens as a fraction of input


@dataclass(frozen=True)
class Estimate:
    """Result of a single estimation call."""

    model: str
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    est_cost_usd: float
    breakdown: dict[str, float]
    assumptions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "est_cost_usd": round(self.est_cost_usd, 4),
            "breakdown_usd": {k: round(v, 4) for k, v in self.breakdown.items()},
            "assumptions": self.assumptions,
        }


def list_models() -> list[dict[str, Any]]:
    """Return the known-models registry as a list of dicts."""
    return [m.to_dict() for m in MODELS.values()]


def _resolve_price(model: str, prices: dict[str, ModelPrice] | None) -> ModelPrice:
    registry = {**MODELS, **(prices or {})}
    if model in registry:
        return registry[model]
    # Allow callers to pass an override by model name without re-declaring
    # provider etc. — construct a ModelPrice from the override shape.
    raise KeyError(
        f"unknown model: {model!r} (known: {sorted(registry)}); "
        "pass prices={<name>: ModelPrice(...)} to override."
    )


def estimate_cost(
    workload: Workload,
    model: str,
    prices: dict[str, ModelPrice] | None = None,
) -> Estimate:
    """Estimate token volume and dollar cost for one full evolution.

    Model: rollout, reflection, and gate each produce a pass over the
    workload. Rollout costs n_train_items × rollouts_per_item per epoch;
    reflection costs n_train_items × reflections_per_item per epoch;
    gate costs n_eval_items once per epoch. Each unit consumes
    mean_tokens_per_item input tokens and emits output_token_ratio ×
    mean_tokens_per_item output tokens.
    """
    price = _resolve_price(model, prices)

    per_epoch_rollout_items = workload.n_train_items * workload.rollouts_per_item
    per_epoch_reflect_items = workload.n_train_items * workload.reflections_per_item
    per_epoch_gate_items = workload.n_eval_items

    def tokens_for(items: int) -> tuple[int, int]:
        inp = items * workload.mean_tokens_per_item
        out = int(inp * workload.output_token_ratio)
        return inp, out

    inp_r, out_r = tokens_for(per_epoch_rollout_items * workload.num_epochs)
    inp_f, out_f = tokens_for(per_epoch_reflect_items * workload.num_epochs)
    inp_g, out_g = tokens_for(per_epoch_gate_items * workload.num_epochs)

    def usd(inp: int, out: int) -> float:
        return (inp / 1_000_000.0) * price.input_per_1m + (out / 1_000_000.0) * price.output_per_1m

    breakdown = {
        "rollout": usd(inp_r, out_r),
        "reflect": usd(inp_f, out_f),
        "gate":    usd(inp_g, out_g),
    }
    total_in = inp_r + inp_f + inp_g
    total_out = out_r + out_f + out_g

    return Estimate(
        model=price.name,
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        total_tokens=total_in + total_out,
        est_cost_usd=sum(breakdown.values()),
        breakdown=breakdown,
        assumptions={
            "num_epochs": workload.num_epochs,
            "n_train_items": workload.n_train_items,
            "n_eval_items": workload.n_eval_items,
            "mean_tokens_per_item": workload.mean_tokens_per_item,
            "rollouts_per_item": workload.rollouts_per_item,
            "reflections_per_item": workload.reflections_per_item,
            "output_token_ratio": workload.output_token_ratio,
            "provider": price.provider,
            "prices_updated_at": price.updated_at,
        },
    )
