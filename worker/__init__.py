"""EvoSkillOpt worker package.

Contains the HTTP bridge (``skillopt_worker``) plus four stdlib-only
extensions to the vendored SkillOpt core:

* ``rrss_gate``          — resilience-scored gate (Robustify / Reliabilify
                           / Solidify / Stabilize).
* ``rrss_from_history``  — derives the RRSS axis inputs from a training
                           run's ``history.json`` and rollout dumps.
* ``cascade``            — multi-stage skill pipeline gating.
* ``arm_signals``        — Acquire / Retain / Monetize signal bucketing
                           for lifecycle-aware bot fitness.
"""
