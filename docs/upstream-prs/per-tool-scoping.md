# Upstream PR Candidate — Sub-Toolset Tool Scoping for `delegate_task`

**Status:** Not yet filed. Tracking note for OMH's needs against Hermes.
**Filed against:** `NousResearch/hermes-agent`
**Last updated:** 2026-04-22 (Forge ⚒️)

## Problem

`delegate_task`'s `toolsets=[...]` parameter restricts subagents at
**toolset granularity**, not tool granularity. The `file` toolset
bundles four tools that are not all of the same risk class:

```python
# hermes-agent/toolsets.py:147
"file": {"tools": ["read_file", "write_file", "patch", "search_files"]}
```

This means a parent that wants to dispatch a **read-only** worker
(verifier, auditor, code reviewer that should not edit) cannot do so
through the public schema. The closest available restriction
(`toolsets=["file"]`) hands the worker `write_file` and `patch`.

The upstream patterns guide
(`website/docs/guides/delegation-patterns.md`) labels `["file"]` as
"Read-only analysis, code review without execution" — that label is
misleading; it should say "file read AND write, no shell."

## Concrete OMH need

`omh-deep-research`'s research-verifier role
(`plugins/omh/references/role-research-verifier.md`) has a hard
contract:

> All inputs (the draft report + all findings blocks) are inlined into
> your context by the parent. **READ-ONLY: you have no filesystem or
> write tools.** You verify by inspection of context.

OMH currently enforces this by **prose only** because the substrate
provides no machine-enforceable equivalent. README "Known Gaps" A5
documents this. The verifier is the only OMH role with this need today,
but adding a code-review-only role or a security-audit-read-only role
would hit the same wall.

## Three upstream paths (ordered by surface-area cost)

### Option 1 — Add `tools=[...]` allowlist parameter to `delegate_task`

Smallest change. Add an optional `tools` parameter parallel to
`toolsets` that, when set, restricts the child to a specific tool name
allowlist (still intersected with parent + still subject to the
hard-blocked toolset list). Fall back to current behavior when omitted.

```python
delegate_task(
    goal="Verify citation integrity",
    context="<inlined report + findings>",
    tools=["read_file", "search_files"],  # NEW: tool-level allowlist
)
```

- **Pro:** No breaking changes, no toolset registry surgery, smallest diff.
- **Pro:** Useful beyond OMH (anyone wanting fine-grained restriction).
- **Con:** Adds a second axis of restriction (`toolsets` + `tools`); behavior of intersection between the two needs spec.
- **Effort estimate:** ~1 day. Code touches `tools/delegate_tool.py` schema + `_build_child_agent` toolset filter + tests.

### Option 2 — Split the `file` toolset into `file_read` + `file_write`

Restructures the toolset registry. `file_read` = `[read_file, search_files]`; `file_write` = `[write_file, patch]`. The `file` toolset is retained as an alias for `[file_read, file_write]` for backwards compatibility.

- **Pro:** Cleaner conceptual model — toolsets become risk-tier groupings, not capability bags.
- **Pro:** Generalizes — other toolsets (`terminal` arguably has the same problem: shell-exec is far higher risk than process management) could follow the same pattern.
- **Con:** Touches every toolset consumer in the codebase. Larger diff, larger review burden.
- **Con:** Default-toolset semantics get fiddly (does `["file"]` still resolve at runtime to both halves?).
- **Effort estimate:** 3-5 days including migration.

### Option 3 — Accept prose-only enforcement, document permanently

Make A5 a known and accepted property of OMH rather than a gap. Update README A5 to say "this contract is enforced by prose only by design — Hermes does not provide sub-toolset tool scoping at the public API." Move on.

- **Pro:** Zero engineering cost.
- **Con:** Verifier remains a *trust* boundary, not an *enforced* one. A misaligned model could in principle write to disk and corrupt the report-under-review before producing a verdict.
- **Con:** Future read-only roles inherit the same trust-not-enforce posture.

## Recommendation

**Option 1.** Smallest upstream surface area, broadest applicability beyond OMH, and the conceptual question Option 2 raises (should `terminal` also split?) probably wants its own RFC rather than being bundled into a one-skill-need PR.

## Pre-filing checklist

Before opening the PR upstream, OMH should:

1. ~~Verify the granularity claim is current~~ — confirmed against `toolsets.py:147` on 2026-04-22.
2. Run a validation spike: confirm a stub `tools=["read_file"]` child cannot actually invoke `write_file` even when the model tries (the dispatcher has to honor the allowlist, not just the schema).
3. Sketch the test cases: parent passes `tools=["read_file"]`; child attempts `write_file`; expect tool-not-available error in child's loop, not silent success.
4. Confirm the `toolsets` + `tools` intersection semantics with upstream maintainers before writing the PR (avoids burning the diff on a contested API choice).
5. Search upstream issues/PRs first — this may already be tracked.

## Cross-references

- [`docs/research/hermes-multiagent.md`](../research/hermes-multiagent.md) §4 — corrected toolset granularity finding
- [`README.md`](../../README.md) Known Gaps A5
- [`plugins/omh/references/role-research-verifier.md`](../../plugins/omh/references/role-research-verifier.md) — the contract this would let us enforce
- [`plugins/omh/skills/omh-deep-research/SKILL.md`](../../plugins/omh/skills/omh-deep-research/SKILL.md) Phase 5 step 3 — current dispatch site
