# The Agentic Coding Paradigm
*A Workflow Framework by Matt Pocock*

## Core Principles & LLM Constraints

- **Software Engineering Fundamentals Apply**: Classical engineering principles remain essential when working with AI agents [1].
- **Smart Zone vs. Dumb Zone**: LLMs operate best in a ~100k token "smart zone" where attention is crisp [3, 4]. Beyond this, quadratic attention scaling causes performance to degrade into the "dumb zone" [4, 5, 35].
- **Clear Context over Compacting**: Rather than "compacting" conversation history (which accumulates token sediment), developers should clear context frequently to return to a lean system prompt [9, 10].
- **Rejection of "Specs-to-Code" Vibe Coding**: Blindly turning specifications into code without maintaining developer comprehension leads to fragile codebases [13].

---

## Workflow: Day Shift vs. Night Shift

```
[Idea / Brief] ──> [Grill Me Skill] ──> [PRD Destination] ──> [Kanban / Vertical Slices]
                                                                        │
                                                             (Day Shift / Human-in-Loop)
────────────────────────────────────────────────────────────────────────┼───────────────────────────
                                                             (Night Shift / AFK Execution)
                                                                        ▼
[Human QA & Taste] <── [Isolated Code Review] <── [TDD / Red-Green] <── [AFK Ralph Loop Agent]
```

### 1. Day Shift (Human-in-the-Loop Alignment & Planning)
- **The "Grill Me" Skill**: A reciprocal interview process where the AI relentlessly quizzes the developer until both reach a shared "design concept" [12, 15, 16].
- **PRD (Destination Document)**: Summarizes the agreed design concept into problem statements, solution goals, user stories, and definition of done [28, 29, 30].
- **Kanban DAG & Vertical Slices (Tracer Bullets)**: Breaks the PRD into independent, parallelizable tasks arranged in a Directed Acyclic Graph (DAG) [37, 46]. Tasks use "vertical slices" (UI + API + DB) rather than horizontal layers to ensure immediate feedback [39, 40, 41].

### 2. Night Shift (AFK Execution & Feedback Loops)
- **AFK Ralph Loops**: Autonomous agents execute off-keyboard in isolated sandboxes (e.g., Docker / Sand Castle) by pulling tasks from the Kanban backlog [49, 50, 51, 81].
- **Test-Driven Development (TDD)**: Agents write failing tests first (red-green-refactor) to provide tight automated feedback loops and prevent AI test cheating [61, 62, 64].
- **Deep Modules Architecture**: Code is structured into deep modules with simple interfaces hiding implementation complexity [70, 71]. Developers manage module boundaries while delegating internal "gray box" coding to agents [71, 73].
- **Isolated Reviewers & Human QA**: Code is reviewed by a separate agent with clean context using "push" coding standards [60, 80]. Final manual QA allows the developer to enforce taste and prevent code slop [66, 67].
