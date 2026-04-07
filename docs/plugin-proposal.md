# OMH Plugin Proposal v2: Infrastructure Layer for Natural Skills

## Revision Note

v1 of this proposal (~530 lines estimated) was written before analyzing the actual OMC
source code. After reading ~12,000 lines of OMC TypeScript across hooks, state management,
model routing, delegation, tools, and skill activation, this v2 reflects the true scope
of what makes OMC skills "natural" and what OMH needs to replicate.

**The insight (from a colleague): "The plugin code is the real value from OMC."** The
skills are markdown — anyone can write "plan then execute then verify." The hard part
is the 1,310-line persistent-mode engine, the session-scoped state machine, the weighted
model router, the delegation enforcer, and the 36 MCP tools that let skills express
intent in one line instead of spelling out mechanism in a paragraph.

---

## The Problem (With Evidence)

OMH v1.0 skills work but are verbose. Here's a real comparison from our codebase:

**OMC skill (ralph SKILL.md) — delegation:**
```
Task(subagent_type="oh-my-claudecode:executor")
```
The plugin handles: role prompt loading, model routing (Sonnet), context construction,
session isolation, progress tracking.

**OMH skill (omh-ralph SKILL.md) — same delegation:**
```markdown
Load the executor role prompt from `omh-ralplan/references/role-executor.md`.
Pass the FULL prompt text inlined in the delegate_task call — subagents can't
load skill files.

delegate_task(
    goal="Implement this task:\n\n{task.title}\n{task.description}\n\n
    Acceptance Criteria:\n{task.acceptance_criteria}",
    context="{role-executor.md prompt}\n\n---\n\nProject Context:\n
    {tech stack, conventions, relevant paths}\n\nPrevious Feedback
    (if retry):\n{verifier's rejection feedback}\n\nLearnings from
    prior tasks:\n{completed_task_learnings from ralph-state.json}"
)
```

**OMC skill — state management:**
```
state_write(mode="ralph", data={iteration: 5, phase: "verify"})
```

**OMH skill — same state management:**
```markdown
Update `.omh/state/ralph-state.json`:
1. Read the current file
2. Parse JSON
3. Update the `iteration` and `phase` fields
4. Write to `.omh/state/ralph-state.json.tmp`
5. Rename `.tmp` to `.json` (atomic write)
```

The OMH skill spends ~50% of its lines on infrastructure plumbing. The plugin eliminates
that plumbing by providing tools that handle it mechanically.

---

## What OMC's Plugin Infrastructure Actually Does

Based on analysis of the actual source code (see companion docs):

### 1. Persistent Mode Engine (1,310 LOC in OMC)

**What it does mechanically:**
- Intercepts every Claude Code Stop event
- Checks modes in priority order: Ralph(1) > Autopilot(2) > Team(3) > Ralplan(4) > Ultrawork(5) > SkillState(6)
- For each active mode: reads state files, checks circuit breakers, decides block/allow
- Circuit breakers: max iterations, staleness (2h), cancel signal (30s TTL), error loops (20 per 5min for team, 30/45min for ralplan)
- Cancel protocol: multiple redundant paths (file signal, user abort detection, rate limit, auth error, context limit)
- On block: injects progressive urgency messages ("continue working" → "if complete run cancel" → "you MUST cancel immediately")

**Hermes equivalent:** `on_session_end` hook — but it CANNOT veto exit. It can only:
- Log a warning
- Ensure state is cleanly saved
- Queue a notification (e.g., Telegram: "autopilot interrupted at iteration 7")

**OMH plugin design:**
- `on_session_end` hook: detect active OMH modes, ensure atomic state save, send notification
- `pre_llm_call` hook: inject mode-awareness context ("you are in ralph iteration 7, do not stop")
- Accept that mechanical stop prevention is impossible — compensate with clean resumability
- ~150 lines of Python

### 2. State Machine (1,793 LOC in OMC)

**What it does mechanically:**
- Unified API: `state_read(mode)`, `state_write(mode, data)`, `state_clear(mode)`, `state_list_active()`
- Session-scoped isolation: state paths include session ID to prevent cross-session leakage
- `_meta` envelope: every state write wraps data with `{_meta: {written_at, written_by, session_id}, ...data}`
- Mtime-validated 5-second cache: avoids re-reading files that haven't changed
- Atomic writes: write to temp → fsync → rename (crash-safe)
- Legacy migration: auto-upgrades old state formats

**Hermes equivalent:** None — skills manually read/write JSON files.

**OMH plugin design:**
Register 5 tools via `PluginContext.register_tool()`:

