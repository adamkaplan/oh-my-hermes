# OMH Plugin Proposal: Infrastructure Layer for Natural Skills

## The Problem

OMH skills work, but they're verbose. Roughly half of each SKILL.md is "how to operate
the infrastructure" rather than "what to do." Compare:

**OMC (with plugin scoping):**
```
Task(subagent_type="oh-my-claudecode:executor")
```

**OMH (skills only):**
```
Load the executor role prompt from `omh-ralplan/references/role-executor.md`.
Pass the FULL prompt text inlined in the delegate_task call — subagents can't
load skill files.

delegate_task(
    goal="Implement this task:\n\n{task description}\n\n{acceptance criteria}",
    context="{full role prompt text}\n\n---\n\nProject Context:\n{tech stack}
    \n\nPrevious Feedback:\n{verifier rejection}\n\nLearnings:\n{completed tasks}"
)
```

The Claude Code plugin system gives OMC skills three things we lack:

1. **Mechanical guarantees** — hooks enforce behavior (stop prevention, verification)
   rather than relying on the agent to follow prose instructions
2. **Implicit infrastructure** — role prompt loading, model routing, and subagent
   lifecycle are handled by the plugin, not spelled out in every skill
3. **Composable hooks** — concerns are separated across small, focused hook scripts
   rather than encoded in 250-line monolithic SKILL.md files

## What the Plugin Would Provide

A Hermes plugin (`oh-my-hermes` or `omh`) installed at `~/.hermes/plugins/omh/` that
registers hooks and custom tools to give OMH skills the same infrastructure OMC gets
from its Claude Code plugin.

### 1. Role Prompt Auto-Loading Tool

**Problem:** Every delegation requires manually loading a role prompt file and inlining
it in the context string. This is ~5 lines of boilerplate per delegation.

**Solution:** A custom tool `omh_delegate` that wraps `delegate_task`:

```
omh_delegate(
    role="executor",
    goal="Implement the auth module",
    task_context="Project uses FastAPI...",
    learnings=[...],
    previous_feedback="..."
)
```

The tool automatically:
- Loads the role prompt from a configured directory
- Constructs the context string with proper formatting
- Applies model routing (if configured) based on role tier
- Returns the same result as delegate_task

Skills shrink from paragraphs of delegation boilerplate to single tool calls.

### 2. State Management Tools

**Problem:** Skills manually read/write JSON state files with atomic write patterns.
Every skill re-implements: read file → parse JSON → modify → write to .tmp → rename.

**Solution:** Custom tools for OMH state:

```
omh_state_read(mode="ralph")       → returns parsed JSON
omh_state_write(mode="ralph", data={...})  → atomic write
omh_state_check(mode="ralph")      → exists? active? stale?
omh_cancel_check()                 → cancel signal present?
```

### 3. Persistence Hook (on_session_end)

**Problem:** Ralph and autopilot rely on prompt-based persistence — the agent is
instructed to continue, but nothing mechanically prevents it from stopping. The
one-task-per-invocation pattern works around this but adds caller loop complexity.

**Solution:** An `on_session_end` hook that:
- Checks if an OMH mode is active (ralph-state.json or autopilot-state.json exists with active=true)
- If active: logs a warning, ensures state is saved, and optionally queues a re-invocation message
- Doesn't block exit (Hermes hooks can't veto), but ensures clean state preservation

### 4. Evidence Gathering Tool

**Problem:** Ralph's verification step requires the orchestrator to run builds/tests,
capture output, truncate to 2000 chars, then pass to the verifier. This is ~15 lines
of procedure in the SKILL.md.

**Solution:** A tool that handles the common pattern:

```
omh_gather_evidence(
    commands=["npm run build", "npm test", "npm run lint"],
    truncate=2000
)
→ returns {build: "...", test: "...", lint: "...", all_pass: true/false}
```

### 5. Model Tier Routing (Optional)

**Problem:** All subagents use the same model. OMC routes Haiku for simple tasks,
Sonnet for standard, Opus for complex — saving 30-50% on token costs.

**Solution:** Configuration in the plugin that maps roles to model tiers:

```yaml
# ~/.hermes/plugins/omh/config.yaml
model_routing:
  low: "haiku"        # explore, writer
  medium: "sonnet"    # executor, verifier, test-engineer
  high: "opus"        # architect, critic, planner
```

The `omh_delegate` tool reads this config and passes the model override to delegate_task.

## Impact on Skill Verbosity

With the plugin, ralph's executor delegation shrinks from:

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

To:

```markdown
omh_delegate(
    role="executor",
    goal="Implement: {task.title}\n{task.description}",
    criteria=task.acceptance_criteria,
    learnings=state.completed_task_learnings,
    previous_feedback=task.verifier_verdict
)
```

The skill expresses intent. The plugin handles mechanism.

## Implementation

Hermes plugins live at `~/.hermes/plugins/<name>/` with:
- `plugin.yaml` — manifest (name, version, provides_tools, provides_hooks)
- `__init__.py` — `register(ctx)` function that registers tools and hooks

The plugin uses `PluginContext.register_tool()` to add custom tools and hook callbacks
for the 8 available Hermes lifecycle hooks.

Available hooks: `pre_tool_call`, `post_tool_call`, `pre_llm_call`, `post_llm_call`,
`pre_api_request`, `post_api_request`, `on_session_start`, `on_session_end`.

## Phased Approach

The skills-first approach was correct for v1 — it proved the workflow architecture
works without any code changes. The plugin is the natural v2: keep the same skills
but give them better primitives to work with.

```
v1.0 (done):   Skills only — verbose but functional
v2.0 (plugin): Skills + plugin — natural and mechanical
v3.0 (upstream): Submit plugin + skills to hermes-agent optional-skills/
```

The plugin doesn't replace the skills — it makes them better. Existing skills continue
to work without the plugin (they just stay verbose). With the plugin installed, skills
can use the shorter tool-based patterns.

## Estimated Effort

| Component | Complexity | Lines (est.) |
|-----------|-----------|-------------|
| Plugin scaffold (plugin.yaml, __init__.py) | Low | ~50 |
| omh_delegate tool | Medium | ~150 |
| omh_state_read/write/check tools | Low | ~100 |
| omh_cancel_check tool | Low | ~30 |
| omh_gather_evidence tool | Medium | ~100 |
| on_session_end hook | Low | ~50 |
| Model routing config | Low | ~50 |
| **Total** | | **~530** |

About a day of focused work, plus testing.
