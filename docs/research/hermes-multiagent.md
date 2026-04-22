# Hermes Native Multi-Agent Capabilities — Research Summary

**Sources:**
- `~/src/ext/hermes-agent/website/docs/user-guide/features/delegation.md` (240 lines, full reference)
- `~/src/ext/hermes-agent/website/docs/guides/delegation-patterns.md` (239 lines, patterns guide)
- Cross-checked against `~/src/ext/hermes-agent/tools/delegate_tool.py` (1672 lines) for what the docs actually map to in code.

**Audience:** OMH maintainers. The question this doc exists to answer is *"what is Hermes already giving us natively that OMH should lean on instead of route around?"* — so each capability ends with an **OMH implication** line.

---

## 1. The `delegate_task` tool — single + batch

`delegate_task` spawns child `AIAgent` instances with isolated context, restricted toolsets, and their own terminal sessions. **Only the final summary** enters the parent's context — intermediate tool calls never come back.

Two invocation modes, gated mutually exclusive:

```python
# Single task
delegate_task(goal=..., context=..., toolsets=[...], max_iterations=50, role="leaf")

# Batch (parallel)
delegate_task(tasks=[
    {"goal": ..., "context": ..., "toolsets": [...], "role": ...},
    ...
])
```

Batch mode runs through a `ThreadPoolExecutor`, results are sorted back to input order regardless of completion order, and **interrupting the parent interrupts all active children** (and grandchildren under orchestrators).

> **OMH implication:** Ralplan's three-perspective debate (Planner / Architect / Critic) is a textbook batch-of-3 use case — and OMH already does this. Worth confirming we're not paying the per-call thread-pool overhead by serializing. Where ralph fans out independent tasks, ensure we're truly batching, not looping `delegate_task` calls.

---

## 2. Concurrency cap is **configurable, not 3**

The widely-cited "3 concurrent subagents" is the **default**, not a ceiling.

- `delegation.max_concurrent_children` (config.yaml) or `DELEGATION_MAX_CONCURRENT_CHILDREN` (env): floor of 1, **no hard upper cap**.
- Batches larger than the configured limit return a `tool_error` at dispatch — they are *not* silently truncated.

> **OMH implication:** `docs/hermes-constraints.md` currently lists "3 concurrent subagents" as a fixed constraint. **That's stale.** OMH validation phases that wanted 4-6 parallel reviewers (security + architect + code-review + tests + docs) can be unlocked by raising `max_concurrent_children` either globally or via per-project config — no plugin work, no spawning workaround. Fix the doc and consider making OMH's autopilot Phase 4 honor a higher fan-out when configured.

---

## 3. Nested orchestration via `role="orchestrator"`

By default delegation is **flat**: parent (depth 0) → leaves (depth 1), and leaves cannot delegate further. But Hermes supports nested orchestration:

- `role="leaf"` (default): child cannot call `delegate_task`. Identical to flat-delegation behavior.
- `role="orchestrator"`: child **retains the `delegation` toolset** so it can spawn its own workers.
- Gated by `delegation.max_spawn_depth` (default **1** = flat, `role="orchestrator"` is a no-op at defaults). Raise to 2 for two levels, 3 for three (cap).
- `delegation.orchestrator_enabled: false` is a global kill-switch that forces every child back to leaf regardless of the `role` parameter.

**Cost warning quoted from the upstream docs:** `max_spawn_depth: 3` × `max_concurrent_children: 3` = 27 concurrent leaf agents. Each level multiplies spend.