```python
omh_state_read(mode: str) → dict
    # Reads .omh/state/{mode}-state.json, validates session, returns parsed JSON
    
omh_state_write(mode: str, data: dict) → dict
    # Atomic write with _meta envelope, session scoping

omh_state_clear(mode: str) → dict
    # Delete state file (used on completion/cleanup)

omh_state_check(mode: str) → dict
    # Returns: exists, active, stale, session_match, phase

omh_state_list() → dict
    # List all active OMH modes with summary status
```

Each tool handles: file I/O, JSON parsing, atomic writes, session scoping, staleness
detection, error handling. Skills just call the tool.

~250 lines of Python.

### 3. Delegation Layer (2,617 LOC in OMC)

**What it does mechanically:**

*Delegation Enforcer* (intercepting every Task/Agent call):
- Reads delegation config to determine provider + model for the role
- Injects/normalizes model parameters automatically
- Intercepts PreToolUse hook to modify delegation calls in-flight

*Delegation Routing* (resolving where to send work):
- 4-level precedence: explicit param > delegation config > env var > default
- Provider resolution: maps role → provider:model
- API key resolution: finds the right credential for the resolved provider

*Delegation Categories* (7 semantic categories):
- ANALYSIS (architect, critic): tier HIGH, temp 0.7, thinking budget 16K
- IMPLEMENTATION (executor): tier MEDIUM, temp 0.3, thinking budget 8K
- REVIEW (security, code-reviewer): tier HIGH, temp 0.5, thinking budget 12K
- PLANNING (planner): tier HIGH, temp 0.7, thinking budget 16K
- EXPLORATION (explore): tier LOW, temp 0.3, thinking budget 4K
- TESTING (test-engineer, qa): tier MEDIUM, temp 0.3, thinking budget 8K
- DOCUMENTATION (writer): tier LOW, temp 0.5, thinking budget 4K

*Model Routing* (weighted scoring):
- Extracts signals from task text (lexical: "architect", "refactor"; structural: file count, code blocks; contextual: conversation length)
- 20 priority-ordered rules (first match wins)
- Calculates weighted complexity score: <4=LOW/Haiku, 4-7=MEDIUM/Sonnet, 8+=HIGH/Opus
- When rules and scorer diverge by >1 level: reduces confidence, prefers higher tier

**Hermes equivalent:** `delegate_task` accepts a `model` param, but no auto-routing.

**OMH plugin design:**
Register 1 high-level tool:

```python
omh_delegate(
    role: str,           # "executor", "architect", "verifier", etc.
    goal: str,           # What to accomplish
    task_context: str,   # Project-specific context
    learnings: list = None,      # From completed tasks
    previous_feedback: str = None,  # From prior rejection
    model_override: str = None      # Skip auto-routing
) → dict
```

The tool:
1. Loads the role prompt from a configured directory (default: `~/.hermes/skills/omh-ralplan/references/role-{name}.md`)
2. Looks up the role's category → tier → model from config
3. Constructs the context string (role prompt + task context + learnings + feedback)
4. Calls `delegate_task` with the assembled goal, context, and model
5. Returns the subagent's result

Config file (`~/.hermes/plugins/omh/config.yaml`):
```yaml
role_prompts_dir: ~/.hermes/skills/omh-ralplan/references
model_routing:
  enabled: true
  tiers:
    low: null      # use default model (cheapest available)
    medium: null   # use default model
    high: null     # use default model
  # Users can override:
  # tiers:
  #   low: "anthropic/claude-haiku"
  #   medium: "anthropic/claude-sonnet"
  #   high: "anthropic/claude-opus"
roles:
  executor: {category: implementation, tier: medium}
  verifier: {category: review, tier: medium}
  architect: {category: analysis, tier: high}
  planner: {category: planning, tier: high}
  critic: {category: analysis, tier: high}
  analyst: {category: analysis, tier: high}
  security-reviewer: {category: review, tier: high}
  code-reviewer: {category: review, tier: high}
  test-engineer: {category: testing, tier: medium}
  debugger: {category: analysis, tier: medium}
```

~300 lines of Python.

### 4. Evidence Gathering Tool (new — no direct OMC equivalent)

OMC's verifier agent can run commands. Hermes verifier subagents are READ-ONLY (our design
choice). So the orchestrator gathers evidence. This is repeated boilerplate in every skill.

```python
omh_gather_evidence(
    commands: list[str],   # ["npm run build", "npm test", "npm run lint"]
    truncate: int = 2000,  # Keep last N chars per command
    workdir: str = None
) → dict
    # Returns: {results: [{cmd, output, exit_code, truncated}], all_pass: bool}
```

~100 lines of Python.

### 5. Cancel Check Tool

