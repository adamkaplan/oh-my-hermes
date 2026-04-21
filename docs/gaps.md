# Honest Gaps

OMH v1.0 replicates the core execution pipeline (~85%) but not the full OMC
feature surface (~60% overall). This document tracks what's missing.

For gaps that require Hermes-level changes (LSP, stop prevention, HUD), see
[`hermes-constraints.md`](hermes-constraints.md).

## Could Be Skills (Not Yet Built)

| Gap | What OMC Has | Priority | Effort |
|-----|-------------|----------|--------|
| **19 more agent roles** | designer, qa-tester, scientist, git-master, tracer, vision, product-manager, ux-researcher, etc. We have 10 of OMC's 29. | Medium | Low per role — add as needed |
| **Deslop pass** | `ai-slop-cleaner` as mandatory post-process in ralph | Medium | New skill |
| **Model tier routing** | Auto-routes Haiku/Sonnet/Opus by task complexity. We use one model for all. | Low-Medium | Routing logic in autopilot |
| **Ontology extraction** | Tracks entities across interview rounds with stability ratios | Medium-High | Deep-interview v1.1 |
| **Brownfield explore-first** | Scans codebase before asking the user | Medium | Deep-interview v1.1 |
| **Team mode** | Native agent teams with direct inter-agent messaging | Low | Fundamental architecture difference — Hermes subagents are isolated |
| **Multi-model orchestration** | Claude + Codex + Gemini workers via tmux | Low | Niche; ACP transport partially addresses |