> **OMH implication:** This is the **single biggest stale assumption** in OMH. `docs/hermes-constraints.md` says "No recursive delegation. All orchestration at top level; subagents are leaf workers." That was true at OMH's design time; it is no longer true. Concrete unlocks:
> - **Ralplan** could spawn an orchestrator-Planner that runs its own three-way sub-debate on a contested section (currently Planner is a single leaf doing it all in-context).
> - **Autopilot** could spawn an orchestrator per phase, letting each phase manage its own sub-fanout — instead of the top-level autopilot agent juggling all six phases plus all leaves.
> - **Deep-research** could spawn an orchestrator-synthesist that delegates citation-verification per-claim to leaf verifiers, with the verifier results never polluting the synthesist's context.
>
> Adoption recommendation: **opt-in, off-by-default**. Document `max_spawn_depth: 2` as the supported OMH configuration, keep the defaults flat, and gate any nested-orchestrator code paths on a config check so OMH still works on stock Hermes.

---

## 4. Toolset restriction is real, but granularity is **toolset**, not tool

> **Correction (2026-04-22, day-of):** An earlier draft of this section
> claimed `toolsets=["file"]` gave a "read-only" worker. That was wrong —
> the `file` toolset includes `write_file` and `patch` alongside
> `read_file` and `search_files`. The upstream patterns guide's "Read-only
> analysis" label for `["file"]` is misleading. Spot-checked the actual
> toolset definition (`hermes-agent/toolsets.py:147`) and found:
>
> ```python
> "file": {"tools": ["read_file", "write_file", "patch", "search_files"]}
> ```
>
> The corrected story is below; see also the **OMH implication** at the
> end for what this means for A5.

Per-call `toolsets=[...]` selects from the parent's enabled toolsets
(intersected — children can never gain a toolset the parent lacks).
Granularity is **whole toolsets**, not individual tools. There is no
public way to say "give the child `read_file` and `search_files` but not
`write_file`."

Subagents **never** get the following toolsets, regardless of what the
caller passes:

- `delegation` — blocked for leaves, retained only for orchestrators
- `clarify` — subagents cannot interact with the user
- `memory` — no writes to shared persistent memory
- `code_execution` (`execute_code`) — children must reason step-by-step
- `send_message` — no cross-platform side effects (no firing Telegram messages from a subagent)

Empty list (`toolsets=[]`) is treated as falsy by the dispatcher and
falls through to inheriting the parent's enabled toolsets — it does
**not** mean "no tools." There is no built-in "no-tools" or "read-only"
toolset.

The toolset patterns the upstream docs publish, with corrected labels:

| Toolset Pattern | What the child actually has |
|---|---|
| `["terminal", "file"]` | Shell + file read/write/patch/search — full code work |
| `["web"]` | `web_search` + `web_extract` only — research |
| `["terminal", "file", "web"]` | Full-stack |
| `["file"]` | File **read AND write** + search (NOT read-only) |
| `["terminal"]` | Shell + process management |