```python
omh_cancel_check(mode: str = "ralph") → dict
    # Checks .omh/state/{mode}-cancel.json, validates TTL (30s)
    # Returns: {cancelled: bool, reason: str, requested_by: str}
```

~40 lines of Python.

### 6. Session Hooks

**`on_session_start`:**
- Check for active OMH modes
- If found: inject mode-awareness into the agent's context ("You are mid-autopilot, Phase 2, ralph iteration 7. Read .omh/state/autopilot-state.json to continue.")
- ~50 lines

**`on_session_end`:**
- Check for active OMH modes
- If found: ensure state is atomically saved, log the interruption point
- Optionally send notification (Telegram/Discord) if configured
- ~50 lines

**`pre_llm_call`:**
- If an OMH mode is active: inject a brief reminder into user context
- This is the prompt-based persistence — not mechanical, but consistent
- ~30 lines

---

## What We're NOT Replicating (and Why)

### From OMC's Plugin Layer

| OMC Component | LOC | Why Not | Alternative |
|---|---|---|---|
| Stop hook blocking (veto exit) | ~500 | Hermes hooks can't veto. Architectural impossibility. | State-based resume + `on_session_end` save + notification |
| Transcript parsing (approval detection) | ~200 | Hermes doesn't expose raw transcript to hooks | Use tool results (delegate_task return values) |
| Team infrastructure | ~3,000+ | Hermes subagents are isolated, no inter-agent messaging | Out of scope — fundamental architecture difference |
| HUD statusline | ~2,000+ | Hermes has no terminal display API for plugins | Use `todo` tool + progress files |
| LSP tools (12) | ~1,500 | Requires language server integration | Terminal-based: `tsc --noEmit`, `pylsp`, `ripgrep` |
| AST tools (2) | ~500 | Requires ast-grep integration | Terminal: `ast-grep` CLI (if installed) |
| Notification system | ~2,000+ | Hermes has its own gateway (Telegram, Discord, etc.) | Use Hermes's native `send_message` tool |
| Rate limit daemon | ~500 | Hermes has credential pool rotation | Adequate for most cases |
| Python REPL | ~800 | Hermes has `execute_code` | Already available |

### From OMC's Skill Activation Layer

| OMC Component | Why Not | Alternative |
|---|---|---|
| 15-regex keyword detector | Hermes matches skill descriptions automatically | Adequate — add better trigger keywords to SKILL.md descriptions |
| Learned skill injection | Hermes skills are self-improving (skill_manage patch) | Different mechanism, same outcome |
| Context injection framework | Hermes uses system prompt + progressive disclosure | Already works |
| Skill-state protection levels | Would need `pre_llm_call` injection | Partial — via hook, see above |

---

## Revised Scope and Estimates

### Core Plugin (~850 lines Python)

| Component | Lines | Priority | Impact |
|---|---|---|---|
| Plugin scaffold (plugin.yaml, __init__.py, config) | 80 | Required | Foundation |
| `omh_state_read/write/clear/check/list` (5 tools) | 250 | High | Eliminates manual JSON in all skills |
| `omh_delegate` (1 tool + config loading) | 300 | High | Delegation paragraph → one tool call |
| `omh_gather_evidence` (1 tool) | 100 | High | Verification boilerplate → one tool call |
| `omh_cancel_check` (1 tool) | 40 | Medium | Cancel detection cleanup |
| Session hooks (start + end + pre_llm) | 80 | Medium | Mode awareness + clean interruption |

### Optional Extensions (~650 lines Python)

| Component | Lines | Priority | Impact |
|---|---|---|---|
| Model tier routing (config + resolution) | 150 | Medium | 30-50% cost savings |
| Notepad tools (priority/working/manual sections) | 150 | Low | Cross-invocation scratchpad |
| Progress tracking tool (append-only log) | 100 | Low | Replaces manual file appends |
| Trace tools (timeline, summary) | 150 | Low | Debugging/observability |
| Enhanced keyword matching via `pre_llm_call` | 100 | Low | Better skill activation |

### Total

```
Core plugin:          ~850 lines  (~2-3 days)
Optional extensions:  ~650 lines  (~2 days)
Full plugin:        ~1,500 lines  (~4-5 days)
```

This is significantly more than v1's estimate of 530 lines but still an order of
magnitude smaller than OMC's ~12,000 lines — because we're building on Hermes's
existing primitives (delegate_task, terminal, read_file, write_file) rather than
from scratch, and we're not replicating team infrastructure, HUD, LSP, or the
notification system.

---

## Impact on Skills

With the core plugin, here's how each skill changes:

### omh-ralph (currently 246 lines)

