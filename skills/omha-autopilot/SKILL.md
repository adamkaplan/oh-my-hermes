---
name: omha-autopilot
description: >
  Full autonomous pipeline from idea to verified code. Composes deep-interview,
  ralplan, and ralph into 6 phases: Requirements → Planning → Execution → QA →
  Validation → Cleanup. One phase step per invocation — the caller re-invokes
  until complete. Detects existing artifacts to skip completed phases.
version: 1.0.0
tags: [autopilot, pipeline, autonomous, end-to-end, composition]
category: omha
metadata:
  hermes:
    requires_toolsets: [terminal]
---

# OMHA Autopilot — End-to-End Autonomous Pipeline

## When to Use

- End-to-end feature implementation from idea to verified, reviewed code
- The user says: "autopilot", "build me", "handle it all", "e2e this"
- You want the full pipeline: requirements → plan → implement → QA → validate

## When NOT to Use

- Single-file changes or trivial tasks (just do them)
- You want to stay in one continuous session (autopilot is multi-session by design)
- You only need planning (use omha-ralplan) or only need execution (use omha-ralph)

## Architecture: One Phase Step Per Invocation

Each autopilot invocation reads state, performs ONE unit of work, updates state, and
exits. The caller (user, cron, shell script) re-invokes until complete.

**Why?** Ralph was designed for fresh context per invocation. Running ralph's full
procedure 15 times in one session accumulates 80-180K tokens, exhausting context
before QA/Validation phases run. The multi-session design preserves fresh context
at every level.

**Why not delegate ralph as a subagent?** Hermes enforces MAX_DEPTH = 2 with no
recursive delegation. Autopilot at depth 1, ralph's executor/verifier at depth 2.
Delegating ralph as a subagent (depth 2) would push executor/verifier to depth 3 — blocked.

```
Invocation 1:   Phase 0 — requirements (or skip if spec exists)
Invocation 2:   Phase 1 — planning (or skip if plan exists)
Invocation 3:   Phase 2 — ralph iteration 1
Invocation 4:   Phase 2 — ralph iteration 2
...
Invocation N:   Phase 2 — ralph complete
Invocation N+1: Phase 3 — QA cycle 1                [FRESH SESSION]
...
Invocation M:   Phase 4 — validation round 1         [FRESH SESSION]
...
Final:          Phase 5 — cleanup → complete
```

See `references/caller-examples.md` for how to drive the loop.

## Procedure

### On Every Invocation: Dispatch

1. **Check for state**: Read `.omha/state/autopilot-state.json`
   - **Found**: Go to the handler for the current `phase`
   - **Not found**: Fresh start — go to Smart Detection below

2. **Check context_checkpoint**: If `true`, clear the flag, update state, and exit.
   The next invocation will be a fresh session. (In practice, since each invocation
   IS a fresh session when the caller loops, this flag confirms the phase boundary.)

3. **Check staleness**: If `last_updated_at` > 2 hours ago, warn:
   "Autopilot state is {N} hours old. Continue or fresh start?"

4. **Check pause**: If `pause_after_phase` matches the current phase and
   the phase just completed, set `phase: "paused"` and exit for user review.

5. **Dispatch** to the current phase handler.

### Smart Detection (Fresh Start)

When no autopilot-state.json exists, detect existing artifacts:

1. `.omha/specs/*-spec.md` with `status: confirmed` → create state at Phase 1, log "Skipping Phase 0: confirmed spec found"
2. `.omha/plans/ralplan-*.md` or `.omha/plans/consensus-*.md` → create state at Phase 2, log "Skipping Phases 0-1: consensus plan found"
3. `.omha/state/ralph-state.json` with `phase: "complete"` → create state at Phase 3, log "Skipping Phases 0-2: ralph execution complete"
4. Nothing found → create state at Phase 0

Also check: if `ralph-state.json` exists with `active: true` but no autopilot-state.json,
warn: "An active ralph session exists. Resume it under autopilot, or cancel and start fresh?"

