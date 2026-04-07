# LobeHub Skills Reference — Ralph, Deep-Interview, Autopilot

> Extracted April 2026 from LobeHub Skills Marketplace.
> Purpose: Reference for designing Hermes-native OMHA skill equivalents.

---

## Table of Contents

1. [Ralph Pattern Overview](#1-ralph-pattern-overview)
2. [Skill: Ouroboros Ralph (neversight)](#2-ouroboros-ralph-neversight)
3. [Skill: Ralph Autonomous Agent Loop (aradotso/Huntley)](#3-ralph-autonomous-agent-loop-aradotsohuntley)
4. [Skill: Ralph Autonomous Loop (anorbert-cmyk)](#4-ralph-autonomous-loop-anorbert-cmyk)
5. [Skill: Deep Interview (fainir)](#5-deep-interview-fainir)
6. [Skill: Deep Interview (dolodorsey/KHG)](#6-deep-interview-dolodorseykhg)
7. [Skill: Autopilot (sehoon787)](#7-autopilot-sehoon787)
8. [Skill: Autopilot (dolodorsey/KHG)](#8-autopilot-dolodorseykhg)
9. [Original Ralph Pattern (Geoffrey Huntley)](#9-original-ralph-pattern-geoffrey-huntley)
10. [Cross-Cutting Design Patterns](#10-cross-cutting-design-patterns)
11. [OMHA Design Implications](#11-omha-design-implications)

---

## 1. Ralph Pattern Overview

The "Ralph" pattern (named after Ralph Wiggum by Geoffrey Huntley) is a simple autonomous
loop that repeatedly feeds an AI coding agent a prompt + external state until all tasks are
done. All marketplace implementations share this DNA:

```
while tasks_remain:
    load_context(specs, plan, progress)
    pick_next_task()
    execute_task()
    verify(build, test, lint)
    commit_and_update_state()
```

Three key variants exist on LobeHub:
- **Ouroboros Ralph** — evolutionary loop with Socratic interviewing and convergence metrics
- **Huntley Ralph** — faithful to original bash loop, prd.json-driven, fresh instances
- **Agentic Kit Ralph** — simplified Plan→Execute→Verify→Repeat protocol

---

## 2. Ouroboros Ralph (neversight)

**ID:** `neversight-learn-skills.dev-ralph`
**Version:** 1.0.2 | **Author:** NeverSight | **Source:** [Q00/ouroboros](https://github.com/Q00/ouroboros)
**Stars:** 13 | **Downloads:** 92

### Philosophy

> "Stop prompting. Start specifying."
> "The beginning is the end, and the end is the beginning."
> The serpent doesn't repeat — it evolves.

### Evolutionary Loop

```
Interview → Seed → Execute → Evaluate
     ↑                            ↓
     └──── Evolutionary Loop ─────┘
```

Each cycle **evolves** (not repeats). Evaluation output feeds back as input for next
generation until convergence.

### Double Diamond Architecture

```
◇ Wonder          ◇ Design
   ╱ (diverge)       ╱ (diverge)
  ╱   explore       ╱   create
 ╱                  ╱
◆ ────────────── ◆ ────────────── ◆
 ╲                  ╲
  ╲   define        ╲   deliver
   ╲ (converge)      ╲ (converge)
    ◇ Ontology        ◇ Evaluation
```

- First diamond (Socratic): diverge into questions → converge into ontological clarity
- Second diamond (Pragmatic): diverge into design options → converge into verified delivery

### Commands

| Command | What It Does |
|---------|-------------|
| `ooo interview` | Socratic questioning → expose hidden assumptions |
| `ooo seed` | Crystallize interview into immutable spec (Ambiguity ≤ 0.2) |
| `ooo run` | Execute via Double Diamond decomposition |
| `ooo evaluate` | 3-stage gate: Mechanical → Semantic → Multi-Model Consensus |
| `ooo evolve` | Evolutionary loop until ontology converges (similarity ≥ 0.95) |
| `ooo unstuck` | 5 lateral thinking personas when stuck |
| `ooo status` | Drift detection + session tracking |
| `ooo ralph` | Persistent loop until verified — "The boulder never stops" |

### Ambiguity Formula

```
Ambiguity = 1 − Σ(clarityᵢ × weightᵢ)

Greenfield: Goal(40%) + Constraint(30%) + Success(30%)
Brownfield: Goal(35%) + Constraint(25%) + Success(25%) + Context(15%)

Threshold: Ambiguity ≤ 0.2 → ready for Seed
```

### Seed Specification (YAML)

```yaml
goal: Build a CLI task management tool
constraints:
  - Python 3.14+
  - No external database
  - SQLite for persistence
acceptance_criteria:
  - Tasks can be created
  - Tasks can be listed
  - Tasks can be marked complete
ontology_schema:
  name: TaskManager
  fields:
    - name: tasks
      type: array
    - name: title
      type: string
```

### 3-Stage Evaluation

| Stage | Cost | What It Checks |
|-------|------|----------------|
| Mechanical | $0 | Lint, build, tests, coverage |
| Semantic | Standard | AC compliance, goal alignment, drift score |
| Consensus | Frontier | Multi-model vote, majority ratio |

### Drift Thresholds

- 0.0–0.15: Excellent (on track)
- 0.15–0.30: Acceptable (monitor closely)
- 0.30+: Exceeded (course correction needed)

### Cancellation

| Action | Command |
|--------|---------|
| Save checkpoint & exit | `/ouroboros:cancel` |
| Force clear all state | `/ouroboros:cancel --force` |
| Resume after interruption | `ooo ralph continue` |

---

## 3. Ralph Autonomous Agent Loop (aradotso/Huntley)

**ID:** `aradotso-trending-skills-ralph-autonomous-agent-loop`
**Version:** 1.0.1 | **Author:** Aradotso | **Based on:** Geoffrey Huntley's Ralph pattern

### Architecture

Faithful to the original Huntley pattern. A bash script (`ralph.sh`) spawns **fresh AI
instances** per task to prevent context pollution.

### Iteration Protocol

1. Read `prd.json` → pick highest-priority story where `passes: false`
2. Spawn fresh AI instance (Amp or Claude Code) with story prompt
3. AI implements, runs quality checks (typecheck, tests), commits
4. Update `prd.json` → mark story `passes: true`
5. Append learnings to `progress.txt`
6. Repeat until all stories pass or max iterations reached
7. Output `<promise>COMPLETE</promise>` when done

### prd.json Schema

```json
{
  "branchName": "feature/user-dashboard",
  "projectContext": "A Next.js SaaS app using Prisma, tRPC, and Tailwind.",
  "userStories": [
    {
      "id": "story-1",
      "title": "Add avatar column to users table",
      "priority": 1,
      "passes": false,
      "description": "Add an optional avatarUrl string column...",
      "acceptanceCriteria": [
        "Migration file created and applied",
        "User model updated in schema.prisma",
        "TypeScript types regenerated",
        "Existing tests still pass"
      ]
    }
  ]
}
```

| Field | Type | Purpose |
|-------|------|---------|
| branchName | string | Git branch Ralph creates/works on |
| projectContext | string | Shared context injected into every iteration |
| userStories[].id | string | Unique identifier |
| userStories[].priority | number | Lower = higher priority (1 is first) |
| userStories[].passes | boolean | false = not done, true = complete |
| userStories[].acceptanceCriteria | string[] | What AI must verify before marking done |

### Key Files

| File | Purpose |
|------|---------|
| `ralph.sh` | Bash loop spawning fresh AI instances |
| `prompt.md` | Prompt template for Amp iterations |
| `CLAUDE.md` | Prompt template for Claude Code iterations |
| `prd.json` | Live task list with passes status |
| `progress.txt` | Append-only learnings across iterations |

### Running

```bash
./scripts/ralph/ralph.sh              # Default: Amp, 10 iterations
./scripts/ralph/ralph.sh 20           # Custom iteration count
./scripts/ralph/ralph.sh --tool claude # Use Claude Code
./scripts/ralph/ralph.sh --tool claude 15
```

### Workflow

```
/prd → Generate PRD markdown
/ralph → Convert PRD to prd.json
./ralph.sh → Execute autonomous loop
```

---

## 4. Ralph Autonomous Loop (anorbert-cmyk)

**ID:** `anorbert-cmyk-agentic-kit-ralph`
**Version:** 1.0.1 | **Source:** [agentic-kit](https://github.com/anorbert-cmyk/agentic-kit)

### 4-Phase Loop Protocol

#### Phase 1: Context & Consensus ("Read")
1. Locate Source of Truth: `task.md`, `prd.md`, or `IMPLEMENTATION_PLAN.md`
2. Identify next actionable item (highest priority, uncompleted)
3. Verify state via `git status` or file contents

#### Phase 2: Atomic Execution ("Act")
1. Consult specialists from `.agent/skills/` (frontend-design, backend-architect, etc.)
2. Isolate the task — one bullet point only, no bundling
3. Plan the move — state clearly: "I am now implementing [Task Name]..."
4. Execute — write code, run commands, refactor (no lazy placeholders)

#### Phase 3: Verification ("Check")
1. Mandatory proof — run specific tests, lint, browser check
2. Self-correction — if verification fails, fix immediately (no asking permission)

#### Phase 4: Committing Progress ("Update")
1. Mark item as `[x]` in task.md or PRD
2. Git commit: `git commit -m "feat: [Task Name]"`
3. Loop or Exit: more tasks → continue immediately; all done → notify with summary

### Critical Rules

- Do NOT ask permission between iterations (unless critical blocker)
- Maintain momentum — goal is to clear the list
- Micro-tasks — if too big, break down in task list first, then execute

---

## 5. Deep Interview (fainir)

**ID:** `fainir-best-agent-deep-interview`
**Version:** 1.0.1 | **Author:** fainir | **Source:** [fainir/best-agent](https://github.com/fainir/best-agent)

### Core Concept

Socratic, one-question-at-a-time discovery with mathematical ambiguity scoring.
Agent **refuses to proceed until ambiguity < 20%**.

### Ambiguity Scoring

| Dimension | Weight (Greenfield) | Weight (Brownfield) |
|-----------|:---:|:---:|
| Goal | 0.40 | 0.35 |
| Constraints | 0.30 | 0.25 |
| Success Criteria | 0.30 | 0.25 |
| Context | N/A | 0.15 |

```
ambiguity = 1 - (goal × w_goal + constraints × w_const + success × w_succ [+ context × w_ctx])
```

Gate: Do NOT proceed to implementation until ambiguity < 0.20.

### Protocol Phases

#### Phase 0: Brownfield Detection (before any questions)
1. Run Glob/Grep to understand project structure
2. Read key files (package.json, README, main entry points)
3. Identify existing patterns, conventions, tech stack
4. Cite actual code in questions
5. Extract domain entities, track ontology across rounds
6. Codebase scan pre-fills Context score (often 0.6–0.8)

#### Phase 1: Initial Assessment
- Score each dimension from what's known
- Show score transparently
- Ask ONE question targeting the weakest dimension

#### Phase 2: Iterative Questioning
- One question at a time — never batch
- Show score after every answer — user sees progress
- Target the weakest dimension always
- Use codebase evidence in questions

#### Phase 3: Challenge Modes (at thresholds)

| Round | Mode | Purpose |
|-------|------|---------|
| 4+ | Contrarian | "What if we did the opposite?" |
| 6+ | Simplifier | "What's the absolute minimum version?" |
| 8+ | Ontologist | "Let me make sure we're using the same terms..." |

#### Phase 4: Exit Conditions
- Green light: Ambiguity < 20% → automatic proceed
- Early exit: User says "just do it" after round 3+ → proceed with risk disclosure
- Hard cap: 20 rounds max
- Soft warning at round 10

### Question Format

```
Round {n} | Targeting: {weakest_dimension} | Why now: {rationale} | Ambiguity: {score}%

{question}
```

### Output Format

```
## Requirements Summary

### Goal
[1-2 sentence description]

### Constraints
- [constraint 1]
- [constraint 2]

### Success Criteria
- [ ] [testable criterion 1]
- [ ] [testable criterion 2]

### Context
- Existing patterns: [what we're building on]
- Files to modify: [expected files]
- Dependencies: [new deps needed]

### Ambiguity Score: X% (Goal: Y, Constraints: Z, Success: W, Context: V)

### Open Questions (if any remain)
- [question that couldn't be resolved]
```

### Integration Pipeline
1. Requirements summary → input to the Planner
2. Success criteria → sprint contract (`.claude/contract.md`)
3. Open questions → flagged for decision during implementation

---

## 6. Deep Interview (dolodorsey/KHG)

**ID:** `dolodorsey-khg-skills-arsenal-deep-interview`
**Version:** 1.0.1 | **Author:** dolodorsey
**Source:** [khg-skills-arsenal](https://github.com/dolodorsey/khg-skills-arsenal)

Inspired by the Ouroboros project. Nearly identical scoring to fainir's version but adds:

### State Schema

```json
{
  "active": true,
  "current_phase": "deep-interview",
  "state": {
    "interview_id": "<uuid>",
    "type": "greenfield|brownfield",
    "initial_idea": "<user input>",
    "rounds": [],
    "current_ambiguity": 1.0,
    "threshold": 0.2,
    "codebase_context": null,
    "challenge_modes_used": [],
    "ontology_snapshots": []
  }
}
```

### Ontology Extraction & Stability Tracking

Each round extracts key entities (name, type, fields, relationships). For rounds 2+:
- **stable_entities**: present in both rounds with same name
- **changed_entities**: different names but same type AND >50% field overlap
- **new/removed_entities**: unmatched
- **stability_ratio**: `(stable + changed) / total_entities`

### Ambiguity Scoring

Uses **opus model, temperature 0.1** for consistency. Same formula as fainir's.

### Question Targeting by Dimension

| Dimension | Question Style | Example |
|-----------|---------------|---------|
| Goal | "What exactly happens when...?" | "When you say 'manage tasks', what specific action does a user take first?" |
| Constraints | "What are the boundaries?" | "Should this work offline, or is internet assumed?" |
| Success Criteria | "How do we know it works?" | "What would make you say 'yes, that's it'?" |
| Context (brownfield) | "How does this fit?" | "I found JWT auth in src/auth/. Should this extend that?" |
| Ontology | "What IS the core thing?" | "You named Tasks, Projects, Workspaces. Which is core?" |

### Core Execution Policy
- Ask ONE question at a time — never batch
- Target the weakest clarity dimension each round
- Explore codebase first (via explore agent) before asking user
- Score ambiguity after every answer — display transparently
- Do not proceed until ambiguity ≤ threshold
- Persist interview state for resume across session interruptions

---

## 7. Autopilot (sehoon787)

**ID:** `sehoon787-my-claude-autopilot`
**Version:** 1.0.1 | **Author:** sehoon787
**Source:** [sehoon787/my-claude](https://github.com/sehoon787/my-claude)

### 5-Phase Execution Pipeline

| Phase | Name | Details |
|-------|------|---------|
| 1 | Planning | Architect (Opus) creates plan → Critic (Opus) validates. Skipped if ralplan consensus exists. Output: `.omc/plans/autopilot-impl.md` |
| 2 | Execution | Ralph + Ultrawork. Haiku (simple), Sonnet (standard), Opus (complex). Parallel for independent tasks. |
| 3 | QA | UltraQA: build, lint, test, fix. Up to 5 cycles. Same error 3× → stop. |
| 4 | Validation | Parallel review: Architect (functional), Security-reviewer (vulns), Code-reviewer (quality). All must approve. |
| 5 | Cleanup | Delete state files: autopilot-state.json, ralph-state.json, ultrawork-state.json, ultraqa-state.json |

### Execution Policy
- Phase-gated: each phase completes before next begins
- Parallel execution within Phases 2 and 4
- QA: up to 5 cycles; same error 3× → stop and report
- Validation: all reviewers must approve; rejection → fix and re-validate
- Cancel anytime: `/oh-my-claudecode:cancel`

### Trigger Keywords
"autopilot", "autonomous", "build me", "create me", "make me", "full auto",
"handle it all", "I want a/an..."

### Escalation & Stop Conditions
- Same QA error persists 3 cycles → stop (fundamental issue)
- Validation fails after 3 re-validation rounds → stop
- User says "stop", "cancel", or "abort"
- Vague requirements → redirect to `/deep-interview`

### Tool Usage
- `Task(subagent_type="oh-my-claudecode:architect", ...)`
- `Task(subagent_type="oh-my-claudecode:security-reviewer", ...)`
- `Task(subagent_type="oh-my-claudecode:code-reviewer", ...)`

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

---

## 8. Autopilot (dolodorsey/KHG)

**ID:** `dolodorsey-khg-skills-arsenal-autopilot`
**Version:** 1.0.1 | **Author:** dolodorsey
**Source:** [khg-skills-arsenal](https://github.com/dolodorsey/khg-skills-arsenal)

Nearly identical to sehoon787's autopilot (both derive from oh-my-claudecode). Same
5-phase pipeline, same configuration, same escalation rules. Key addition:

### 3-Stage Recommended Pipeline

```
/deep-interview "vague idea"
  → Socratic Q&A → spec (ambiguity ≤ 20%)
  → /ralplan --direct → consensus plan (Planner/Architect/Critic approved)
  → /autopilot → skips Phase 0+1, starts at Phase 2 (Execution)
```

When autopilot detects a ralplan consensus plan (`.omc/plans/ralplan-*.md` or
`.omc/plans/consensus-*.md`), it **skips Phase 0 (Expansion) and Phase 1 (Planning)**
because the plan has already been requirements-validated, architecture-reviewed, and
quality-checked.

### Deep Interview Integration

For vague inputs, Phase 0 redirects:
```
User: "autopilot build me something cool"
Autopilot: "Your request is open-ended. Would you like to run a deep interview first?"
  [Yes, interview first (Recommended)] [No, expand directly]
```

If spec exists at `.omc/specs/deep-interview-*.md`, autopilot uses it directly.

### Cancel Skill

A companion `/cancel` skill detects which mode is active:
- Autopilot: stops workflow, preserves progress for resume
- Ralph: stops persistence loop, clears linked ultrawork
- Ultrawork: stops parallel tasks

---

## 9. Original Ralph Pattern (Geoffrey Huntley)

**Source:** [ghuntley.com/ralph](https://ghuntley.com/ralph/)

### Purest Form

```bash
while :; do cat PROMPT.md | claude-code ; done
```

### Core Principles

1. **Specifications-First**: Have long conversation about requirements first.
   Write specs (one per file) in a specifications folder. Loaded every loop.

2. **One Task Per Loop**: "To get good outcomes, ask Ralph to do one thing per loop.
   Only one thing."

3. **Fresh Context Each Loop**: Every iteration starts clean — prevents context rot.

4. **Context Window as Scheduler**: Primary context should schedule work;
   spawn subagents for expensive operations (search, test analysis).

5. **Backpressure**: Type systems, static analyzers, security scanners, test suites
   serve as quality gates. "The wheel has to turn fast."

6. **Don't Assume Not Implemented**: Before making changes, search codebase using
   parallel subagents. Prevent duplicate implementations.

7. **Capture Test Intent**: Tests must be self-documenting with explanations of WHY
   they exist (helps future LLM loops decide whether to fix or delete).

8. **No Cheating**: Force full implementations, no placeholders.

9. **Disposable TODO Lists**: Generate from spec-vs-code comparison using up to
   500 subagents. Delete and regenerate frequently.

10. **Loop Back**: Always feed outputs back as inputs (logs, IR, test results).

### Real-World Numbers

$50k USD contract MVP delivered for **$297 USD** in AI costs.

---

## 10. Cross-Cutting Design Patterns

### Pattern 1: Ambiguity-Gated Execution

All deep-interview implementations share:
- 4-dimension weighted scoring (Goal, Constraints, Success, Context)
- Hard threshold (ambiguity ≤ 0.2) before proceeding
- One question at a time, targeting weakest dimension
- Brownfield detection pre-fills Context score

**OMHA equivalent needed:** A `clarify` procedure with ambiguity scoring.

### Pattern 2: External State + Fresh Instances

All ralph implementations share:
- State lives in files (prd.json, progress.txt, task.md)
- Each iteration loads fresh context from these files
- Git commits provide audit trail and rollback
- Completion tracked via boolean flags or checkboxes

**OMHA equivalent needed:** State schemas in Hermes conversation state, not files.

### Pattern 3: Phase-Gated Pipeline

Autopilot skills use strict phase ordering:
1. Requirements → 2. Design → 3. Execute → 4. QA → 5. Validate → 6. Cleanup

With skip logic (if upstream artifacts exist, skip redundant phases).

**OMHA equivalent needed:** Multi-step procedures with conditional phase skipping.

### Pattern 4: Multi-Perspective Validation

Autopilot spawns parallel reviewer agents:
- Architect (functional completeness)
- Security reviewer (vulnerabilities)
- Code reviewer (quality)
All must approve. Rejection triggers fix + re-validate.

**OMHA equivalent needed:** Parallel tool calls for multi-agent review.

### Pattern 5: Escalation & Stop Conditions

Consistent across skills:
- Same error 3× → stop and report (fundamental issue)
- Max iteration caps (configurable)
- User can cancel with progress preservation
- Resume from checkpoint

**OMHA equivalent needed:** Error tracking with escalation thresholds.

### Pattern 6: Ontology Tracking

Ouroboros ralph and KHG deep-interview track:
- Entity extraction per round
- Stability ratio across rounds
- Convergence threshold (similarity ≥ 0.95)

**OMHA equivalent needed:** Ontology state in conversation context.

---

## 11. OMHA Design Implications

### Skills to Build

| OMC Skill | OMHA Equivalent | Key Adaptation |
|-----------|----------------|----------------|
| deep-interview | `omha-clarify` | Ambiguity scoring via Hermes state, not file-based |
| ralph (Huntley) | `omha-execute-loop` | State in Hermes messages, not prd.json files |
| ralph (Ouroboros) | `omha-evolve` | Evolutionary convergence with ontology tracking |
| autopilot | `omha-autopilot` | Phase-gated pipeline with Hermes tool orchestration |
| cancel | `omha-cancel` | Progress preservation in Hermes state |

### State Management Shift

OMC skills use filesystem state:
- `.omc/plans/`, `.omc/specs/`, `.omc/state/`
- `prd.json`, `progress.txt`, `task.md`
- `autopilot-state.json`, `ralph-state.json`

OMHA should use Hermes conversation state:
- Structured state in message metadata
- Tool results as state transitions
- Conversation history as audit trail

### Key Formulas to Preserve

1. **Ambiguity scoring** (4 weighted dimensions, 0.2 threshold)
2. **Drift detection** (0.0–0.15 excellent, 0.30+ needs correction)
3. **Ontology stability** (entity tracking, ≥0.95 convergence)
4. **Escalation rules** (3× same error → stop, 5 QA cycles max)

### Integration Chain

```
omha-clarify (ambiguity → spec)
  → omha-plan (spec → consensus plan)
    → omha-autopilot (plan → execution → QA → validation)
      ↳ omha-execute-loop (inner ralph loop for implementation)
      ↳ omha-cancel (graceful stop with state preservation)
```

---

## Source URLs

| Skill | LobeHub URL |
|-------|-------------|
| Ouroboros Ralph | https://lobehub.com/skills/neversight-learn-skills.dev-ralph |
| Huntley Ralph | https://lobehub.com/skills/aradotso-trending-skills-ralph-autonomous-agent-loop |
| Agentic Kit Ralph | https://lobehub.com/skills/anorbert-cmyk-agentic-kit-ralph |
| Deep Interview (fainir) | https://lobehub.com/skills/fainir-best-agent-deep-interview |
| Deep Interview (KHG) | https://lobehub.com/skills/dolodorsey-khg-skills-arsenal-deep-interview |
| Autopilot (sehoon787) | https://lobehub.com/skills/sehoon787-my-claude-autopilot |
| Autopilot (KHG) | https://lobehub.com/skills/dolodorsey-khg-skills-arsenal-autopilot |
| Original Ralph | https://ghuntley.com/ralph/ |
| snarktank/ralph (GitHub) | https://github.com/snarktank/ralph |
| Q00/ouroboros (GitHub) | https://github.com/Q00/ouroboros |
| fainir/best-agent (GitHub) | https://github.com/fainir/best-agent |
| sehoon787/my-claude (GitHub) | https://github.com/sehoon787/my-claude |
| dolodorsey/khg-skills-arsenal | https://github.com/dolodorsey/khg-skills-arsenal |