**Before (v1, skills only):**
```markdown
### Step 4: Execute

Load the executor role prompt from `omh-ralplan/references/role-executor.md`.
Pass the FULL prompt text inlined in the delegate_task call...

delegate_task(
    goal="Implement this task:\n\n{task.title}\n{task.description}\n\n
    Acceptance Criteria:\n{task.acceptance_criteria}",
    context="{role-executor.md prompt}\n\n---\n\n..."
)
```

**After (v2, with plugin):**
```markdown
### Step 4: Execute

omh_delegate(role="executor", goal="Implement: {task.title}\n{task.description}",
    task_context="Acceptance Criteria:\n{task.acceptance_criteria}",
    learnings=state.completed_task_learnings,
    previous_feedback=task.verifier_verdict)
```

**Before:**
```markdown
1. Read `.omh/state/ralph-state.json`
2. Parse JSON
3. Check active, phase, staleness...
```

**After:**
```markdown
state = omh_state_read(mode="ralph")
# state includes: active, phase, stale, session_match + all data
```

**Before (evidence gathering):**
```markdown
1. Run the project's build command. Capture output.
2. Run the project's test suite. Capture output.
3. Run linting/type-checking. Capture output.
4. Truncate each to 2000 chars...
```

**After:**
```markdown
evidence = omh_gather_evidence(commands=["npm run build", "npm test", "npm run lint"])
```

**Estimated reduction: 246 → ~140 lines** (~43% shorter, and the remaining lines
are pure workflow logic).

### omh-autopilot (currently 252 lines)

Similar reductions across all 6 phases. Estimated: 252 → ~150 lines.

### omh-ralplan (currently 138 lines)

Delegation boilerplate reduced. Estimated: 138 → ~90 lines.

### omh-deep-interview (currently 233 lines)

Least affected — most of its content is interview logic, not infrastructure.
State management would shrink. Estimated: 233 → ~200 lines.

---

## Implementation Plan

### Phase 1: Core Plugin (Days 1-3)

1. Plugin scaffold: `~/.hermes/plugins/omh/plugin.yaml` + `__init__.py`
2. Config loading: `~/.hermes/plugins/omh/config.yaml` with role mappings
3. State tools: `omh_state_read`, `omh_state_write`, `omh_state_clear`, `omh_state_check`, `omh_state_list`
4. Delegate tool: `omh_delegate` with role prompt auto-loading
5. Evidence tool: `omh_gather_evidence`
6. Cancel tool: `omh_cancel_check`
7. Session hooks: `on_session_start`, `on_session_end`, `pre_llm_call`

### Phase 2: Refactor Skills (Days 3-4)

8. Refactor omh-ralph to use plugin tools
9. Refactor omh-autopilot to use plugin tools
10. Refactor omh-ralplan to use plugin tools
11. Update omh-deep-interview state management
12. Test all skills with plugin installed

### Phase 3: Optional Extensions (Days 5+)

13. Model tier routing config
14. Notepad tools
15. Progress tracking tool
16. Trace tools

### Backward Compatibility

Skills MUST continue to work without the plugin. The plugin makes them shorter
and more reliable, but the verbose v1 instructions remain valid. This means:

- Skills check for plugin tools (`omh_delegate`) and fall back to manual delegation
- OR: maintain two versions of each skill (verbose and plugin-aware)
- OR: accept that the plugin is required for v2 skills (recommended — simpler)

**Recommendation:** v2 skills require the plugin. v1 skills remain in a `legacy/`
directory for users who don't want the plugin. The README documents both paths.

---

## Comparison: OMC vs OMH Plugin

| Dimension | OMC Plugin | OMH Plugin |
|---|---|---|
| Language | TypeScript (~12,000 LOC) | Python (~1,500 LOC) |
| Stop prevention | Mechanical (veto exit) | Best-effort (save state + notify) |
| State management | 5 tools via MCP server | 5 tools via Hermes plugin |
| Delegation | Enforcer + router + categories | Single `omh_delegate` tool + config |
| Model routing | Weighted multi-signal scoring | Config-based tier mapping |
| Tools exposed | 36 MCP tools | 8-12 plugin tools |
| Skill activation | Keyword regex + injection | Hermes skill description matching |
| Team support | Full orchestration | Not supported |
| HUD | Real-time statusline | Not supported (use todo/logs) |
| LSP/AST | 14 tools | Not supported (use terminal) |
| Distribution | Claude Code plugin marketplace | Hermes plugin (pip or directory) |

The OMH plugin is ~8x smaller than OMC's because:
1. Hermes provides more built-in primitives (delegate_task, terminal, file tools)
2. We're not replicating team, HUD, LSP, or notification infrastructure
3. Python is more concise than TypeScript for this type of glue code
4. We accept best-effort persistence instead of mechanical stop prevention
