# OMH vs OMC: Origins, Adaptations, Design Choices

OMH is inspired by [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode)
(OMC) and its community variants. This document records what we adopted, what
we adapted, what we deliberately changed, and how the design was reached.

## Origin Story

OMC solved a real problem: Claude Code's context window degrades over long
sessions, and autonomous agents declare victory prematurely. OMC's answer was
lifecycle hooks, 29 specialized agents, and mechanical stop-prevention — all
tightly coupled to Claude Code's infrastructure.

OMH takes the best ideas from OMC and its community variants (Ouroboros,
Huntley, Agentic Kit, and others published on the LobeHub Skills Marketplace)
and rebuilds them for Hermes using only three primitives:

- **`delegate_task`** — Isolated subagents with role-specific context (fresh
  context per agent, no history leakage)
- **File-based state** — `.omh/` directory for persistence, handoffs, and
  resumability
- **Skills** — Markdown instructions the agent follows, in the
  `agentskills.io` open standard

The key architectural insight came during the ralph consensus process: instead
of fighting Hermes's lack of a stop-prevention hook, we lean into the
"one-task-per-invocation" pattern — each ralph call does one unit of work,
updates state, and exits. The caller re-invokes. This is actually more
faithful to Geoffrey Huntley's original ralph concept
(`while :; do cat PROMPT.md | claude-code; done`) than OMC's in-session loop.

## Key Adaptations

| OMC Pattern | OMH Adaptation | Why |
|---|---|---|
| `spawn_agent` with role prompts | `[omh-role:NAME]` marker in goal; `pre_llm_call` hook injects role prompt into subagent system prompt only | Parent context never loads role text — zero token overhead in the parent session |
| `persistent-mode.cjs` (mechanical stop prevention) | One-task-per-invocation + state files | Hermes has no stop hook; state-based resumability is more robust than prompt-based persistence |
| 6 concurrent child agents | 3 concurrent (Hermes `MAX_CONCURRENT_CHILDREN`) | Batch into groups of 3; Phase 4 validation fits exactly |
| Float ambiguity scores (0.0-1.0) with auto-exit gate | Coarse bins (HIGH/MEDIUM/LOW/CLEAR) with user-confirmed exit | LLM self-assessment lacks the precision to justify decimal thresholds |
| PRD user stories (`prd.json`) | Task items from ralplan consensus plans | Equivalent structure, different source |
| `.omc/` state directory | `.omh/` state directory | Same convention, different namespace |
| Haiku/Sonnet/Opus tier routing | Default model with per-subagent override | Hermes delegate_task supports model param but doesn't auto-route |
| Challenge modes (Contrarian/Simplifier/Ontologist) | Single adaptive instruction | Same effect, less ceremony |
| `AskUserQuestion` (clickable UI) | Conversational questions | Hermes is platform-agnostic (CLI, Telegram, etc.) |
| Deslop pass (mandatory in ralph) | Deferred to autopilot | Scope reduction for v1; documented as known gap |

## Deliberate Design Differences

These aren't gaps — they're choices made during consensus review:

| OMC Does | OMH Does | Why |
|----------|-----------|-----|
| Float ambiguity scores (0.0-1.0) with auto-exit | Coarse bins (HIGH/MEDIUM/LOW/CLEAR), user-confirmed exit | LLM self-assessment lacks decimal precision. The user is the authority on readiness. |
| In-session persistence loop | One-task-per-invocation + state files | Hermes can't prevent exit mechanically. State-based resume is more robust and eliminates context exhaustion. |
| Auto-detect brownfield | Ask the user | Checking for `package.json` etc. is unreliable and presumptuous. |
| 3 named challenge modes at fixed rounds | Single adaptive instruction | Same effect, less ceremony. Consensus review called the modes "cargo cult." |
| Full interview transcript in spec | Synthesized summary only | Keeps specs readable and focused. Full transcript is ephemeral. |

## Methodology: Self-Bootstrapping

OMH was built using its own tools. The first skill implemented was
`omh-ralplan` (consensus planning), which was then used to design the
remaining skills through multi-agent debate:

1. **omh-deep-interview** — Designed via ralplan consensus (2 rounds: Planner
   drafted, Critic challenged scoring-as-exit-gate and undefined spec
   contract, Planner revised, both approved)
2. **omh-ralph** — Designed via ralplan consensus with OMC source + LobeHub
   references fed to all subagents (2 rounds: both reviewers demanded cancel
   mechanism, context strategy, and verifier separation; Critic proposed
   one-task-per-invocation architecture; Planner adopted it; both approved)

Each consensus process produced a plan that was then reviewed against the
actual OMC source code and LobeHub marketplace implementations, ensuring OMH
preserves the patterns that matter while adapting to Hermes's architecture.

## Source Reference Material

| Document | Contents |
|----------|----------|
| [`docs/research/omc-ralph-reference.md`](research/omc-ralph-reference.md) | Extracted from actual OMC source: ralph, ultrawork, autopilot, persistent-mode.cjs, agent prompts, 12 design patterns |
| [`docs/research/lobehub-skills-reference.md`](research/lobehub-skills-reference.md) | 3 ralph variants, 2 deep-interview implementations, 2 autopilot implementations from the LobeHub marketplace |