> **OMH implication:** This is exactly the granularity gap behind README
> A5 (the omh-deep-research verifier whose contract is *"you have NO
> filesystem or write tools — everything is inlined"*). Stock Hermes
> cannot enforce that contract: the closest available restriction
> (`toolsets=["file"]`) actively violates it by handing the verifier
> `write_file` and `patch`. **A5 is a real, persistent gap** — keep the
> prose-only enforcement and keep the README note. Three upstream paths
> would close it; tracked in
> [`upstream-prs/per-tool-scoping.md`](upstream-prs/per-tool-scoping.md).
>
> Where per-call scoping IS useful at OMH's current granularity:
> researcher leaves narrowed to `["web"]`, executor leaves narrowed to
> `["terminal", "file"]`, etc. We already do this. The only role that
> wants finer granularity than Hermes provides is the verifier.

---

## 5. Per-subagent model + provider override

`delegation` config block can route subagents to a different model/provider entirely:

```yaml
delegation:
  model: "google/gemini-flash-2.0"
  provider: "openrouter"
  # OR a custom endpoint:
  # base_url: "http://localhost:1234/v1"
  # api_key: "local-key"
```

Falls back to parent model when omitted. Subagents **inherit the parent's credential pool**, so key rotation on rate-limits works for children too.

> **OMH implication:** Direct path to the gap listed in `docs/gaps.md` ("Model tier routing — Auto-routes Haiku/Sonnet/Opus by task complexity. We use one model for all"). OMH doesn't need to build its own router — point users at `delegation.model` for cheap-leaf workloads (verifier, deslop, mechanical refactor leaves) and document the recommended config. Note: the override is global per Hermes install, not per-task in the current API. Per-task model routing inside one batch is not supported by the public schema (only per-task `acp_command` / `acp_args` are).

---

## 6. ACP transport — spawn Claude Code, Codex, etc. as workers

This is the multi-agent capability that's least visible from the OMH docs but most relevant to the "multi-model orchestration" gap.

`delegate_task` accepts an `acp_command` (and `acp_args`) parameter, top-level or per-task. When set, the child uses **ACP subprocess transport** instead of inheriting the parent's transport. Examples from the schema:

- `acp_command="claude"`, `acp_args=["--acp", "--stdio", "--model", "claude-opus-4-6"]` — spawn Claude Code as a worker
- `acp_command="copilot"` — spawn GitHub Copilot
- Any ACP-capable agent

> **OMH implication:** `docs/gaps.md` lists "Multi-model orchestration: Claude + Codex + Gemini workers via tmux" as Low priority and "niche; ACP transport partially addresses." It doesn't *partially* address it — it natively addresses it. A ralplan debate where Planner = Claude Code, Architect = Codex, Critic = Hermes-native, all dispatched via one `delegate_task(tasks=[...])` call with per-task `acp_command`, is a few-line config change. Worth a follow-up skill (`omh-cross-model-debate`) once we've validated stability. Also worth an entry in OMH's docs explicitly listing this as supported, so users don't reach for tmux when they don't need it.

---

## 7. Subagent isolation properties (the hard guarantees)

These are the contract OMH builds against. Worth copying verbatim into our docs because the wording matters:

- **Each subagent gets its own terminal session** (separate working directory and state from the parent).
- **No conversation history.** Subagents see only the `goal` + `context` the parent passes. They have *zero knowledge* of the parent's prior tool calls or messages. The upstream docs underscore this with "BAD" / "GOOD" examples — `goal="Fix the error"` is a bug; the parent must inline the file paths, error text, project structure, and constraints.
- **Default `max_iterations: 50`** per child (configurable per-call). Lower for simple tasks to bound cost.
- **Interrupt propagation** — a parent interrupt cancels all active children and grandchildren.
- **Inherited credentials** — API key, provider, credential pool flow through.
- **Final summary only** — the focused system prompt instructs the child to return what it did, what it found, files modified, and issues encountered.

> **OMH implication:** `omh_delegate`'s subagent-persists-via-write-file pattern exists *because* the final-summary-only contract loses everything if the parent's tool dispatch hiccups (FM1: 14.8 minutes of subagent reasoning gone). Our wrapper is the right shape for that hazard. Worth noting in our own `omh-delegate.md` that this is a **mitigation for an architectural property of `delegate_task`**, not a bug to be fixed upstream — the property is intentional (context efficiency).

---

## 8. `delegate_task` vs `execute_code` — when each wins

The upstream docs publish this comparison and it's load-bearing for OMH skill design:

| Factor | `delegate_task` | `execute_code` |
|---|---|---|
| Reasoning | Full LLM loop | Just Python execution |
| Context | Fresh isolated conversation | No conversation, just script |
| Tool access | All non-blocked tools, with reasoning | 7 tools via RPC, no reasoning |
| Parallelism | 3 concurrent children by default (configurable) | Single script |
| Best for | Complex tasks needing judgment | Mechanical multi-step pipelines |
| Token cost | Higher (full LLM loop) | Lower (only stdout returned) |
| User interaction | None | None |

The upstream pattern guide also documents a **gather-then-analyze** composition: use `execute_code` for cheap mechanical fan-out (e.g. 15 web_search calls + web_extract over the top hits), persist to disk, then a single `delegate_task` does the reasoning over the prepared bundle.

> **OMH implication:** This is exactly the shape `omh-deep-research` should be optimized toward — researcher leaves currently each do their own search→extract→summarize loop in full LLM context. For factual gather phases where we know the queries up front, the cheaper pattern is one `execute_code` doing N searches + extracts to a JSON bundle, then one synthesist subagent reasoning over the bundle. Worth a measured comparison of cost on a real query.

---

## 9. Capabilities adjacent to delegation OMH might not be using

These don't appear in `delegation.md` but show up in the broader Hermes multi-agent surface and are worth knowing:

- **Spawning full `hermes` subprocesses** (via `terminal(command="hermes chat -q ...")` or tmux) — fully independent processes, hours/days of runtime, full tool access, can be interactive. Heavier than `delegate_task` but not bounded by the parent's loop. Useful for autopilot-style autonomous missions where the parent shouldn't be blocked.
- **Profiles** (`hermes profile create/use`) — isolated config, sessions, skills, memory per profile. Different OMH workflows could run under different profiles to keep skill sets and memory clean.
- **Worktree mode** (`hermes -w` or `--worktree`) — isolated git worktree per agent. Critical when spawning multiple code-editing agents on the same repo.
- **Cron + webhooks** — `cronjob` tool and webhook subscriptions for event-driven multi-stage pipelines. An autopilot phase that wants to "wait for CI and then continue" could trigger a webhook back into a follow-up cron job rather than blocking.
- **MOA (Mixture of Agents)** — off-by-default toolset, separate from `delegate_task`. Different mechanism (multiple models on one query, then aggregation). Not currently relevant to OMH but worth knowing it exists.

> **OMH implication:** Mostly future-work material. The most interesting near-term lever is `hermes -w` for ralph's parallel-fanout phase — independent tasks that touch overlapping files would each get their own worktree, eliminating the "two leaves edit the same file" footgun the upstream patterns guide flags.

---

## 10. Summary — what to update in OMH

Consolidated action list, ordered by leverage:

1. **`docs/hermes-constraints.md` is partially stale.** Update the "3 concurrent subagents" row (it's a configurable default, no hard cap) and the "No recursive delegation" row (orchestrators exist; gated on `max_spawn_depth >= 2`). Re-frame both as *defaults OMH targets for portability* rather than *hard limits*. **(DONE 2026-04-22)**
2. **`docs/gaps.md` "Multi-model orchestration"** — re-classify from "niche; partially addresses" to "natively supported via `acp_command`; needs an OMH skill to expose." **(DONE 2026-04-22; gated on validation spike)**
3. **`docs/gaps.md` "Model tier routing"** — re-classify from "Routing logic in autopilot" to "Native via `delegation.model` config; document recommended OMH config presets." **(DONE 2026-04-22)**
4. **README "Known Gaps" A5** (per-call tool scoping for verifier) — ~~remove~~ **KEEP**. *Correction:* `toolsets=["file"]` is not read-only (it includes `write_file` + `patch`). Hermes does not currently support sub-toolset tool scoping. A5 is a real, persistent gap. Upstream paths to close it tracked in [`upstream-prs/per-tool-scoping.md`](upstream-prs/per-tool-scoping.md).
5. **Consider new skill: `omh-nested-orchestration`** (or fold into autopilot v2) — patterns for `role="orchestrator"` use under `max_spawn_depth: 2`, with cost warnings prominent. *Validation spike required first.*
6. **Consider new skill: `omh-cross-model-debate`** — ralplan variant that dispatches Planner/Architect/Critic to different model providers via per-task `acp_command`. *Validation spike required first.*
7. **`docs/omh-delegate.md`** — add a paragraph framing the wrapper as a mitigation for the *intentional* final-summary-only contract of `delegate_task`, not a workaround for a bug. **(DONE 2026-04-22)**

⚒️ Forge — 2026-04-22, ~/src/witt3rd/oh-my-hermes/docs/research/hermes-multiagent.md
*Updated same-day with §4 correction after the toolset definition was actually inspected, not just docstring-spot-checked.*