Generate `session_id` (UUID), set `started_at`, create autopilot-state.json.

### Phase 0: Requirements

**Goal**: Ensure a confirmed spec exists.

1. Check for confirmed spec at `.omha/specs/*-spec.md` (YAML frontmatter `status: confirmed`)
2. If found: set `spec_file`, advance to Phase 1, exit
3. If not found, assess the user's input:
   - **Concrete** (contains file paths, function names, specific technologies, quantified requirements): Generate an inline spec at `.omha/specs/{slug}-spec.md` with `status: confirmed`. Advance to Phase 1, exit.
   - **Vague** (abstract goals, no technical anchors): Load `omha-deep-interview` and follow its procedure. **This phase is interactive** — the user must participate in the interview. When the interview produces a confirmed spec, advance to Phase 1, exit.

**Important**: For fully autonomous execution, run `omha-deep-interview` separately first. Autopilot will detect the confirmed spec and skip Phase 0 entirely.

Update state: `phase: "planning"`, `spec_file: "<path>"`. Exit.

### Phase 1: Planning

**Goal**: Ensure a consensus plan exists.

1. Check for existing plan at `.omha/plans/ralplan-*.md` or `.omha/plans/consensus-*.md`
2. If found: set `plan_file`, advance to Phase 2, exit
3. If not found: Load `omha-ralplan` and follow its procedure, using the spec from Phase 0 as the goal input

Update state: `phase: "execution"`, `plan_file: "<path>"`, `ralph_iteration: 0`, `context_checkpoint: true`. Exit.

The `context_checkpoint` ensures Phase 2 starts in a fresh session.

### Phase 2: Execution (Ralph Loop)

**Goal**: All tasks from the plan are implemented and individually verified.

Each invocation during Phase 2 performs **exactly ONE ralph iteration**:

1. Load `omha-ralph` skill
2. Follow ralph's procedure — it will:
   - Read ralph-state.json and ralph-tasks.json
   - On first invocation: parse the plan into ralph-tasks.json (planning gate)
   - Pick the next eligible task
   - Delegate to executor subagent
   - Gather evidence (run builds/tests)
   - Delegate to verifier subagent
   - Update ralph state
3. After ralph's procedure completes, read `.omha/state/ralph-state.json`:
   - `active: true`, `phase: "execute"` or `"verify"` → increment `ralph_iteration`, exit (caller re-invokes)
   - `phase: "complete"` → advance autopilot to Phase 3
   - `phase: "blocked"` → set autopilot `phase: "blocked"`, report blockers, exit

Update state: `ralph_iteration++`, truncate evidence to 2000 chars in `evidence_summary`. Exit.

On ralph completion: `phase: "qa"`, `qa_cycle: 0`, `context_checkpoint: true`. Exit.

### Phase 3: QA Cycling

**Goal**: The integrated system builds, passes all tests, and passes linting.

Each invocation performs **ONE QA cycle**. Phase 3 starts in a fresh session (context_checkpoint).

If `skip_qa: true` in state: advance to Phase 4, exit.

