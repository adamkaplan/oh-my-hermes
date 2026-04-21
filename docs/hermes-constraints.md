# Hermes Constraints

How OMH works around the limits of Hermes's subagent and lifecycle model.

## Subagent and Lifecycle Constraints

| Constraint | Impact | How OMH Handles It |
|---|---|---|
| 3 concurrent subagents | Can't fire 6 parallel agents like OMC | Batch into groups of 3; validation phase fits exactly |
| No recursive delegation | Subagents can't spawn subagents | All orchestration at top level; subagents are leaf workers |
| No stop-prevention hook | Can't mechanically force continuation | One-task-per-invocation + state files for ralph; prompt-based for ralplan |
| Subagents lack `execute_code` | Children reason step-by-step | Orchestrator handles batch operations; subagents use tools directly |
| Subagents lack `memory` | Children can't write to shared memory | State passed via files and delegate_task context |

## Capabilities Skills Alone Can't Provide

These require Hermes code changes or plugins (some of which the v2 plugin
already addresses; others remain open):

| Gap | What OMC Has | Why We Can't | Path Forward |
|-----|-------------|-------------|--------------|
| **Stop prevention** | `persistent-mode.cjs` — 1144 lines that mechanically block Claude Code from exiting | Hermes has no `Stop` lifecycle hook. Skills can instruct but can't enforce. | PR: `pre_session_end` veto hook. Our workaround: state files + re-invocation. |
| **LSP integration** | 12 IDE-grade tools (hover, references, rename, diagnostics) | Not a skill-level feature — requires tool registration or MCP server. | PR or MCP server package. We use terminal-based tools (ripgrep, linters). |
| **ast-grep** | Structural code search/replace using AST matching | Same — needs tool registration. | Terminal fallback: `ast-grep` CLI works if installed. |
| **HUD / observability** | Real-time statusline with token tracking, agent activity | No display API in Hermes skills. | Plugin using `post_tool_call` hook. We use `todo` + progress logs. |
| **Rate limit auto-resume** | `omc wait` daemon monitors for resets | No equivalent daemon mechanism. | Hermes has credential pool rotation, which handles most cases. |
