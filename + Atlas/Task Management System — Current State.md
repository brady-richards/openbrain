---
title: Task Management System — Current State
created: 2026-04-23
tags: [process, asana, gtd]
---

# Task Management System — Current State

## Philosophy

Inspired by **Getting Things Done (GTD)**. The core principle: capture everything, process it into actionable items, and trust the system enough to let your mind focus on doing rather than remembering.

At Doro, this is reinforced organizationally — Asana is the single task management tool for the whole team, valued as a trust and accountability mechanism: *we build trust by doing what we say we will do.*

## How Tasks Flow In

| Source | Mechanism |
|---|---|
| Email | Manually tagged → auto-synced to Asana |
| Slack | Occasionally, manually |
| Meetings | High volume — primary source |

**Gap:** Due dates are not set automatically. Every inbound task arrives undated and needs manual refinement.

## Intended Workflow

```
Capture → Refine (add due date) → To Do → In Progress (active) → Done
```

- **In Progress** = tasks actively being worked, typically due today
- **To Do** = refined, dated tasks waiting for capacity
- **Backlog / unrefined** = captured but not yet processed (no due date)

## What's Actually Happening

**In Progress is gummed up.** It contains two mixed populations:

1. **Well-defined tasks** — clear scope, due today, actively being worked
2. **Ill-defined tasks** — captured from meetings/email, no due date, need refinement

The result: In Progress doesn't reflect what's actually being worked on — it's functioning more as a holding area.

**Root cause:** Low confidence that moving something to To Do means it will actually get done. So tasks stay in In Progress as a hedge against losing visibility on them. The system isn't trusted enough to let go.

## The Tension

The volume of inbound "stuff" (especially from meetings) outpaces the time available to refine tasks and assign due dates. Without refinement, tasks can't move through the system cleanly. Without trust in To Do, nothing moves at all.