1. Run the project's build command. Capture output.
2. Run the project's test suite. Capture output.
3. Run linting/type-checking. Capture output.
4. If ALL pass: advance to Phase 4. Set `context_checkpoint: true`. Exit.
5. If failures:
   - Increment `qa_cycle`
   - Construct error fingerprint, check `qa_error_history` for 3-strike
   - If 3-strike: set `phase: "blocked"`, report the recurring issue, exit
   - If `qa_cycle > max_qa_cycles` (default 5): set `phase: "blocked"`, exit
   - Delegate diagnosis to architect subagent (read-only analysis of failures)
   - Delegate fix to executor subagent (with architect's diagnosis)
   - Update state. Exit. (Next invocation re-runs QA.)

Update state: `qa_cycle++`, `evidence_summary` (truncated). Exit.

### Phase 4: Multi-Reviewer Validation

**Goal**: Three independent reviewers approve the complete implementation.

Each invocation performs **ONE validation round**. Phase 4 starts in a fresh session.

If `skip_validation: true` in state: advance to Phase 5, exit.

1. Gather fresh evidence: run build + tests, capture output
2. Delegate 3 parallel reviews via `delegate_task` (batch mode, all 3 concurrent):

```
delegate_task(tasks=[
    {goal: "Architectural review of all changes", context: "{role-architect.md}\n\n{spec + plan + files changed + evidence}"},
    {goal: "Security review of all changes", context: "{role-security-reviewer.md}\n\n{spec + files changed + evidence}"},
    {goal: "Code quality review of all changes", context: "{role-code-reviewer.md}\n\n{files changed + evidence}"}
])
```

Load role prompts:
- Architect: `omha-ralplan/references/role-architect.md`
- Security: `omha-ralplan/references/role-security-reviewer.md`
- Code reviewer: `omha-autopilot/references/role-code-reviewer.md`

3. Parse verdicts. Record in `validation_verdicts`:
   ```json
   {"architect": "APPROVE", "security": "REQUEST_CHANGES: ...", "code_reviewer": "APPROVE"}
   ```
4. If ALL APPROVE: advance to Phase 5. Exit.
5. If any REQUEST_CHANGES:
   - Delegate fix to executor subagent with the rejection feedback
   - Increment `validation_round`
   - If `validation_round > max_validation_rounds` (default 3): set `phase: "blocked"`, exit
   - Exit. (Next invocation re-runs all 3 reviews.)

### Phase 5: Cleanup

**Goal**: Clean up state files, produce completion summary.

1. Set `phase: "complete"` (so if cleanup is interrupted, re-invocation retries)
2. Delete state files:
   - `autopilot-state.json`
   - `ralph-state.json`
   - `ralph-tasks.json`
   - `ralph-cancel.json` (if exists)
3. Preserve:
   - `.omha/logs/` (audit trail)
   - `.omha/plans/` (consensus plans)
   - `.omha/specs/` (confirmed specs)
   - `.omha/progress/ralph-progress.md` (execution log)
4. Report completion summary:
   - Original goal
   - Phases completed (with skips noted)
   - Total ralph iterations
   - QA cycles
   - Validation rounds
   - Key files changed

## State Management

See `references/state-schema.md` for full schema.

Key rules:
- Atomic writes (write to `.tmp`, then rename)
- Evidence truncation: build/test output capped at 2000 chars in state (keep the end). Full output in `.omha/logs/`.
- Phase boundaries set `context_checkpoint: true`
- Staleness warning at >2 hours since last update

## Sentinel Convention

Other skills/callers detect autopilot status by checking:
- `.omha/state/autopilot-state.json` exists → autopilot is in progress (check `phase` for details)
- `phase: "complete"` → autopilot finished successfully
- `phase: "blocked"` → autopilot needs intervention
- No state file + `.omha/logs/` exists → autopilot ran and completed (state was cleaned up)

## Pitfalls

- **Don't try to loop ralph in a single session.** Context exhaustion will kill the pipeline before QA/Validation run. Each invocation does ONE step.
- **Don't reimplement ralph.** Load the ralph skill and follow its procedure. Autopilot orchestrates, ralph executes.
- **Phase boundaries require fresh sessions.** Respect `context_checkpoint`. Don't try to squeeze Phase 3 into the same session as the last ralph iteration.
- **Don't skip QA.** Ralph verifies per-task. QA catches integration issues across tasks that per-task verification misses.
- **Phase 0 is interactive if no spec exists.** For cron/automated runs, pre-create a confirmed spec with `omha-deep-interview`.
- **Subagent limit: 3.** Phase 4 uses all 3 slots for parallel review. Don't try to add a 4th reviewer.
- **Evidence truncation: always cap.** Build/test output in state at 2000 chars max. Full output goes to logs.
- **Don't run multiple autopilot sessions.** One autopilot per project at a time. Check for existing state before creating new.
