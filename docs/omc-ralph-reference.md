# OMC Ralph & Related Skills — Comprehensive Reference

> Extracted from oh-my-claudecode source files for informing Hermes-native equivalents.
> Generated: 2026-04-07

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Ralph Skill — Full Detail](#ralph-skill)
3. [Ultrawork Skill — Parallel Execution Engine](#ultrawork-skill)
4. [Autopilot Skill — Full Lifecycle](#autopilot-skill)
5. [UltraQA Skill — QA Cycling](#ultraqa-skill)
6. [Verify Skill — Evidence-Based Completion](#verify-skill)
7. [Persistent-Mode Hook — Stop Prevention](#persistent-mode-hook)
8. [Agent Prompts — Executor, Architect, Verifier](#agent-prompts)
9. [State Management — Files, Fields, Lifecycle](#state-management)
10. [Design Patterns Summary](#design-patterns-summary)

---

## 1. Architecture Overview <a name="architecture-overview"></a>

OMC uses a layered composition model:

```
autopilot (full lifecycle: idea → working code)
 └── ralph (persistence + verification wrapper)
      └── ultrawork (parallel execution engine)
           └── executor agents (actual code changes)
```

Key insight: **ultrawork** provides parallelism only. **ralph** adds persistence, PRD tracking, verification loops, and state management on top. **autopilot** adds requirement expansion, planning, QA cycling, and multi-perspective validation on top of ralph.

### Skill Levels
- Level 2: executor (agent)
- Level 3: architect, verifier, ultraqa (agents/skills)
- Level 4: ralph, ultrawork, autopilot (orchestration skills)

---

## 2. Ralph Skill — Full Detail <a name="ralph-skill"></a>

### Frontmatter
```yaml
name: ralph
description: Self-referential loop until task completion with configurable verification reviewer
argument-hint: "[--no-prd] [--no-deslop] [--critic=architect|critic|codex] <task description>"
level: 4
```

### Purpose
PRD-driven persistence loop that keeps working until ALL user stories in `prd.json` have `passes: true` and are reviewer-verified.

### Core Concept
Ralph wraps ultrawork's parallel execution with:
- Session persistence
- Automatic retry on failure
- Structured story tracking (prd.json)
- Mandatory verification before completion

### CLI Flags
| Flag | Effect |
|------|--------|
| `--no-prd` | Skip PRD generation, legacy mode (no story tracking, generic verification) |
| `--no-deslop` | Skip mandatory post-review ai-slop-cleaner pass |
| `--critic=architect` | (default) Use architect agent for completion review |
| `--critic=critic` | Use critic agent for completion review |
| `--critic=codex` | Use external Codex via `omc ask codex --agent-prompt critic` |

### Template Variables
- `{{ITERATION}}` — current iteration number
- `{{MAX}}` — max iterations
- `{{PROMPT}}` — original user task text

### Execution Steps (9 steps)

#### Step 1: PRD Setup (first iteration only)
1. Check if `prd.json` exists (project root or `.omc/`)
2. If exists, read it and proceed
3. If not, read auto-generated scaffold at `.omc/prd.json`
4. **CRITICAL: Refine the scaffold** — replace generic acceptance criteria with task-specific ones
   - Generic bad: `"Implementation is complete"`, `"Code compiles without errors"`
   - Specific good: `"detectNoPrdFlag('ralph --no-prd fix') returns true"`, `"TypeScript compiles with no errors (npm run build)"`
5. Order stories by priority (foundational first, dependent later)
6. Write refined `prd.json` back to disk
7. Initialize `progress.txt` if it doesn't exist

#### Step 2: Pick Next Story
- Read `prd.json`, select highest-priority story with `passes: false`

#### Step 3: Implement Current Story
- Delegate to specialist agents at appropriate tiers:
  - LOW tier (Haiku): simple lookups
  - MEDIUM tier (Sonnet): standard work
  - HIGH tier (Opus): complex analysis
- If sub-tasks discovered during implementation, add as new stories to `prd.json`
- Long operations use `run_in_background: true`

#### Step 4: Verify Current Story's Acceptance Criteria
- For EACH acceptance criterion, verify with fresh evidence
- Run relevant checks (test, build, lint, typecheck)
- Read actual output
- If any criterion NOT met → continue working, do NOT mark complete

#### Step 5: Mark Story Complete
- Set `passes: true` for story in `prd.json`
- Record in `progress.txt`: what was implemented, files changed, learnings

#### Step 6: Check PRD Completion
- Read `prd.json` — are ALL stories `passes: true`?
- If NOT all complete → loop to Step 2
- If ALL complete → proceed to Step 7

#### Step 7: Reviewer Verification (tiered)
Review tier selection:
- <5 files, <100 lines with full tests → STANDARD tier minimum (Sonnet)
- Standard changes → STANDARD tier (Sonnet)
- >20 files or security/architectural → THOROUGH tier (Opus)
- Ralph floor: always at least STANDARD, even for small changes

Reviewer verifies against SPECIFIC acceptance criteria from prd.json, not vague "is it done?"

For `--critic=codex`, the prompt MUST include:
1. Full list of acceptance criteria from prd.json
2. Directive to evaluate OPTIMALITY (not just correctness)
3. Directive to review ALL related code (callers, callees, shared types, adjacent modules)
4. List of files changed during ralph session

#### Step 7.5: Mandatory Deslop Pass
- Unless `--no-deslop`, run `oh-my-claudecode:ai-slop-cleaner` in standard mode
- Scope: only files changed during current Ralph session
- If deslop introduces follow-up edits, keep within changed-file scope

#### Step 7.6: Regression Re-verification
- After deslop pass, re-run ALL relevant tests, build, lint checks
- Read output and confirm post-deslop regression passes
- If regression fails → roll back cleaner changes or fix, then rerun until passes
- Only proceed after post-deslop regression passes (or `--no-deslop` specified)

#### Step 8: On Approval
- After Step 7.6 passes, run `/oh-my-claudecode:cancel` to cleanly exit and clean up state

#### Step 9: On Rejection
- Fix issues raised, re-verify with same reviewer, loop back

### Escalation & Stop Conditions
- Stop on fundamental blockers requiring user input (missing credentials, unclear requirements)
- Stop on user "stop", "cancel", "abort" → run `/oh-my-claudecode:cancel`
- Continue when hook sends "The boulder never stops" (iteration continues)
- On reviewer rejection → fix and re-verify (do NOT stop)
- Same issue 3+ iterations → report as potential fundamental problem

### Final Checklist (12 items)
```
- [ ] All prd.json stories have passes: true
- [ ] prd.json acceptance criteria are task-specific (not generic boilerplate)
- [ ] All requirements from original task met (no scope reduction)
- [ ] Zero pending or in_progress TODO items
- [ ] Fresh test run output shows all tests pass
- [ ] Fresh build output shows success
- [ ] lsp_diagnostics shows 0 errors on affected files
- [ ] progress.txt records implementation details and learnings
- [ ] Selected reviewer verification passed against specific acceptance criteria
- [ ] ai-slop-cleaner pass completed on changed files (or --no-deslop)
- [ ] Post-deslop regression tests pass
- [ ] /oh-my-claudecode:cancel run for clean state cleanup
```

### Execution Policy
- Fire independent agent calls simultaneously — never wait sequentially
- Use `run_in_background: true` for long operations
- Always pass `model` parameter explicitly when delegating
- Read `docs/shared/agent-tiers.md` before first delegation
- Deliver FULL implementation: no scope reduction, no partial completion, no deleting tests

---

## 3. Ultrawork Skill — Parallel Execution Engine <a name="ultrawork-skill"></a>

### Frontmatter
```yaml
name: ultrawork
description: Parallel execution engine for high-throughput task completion
argument-hint: "<task description with parallel work items>"
level: 4
```

### Purpose
Component (not standalone mode) that provides parallelism and smart model routing. Does NOT provide persistence, verification loops, or state management.

### Steps
1. Read agent reference for tier selection
2. Classify tasks by independence (parallel vs dependent)
3. Route to correct tiers: LOW/Haiku, MEDIUM/Sonnet, HIGH/Opus
4. Fire independent tasks simultaneously
5. Run dependent tasks sequentially (wait for prerequisites)
6. Background long operations (`run_in_background: true`)
7. Lightweight verification: build/typecheck passes, tests pass, no new errors

### Key Distinction from Ralph
- Ultrawork: parallelism only, lightweight verification
- Ralph: ultrawork + persistence + PRD tracking + comprehensive verification + state management

---

## 4. Autopilot Skill — Full Lifecycle <a name="autopilot-skill"></a>

### Frontmatter
```yaml
name: autopilot
description: Full autonomous execution from idea to working code
argument-hint: "<product idea or task description>"
level: 4
```

### 6 Phases

#### Phase 0 — Expansion
- If ralplan consensus plan exists (`.omc/plans/ralplan-*.md` or `.omc/plans/consensus-*.md`): Skip Phase 0 AND Phase 1 → jump to Phase 2
- If deep-interview spec exists (`.omc/specs/deep-interview-*.md`): Skip analyst+architect expansion, use spec directly
- If input is vague: Offer redirect to `/deep-interview`
- Otherwise: Analyst (Opus) + Architect (Opus) → `.omc/autopilot/spec.md`

#### Phase 1 — Planning
- If ralplan consensus plan exists: Skip
- Architect (Opus) creates plan → Critic (Opus) validates
- Output: `.omc/plans/autopilot-impl.md`

#### Phase 2 — Execution
- Uses Ralph + Ultrawork
- Executor at Haiku/Sonnet/Opus tiers, parallel independent tasks

#### Phase 3 — QA (UltraQA mode)
- Build, lint, test, fix failures
- Max 5 cycles
- Same error 3x → stop (fundamental issue)

#### Phase 4 — Validation (parallel)
- Architect: functional completeness
- Security-reviewer: vulnerability check
- Code-reviewer: quality review
- All must approve; fix and re-validate on rejection

#### Phase 5 — Cleanup
- Delete state files: `.omc/state/autopilot-state.json`, `ralph-state.json`, `ultrawork-state.json`, `ultraqa-state.json`
- Run `/oh-my-claudecode:cancel`

### Configuration
```json
{
  "omc": {
    "autopilot": {
      "maxIterations": 10,
      "maxQaCycles": 5,
      "maxValidationRounds": 3,
      "pauseAfterExpansion": false,
      "pauseAfterPlanning": false,
      "skipQa": false,
      "skipValidation": false
    }
  }
}
```

### 3-Stage Pipeline
```
/deep-interview → spec (ambiguity ≤ 20%)
  → /ralplan --direct → consensus plan (Planner/Architect/Critic approved)
    → /autopilot → skips Phase 0+1, starts at Phase 2
```

---

## 5. UltraQA Skill — QA Cycling <a name="ultraqa-skill"></a>

### Frontmatter
```yaml
name: ultraqa
description: QA cycling workflow - test, verify, fix, repeat until goal met
argument-hint: "[--tests|--build|--lint|--typecheck|--custom <pattern>] [--interactive]"
level: 3
```

### Cycle Workflow (Max 5 cycles)
1. **RUN QA**: Execute verification based on goal type
2. **CHECK RESULT**: Pass → exit, Fail → continue
3. **ARCHITECT DIAGNOSIS**: Spawn architect (Opus) to analyze failure root cause
4. **FIX ISSUES**: Spawn executor (Sonnet) to apply architect's fix
5. **REPEAT**: Back to step 1

### Exit Conditions
| Condition | Action |
|-----------|--------|
| Goal Met | "ULTRAQA COMPLETE: Goal met after N cycles" |
| Cycle 5 Reached | "ULTRAQA STOPPED: Max cycles. Diagnosis: ..." |
| Same Failure 3x | "ULTRAQA STOPPED: Same failure detected 3 times. Root cause: ..." |
| Environment Error | "ULTRAQA ERROR: [tmux/port/dependency issue]" |

### State File: `.omc/ultraqa-state.json`
```json
{
  "active": true,
  "goal_type": "tests",
  "goal_pattern": null,
  "cycle": 1,
  "max_cycles": 5,
  "failures": ["3 tests failing: auth.test.ts"],
  "started_at": "2024-01-18T12:00:00Z",
  "session_id": "uuid"
}
```

### State Cleanup
On completion: **DELETE** state file (`rm -f .omc/state/ultraqa-state.json`), do NOT just set `active: false`.

---

## 6. Verify Skill — Evidence-Based Completion <a name="verify-skill"></a>

Simple skill (no complex state). Verification order:
1. Existing tests
2. Typecheck / build
3. Narrow direct command checks
4. Manual or interactive validation

Rules: No "complete" without evidence. If check fails, include failure clearly. If no verification path exists, say so explicitly.

---

## 7. Persistent-Mode Hook — Stop Prevention <a name="persistent-mode-hook"></a>

### File: `scripts/persistent-mode.cjs`

This is the core persistence mechanism. It's a Node.js script that runs as a Claude Code stop hook — intercepts when Claude tries to stop and decides whether to block or allow.

### Input
Reads JSON from stdin with fields:
- `cwd` / `directory` — project directory
- `session_id` / `sessionId` — session identifier
- `stop_reason` / `stopReason` — why Claude stopped
- `end_turn_reason` / `endTurnReason`
- `user_requested` / `userRequested`
- `transcript_path` / `transcriptPath`

### Output
JSON to stdout:
- `{ "continue": true, "suppressOutput": true }` — allow stop silently
- `{ "decision": "block", "reason": "..." }` — prevent stop with message

### Priority Order (9 priorities)

Before checking modes, the hook has critical bypass conditions:

#### Bypass Conditions (always allow stop)
1. **Context limit stop** — patterns: `context_limit`, `context_window`, `context_exceeded`, `context_full`, `max_context`, `token_limit`, `max_tokens`, `conversation_too_long`, `input_too_long`
2. **Context near-full** — estimated context usage ≥ 95% (reads last 4KB of transcript file, parses `context_window` and `input_tokens` fields)
3. **User abort** — `user_requested`/`userRequested` true, or stop_reason matches: `aborted`, `abort`, `cancel`, `interrupt`, `user_cancel`, `user_interrupt`, `ctrl_c`, `manual_stop`
4. **Authentication error** — patterns: `authentication_error`, `unauthorized`, `401`, `403`, `forbidden`, `token_expired`, etc.
5. **Cancel signal active** — checks `cancel-signal-state.json` (session-scoped path first, then legacy), 30-second TTL

#### Priority 1: Ralph Loop
```javascript
if (ralph.state?.active && !isAwaitingConfirmation(ralph.state) && !isStaleState(ralph.state) && isSessionMatch(ralph.state, sessionId))
```
- Increments `ralph.state.iteration`
- If `iteration < max_iterations`: blocks with message including iteration count and task prompt
- If `iteration >= max_iterations`: **EXTENDS** max by 10 and continues (never silently stops)
- Block message: `[RALPH LOOP - ITERATION N/M] Work is NOT done. Continue working.`

#### Priority 2: Autopilot
- Checks `autopilot.state?.active`, not awaiting confirmation, not stale, session match
- If phase !== "complete": increments `reinforcement_count`, blocks up to 20 reinforcements
- Block message: `[AUTOPILOT - Phase: X] Autopilot not complete. Continue working.`

#### Priority 2.5: Team Pipeline (first-class enforcement)
- Circuit breaker: max 20 stops, 5-minute TTL
- Checks phase against `TEAM_ACTIVE_PHASES` set
- Terminal phases: `completed`, `complete`, `failed`, `cancelled`, `canceled`, `aborted`, `terminated`, `done`
- Active phases: `team-plan`, `team-prd`, `team-exec`, `team-verify`, `team-fix`, `planning`, `executing`, `verify`, `verification`, `fix`, `fixing`

#### Priority 2.6: Ralplan
- Circuit breaker: max 30 stops, 45-minute TTL
- Terminal phases: `complete`, `completed`, `failed`, `cancelled`, `canceled`, `done`

#### Priority 3: Ultrapilot
- Checks workers array, counts incomplete (status !== "complete" and !== "failed")
- Max 20 reinforcements

#### Priority 4: Swarm
- Uses `swarm-active.marker` file + `swarm-summary.json`
- Counts `tasks_pending + tasks_claimed`
- Max 15 reinforcements

#### Priority 5: Pipeline
- Tracks `current_stage` vs `stages.length`
- Max 15 reinforcements

#### Priority 6: Team (fallback)
- Only if not handled by Priority 2.5
- Max 20 reinforcements

#### Priority 6.5: OMC Teams (tmux workers)
- Independent of native team state
- Max 20 reinforcements

#### Priority 7: UltraQA
- Checks `cycle < max_cycles` AND `!all_passing`
- Increments cycle count
- Block message: `[ULTRAQA - Cycle N/M] Tests not all passing. Continue fixing.`

#### Priority 8: Ultrawork
- Always continues while `active` (not just when tasks exist)
- Increments `reinforcement_count`, max `max_reinforcements` (default 50)
- After max reached: deactivates state (`active = false`, `deactivated_reason = 'max_reinforcements_reached'`)
- Progressive messaging:
  - reinforcement < 3: "Continue working"
  - reinforcement >= 3: suggest cancel if work complete
  - reinforcement >= 5: STRONG directive to call cancel NOW

#### Priority 9: Skill Active State
- Generic skill persistence via `skill-active-state.json`
- Per-skill TTL (default 5 minutes)
- Max reinforcements (default 3)
- Checks active subagent count — if subagents running, silently allows stop

### Key State Management Patterns

#### Staleness Detection
```javascript
const STALE_STATE_THRESHOLD_MS = 2 * 60 * 60 * 1000; // 2 hours
// Checks both last_checked_at and started_at, uses most recent
```

#### Session Matching
```javascript
function isSessionMatch(state, sessionId) {
  if (sessionId) return state.session_id === sessionId;  // exact match
  return !state.session_id;  // legacy: only match stateless
}
```

#### Awaiting Confirmation
```javascript
const AWAITING_CONFIRMATION_TTL_MS = 2 * 60 * 1000; // 2 minutes
// Checks awaiting_confirmation === true AND timestamp within TTL
```

#### Cancel Signal
- Written by `state_clear`
- 30-second TTL
- Checked at session-scoped path first, then legacy path
- Fields: `requested_at`, `expires_at`

#### Stop Breaker (Circuit Breaker)
- Prevents infinite blocking
- Per-mode limits: team=20 (5min TTL), ralplan=30 (45min TTL)
- State: `{ count, updated_at }` in `{name}-stop-breaker.json`
- When count exceeds max → allows stop (fail-open)

#### Atomic File Writes
```javascript
function writeJsonFile(path, data) {
  const tmp = `${path}.${process.pid}.${Date.now()}.tmp`;
  writeFileSync(tmp, JSON.stringify(data, null, 2));
  renameSync(tmp, path);  // atomic rename
}
```

#### Session-Scoped State Reading
1. Try `{stateDir}/sessions/{sessionId}/{filename}` first
2. If not found, scan ALL session dirs for matching `session_id` field
3. Fall back to legacy `{stateDir}/{filename}` if session_id matches
4. If no sessionId provided, use legacy path only

---

## 8. Agent Prompts <a name="agent-prompts"></a>

### Executor Agent
```yaml
name: executor
model: claude-sonnet-4-6
level: 2
```

**Role**: Implement code changes precisely as specified. Write, edit, verify code within scope.

**Key Patterns**:
- Task classification: Trivial (single file), Scoped (2-5 files), Complex (multi-system)
- Investigation protocol: explore → understand patterns → create TodoWrite → implement step by step → verify each change
- 3-failure circuit breaker: after 3 failed attempts, escalate to architect
- Smallest viable diff principle
- READ-ONLY exploration via explore agents (max 3) permitted
- Plan files (`.omc/plans/*.md`) are READ-ONLY
- Learnings appended to notepad files (`.omc/notepads/{plan-name}/`)

**Verification**: lsp_diagnostics on each modified file, fresh build/test output required, grep for leftover debug code.

**Output Format**:
```
## Changes Made
- `file.ts:42-55`: [what changed and why]

## Verification
- Build: [command] -> [pass/fail]
- Tests: [command] -> [X passed, Y failed]
- Diagnostics: [N errors, M warnings]

## Summary
[1-2 sentences]
```

### Architect Agent
```yaml
name: architect
model: claude-opus-4-6
level: 3
disallowedTools: Write, Edit
```

**Role**: Analyze code, diagnose bugs, provide actionable architectural guidance. **READ-ONLY** (Write and Edit tools blocked).

**Key Patterns**:
- Every finding must cite specific `file:line` reference
- Root cause identification (not just symptoms)
- Trade-off analysis for every recommendation
- 3-failure circuit breaker: question architecture after 3+ fix attempts
- 4-phase debugging: Root Cause Analysis → Pattern Analysis → Hypothesis Testing → Recommendation
- Ralplan consensus: steelman antithesis + tradeoff tension + synthesis + principle-violation flags

**Output Format**:
```
## Summary
## Analysis (with file:line references)
## Root Cause
## Recommendations (prioritized: effort + impact)
## Trade-offs (table format)
## Consensus Addendum (ralplan only)
## References
```

### Verifier Agent
```yaml
name: verifier
model: claude-sonnet-4-6
level: 3
```

**Role**: Ensure completion claims are backed by fresh evidence.

**Key Patterns**:
- Verification is SEPARATE from authoring (never self-approve)
- No approval without fresh evidence
- Reject immediately on: "should/probably/seems to", no fresh test output, claims without results
- Run commands yourself, don't trust claims
- Red flags: "should", "probably", "seems to"

**Investigation Protocol**:
1. DEFINE: What tests prove this works? What edge cases? What could regress? Acceptance criteria?
2. EXECUTE (parallel): test suite, lsp_diagnostics_directory, build, grep related tests
3. GAP ANALYSIS: VERIFIED / PARTIAL / MISSING for each requirement
4. VERDICT: PASS or FAIL with evidence

**Output Format**:
```
## Verification Report
### Verdict: PASS | FAIL | INCOMPLETE (Confidence: high/medium/low, Blockers: count)
### Evidence (table: Check, Result, Command/Source, Output)
### Acceptance Criteria (table: #, Criterion, Status, Evidence)
### Gaps (description, risk level, suggestion)
### Recommendation: APPROVE | REQUEST_CHANGES | NEEDS_MORE_EVIDENCE
```

---

## 9. State Management — Files, Fields, Lifecycle <a name="state-management"></a>

### State File Locations

| Mode | State File | Location |
|------|-----------|----------|
| Ralph | `ralph-state.json` | `.omc/state/` or `.omc/state/sessions/{sessionId}/` |
| Autopilot | `autopilot-state.json` | same |
| Ultrawork | `ultrawork-state.json` | same |
| UltraQA | `ultraqa-state.json` | same |
| Team | `team-state.json` | same |
| Ralplan | `ralplan-state.json` | same |
| Pipeline | `pipeline-state.json` | same |
| Cancel Signal | `cancel-signal-state.json` | same |
| Skill Active | `skill-active-state.json` | same |
| Stop Breaker | `{name}-stop-breaker.json` | same |
| Subagent Tracking | `subagent-tracking.json` | `.omc/state/` |
| Idle Notification | `idle-notif-cooldown.json` | `.omc/state/` |

### PRD & Progress Files

| File | Location | Purpose |
|------|----------|---------|
| `prd.json` | project root or `.omc/` | User stories with acceptance criteria |
| `progress.txt` | project root or `.omc/` | Implementation details, files changed, learnings |

### Ralph State Fields
```json
{
  "active": true,
  "iteration": 1,
  "max_iterations": 100,
  "prompt": "original task text",
  "last_checked_at": "ISO-8601",
  "started_at": "ISO-8601",
  "session_id": "string",
  "project_path": "/path/to/project",
  "awaiting_confirmation": false,
  "awaiting_confirmation_set_at": "ISO-8601",
  "_stopNotified": false
}
```

### Autopilot State Fields
```json
{
  "active": true,
  "phase": "expansion|planning|execution|qa|validation|complete",
  "reinforcement_count": 0,
  "last_checked_at": "ISO-8601",
  "started_at": "ISO-8601",
  "session_id": "string"
}
```

### Ultrawork State Fields
```json
{
  "active": true,
  "reinforcement_count": 0,
  "max_reinforcements": 50,
  "original_prompt": "task text",
  "last_checked_at": "ISO-8601",
  "started_at": "ISO-8601",
  "session_id": "string",
  "project_path": "/path/to/project",
  "awaiting_confirmation": false,
  "deactivated_reason": "max_reinforcements_reached"
}
```

### UltraQA State Fields
```json
{
  "active": true,
  "goal_type": "tests|build|lint|typecheck|custom",
  "goal_pattern": null,
  "cycle": 1,
  "max_cycles": 5,
  "all_passing": false,
  "failures": ["description"],
  "started_at": "ISO-8601",
  "session_id": "string",
  "last_checked_at": "ISO-8601"
}
```

### PRD JSON Structure (inferred from skill)
```json
{
  "stories": [
    {
      "id": "US-001",
      "title": "Story title",
      "acceptanceCriteria": [
        "Specific testable criterion 1",
        "Specific testable criterion 2"
      ],
      "passes": false,
      "priority": 1
    }
  ]
}
```

---

## 10. Design Patterns Summary <a name="design-patterns-summary"></a>

### Pattern 1: Stop Hook Persistence Loop
The core persistence mechanism is NOT in the skill prompt — it's in `persistent-mode.cjs`. The skill prompt provides instructions; the hook enforces them by blocking Claude's stop attempts.

**How it works**:
1. Claude tries to stop (turn ends)
2. Hook reads state files from `.omc/state/`
3. If active mode found and not complete → output `{ "decision": "block", "reason": "..." }`
4. Claude receives the block message and continues working
5. Loop continues until mode completes or circuit breaker trips

### Pattern 2: PRD-Driven Story Tracking
Stories are the unit of work. Each has acceptance criteria that must be individually verified. The loop is:
```
pick story → implement → verify each criterion → mark passes:true → next story → all done? → reviewer verification
```

### Pattern 3: Tiered Agent Routing
Every delegation specifies a model tier:
- Haiku: trivial tasks (type exports, simple lookups)
- Sonnet: standard work (implementation, testing)
- Opus: complex analysis (debugging, architecture, reviewing)

### Pattern 4: Circuit Breakers
Multiple levels of circuit breakers prevent infinite loops:
- Ralph: extends max_iterations by 10 when reached (never truly stops)
- Ultrawork: deactivates after max_reinforcements (default 50)
- Team/Ralplan: stop breakers with TTL-based expiry
- Autopilot: max 20 reinforcements
- UltraQA: same error 3x → early exit
- General: 2-hour staleness threshold on all states

### Pattern 5: Separation of Authoring and Verification
- Executor writes code (level 2, Sonnet)
- Architect reviews code READ-ONLY (level 3, Opus)
- Verifier checks completion with fresh evidence (level 3, Sonnet)
- Ralph orchestrates the loop connecting them (level 4)

### Pattern 6: Session Isolation
- Each session gets its own state directory: `.omc/state/sessions/{sessionId}/`
- State matching requires exact session_id match
- Legacy (no sessionId) states only match legacy requests
- Prevents cross-session interference

### Pattern 7: Fail-Open Design
- All error handlers default to allowing stop (not blocking)
- Circuit breakers trip after max count → allow stop
- Stale states (>2h) are treated as inactive
- Auth errors, context limits, user aborts always pass through

### Pattern 8: Atomic State Updates
- Writes go to temp file first, then atomic rename
- Prevents partial/corrupt state on crash

### Pattern 9: Progressive Urgency in Stop Messages
- Early iterations: "Continue working"
- Mid iterations: "If complete, run cancel"
- Late iterations: "You MUST invoke cancel immediately"

### Pattern 10: Deslop as Mandatory Post-Process
- After reviewer approval, run ai-slop-cleaner on changed files
- Then re-verify (regression check)
- Only skip with explicit `--no-deslop` flag
- Ensures code quality even after AI-generated implementation

### Pattern 11: Parallel-First Execution
- Independent tasks fire simultaneously
- Long operations (builds, tests) run in background
- Short operations (file reads, git status) run in foreground
- Up to 6 concurrent child agents

### Pattern 12: State Cleanup on Completion
- On success: delete state files (don't just set active=false)
- Run `/oh-my-claudecode:cancel` for clean exit
- Stale state files left behind cause confusion in future sessions

---

## Key Differences for Hermes-Native Implementation

### What OMC Has That Hermes Must Replicate
1. **Stop hook mechanism** — The single most important piece. Without it, persistence doesn't work. In Hermes, this needs an equivalent "don't stop until done" enforcement.
2. **Session-scoped state files** — JSON files in `.omc/state/sessions/{id}/` with atomic writes
3. **PRD-driven story tracking** — `prd.json` with per-story acceptance criteria and `passes` boolean
4. **Tiered agent delegation** — model routing based on task complexity
5. **Circuit breakers** — prevent infinite loops at multiple levels
6. **Verification separation** — different agent verifies than the one that authored

### What Hermes Can Do Differently
1. **MCP tools instead of stop hooks** — Hermes can use MCP server state management natively
2. **Structured tool outputs** — Instead of JSON files, can use proper MCP state tools
3. **Native agent spawning** — Instead of Claude Code Task() calls, use Hermes agent orchestration
4. **Built-in iteration tracking** — Instead of file-based state, can use in-memory state with MCP persistence
