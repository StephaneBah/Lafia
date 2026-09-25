# Skills: what I use, what I removed, and why

Personal playbook for the `mattpocock/skills` set in this repo. Human-facing: agents do not read this file.

Two kinds of skill, two costs:

- **User-invoked** (`/name`, I type it): zero context cost, but I must remember it exists.
- **Model-invoked** (the agent can fire it): its description sits in context on every turn. An irrelevant one costs tokens and can misfire, so those are the first to remove.

## The flow, per feature

```
Session A (one feature, one unbroken window)
  /grill-with-docs  →  /to-spec  →  /to-tickets
       │ design question needs runnable code?
       └─ /handoff → /prototype (fresh session) → /handoff back

Session B, C, D... (one ticket each, fresh window)
  /implement   (drives /tdd, closes with /code-review, commits)
```

**Context rule.** I stay under half the window. At a phase boundary past 50%: if the output is already published (spec, tickets, commit), `/clear`; otherwise `/handoff` and restart from the file. I never push on into the degraded zone.

## Kept

| Skill | Invocation | When I reach for it |
|---|---|---|
| `setup-matt-pocock-skills` | user | Once, at repo setup |
| `grill-with-docs` | user | Start of every feature; fills `CONTEXT.md` and ADRs |
| `to-spec` | user | End of grilling: the PRD for the feature |
| `to-tickets` | user | Split the spec into vertical slices with blocking edges |
| `implement` | user | One ticket per fresh session |
| `handoff` | user | Context past half, or detour to a prototype |
| `tdd` | model | Pulled in by `implement`; red-green at the service seam |
| `code-review` | model | Pulled in by `implement`; standards and spec, side by side |
| `grilling` | model | Engine behind `grill-with-docs`; must stay installed |
| `domain-modeling` | model | Keeps `CONTEXT.md` clean; pulled in by grilling |
| `codebase-design` | model | Deep-module vocabulary used by `tdd` |
| `research` | model | Background reading on primary sources, output as a markdown file |
| `prototype` | model | Throwaway code to settle a logic or UI question |
| `diagnosing-bugs` | model | Anything broken or failing that resists a first look |
| `wizard` | model | Steps only I can do: Azure VM, DNS, secrets |
| `git-guardrails-claude-code` | model | Run once: blocks destructive git commands for unattended agents |
| `writing-for-agents` | model | Editing AGENTS.md, SYSTEM_PROMPT.md, or writing the design skill |
| `ask-matt` | user | When I forget which skill fits |
| `to-questionnaire` | user | Field interviews with nurses, cashiers, pharmacists |
| `teach` | user | Learning FHIR or agent concepts in a stateful workspace |
| `wait-what` | user | When an answer does not land |

## Removed

| Skill | Reason |
|---|---|
| `grill-me` | Stateless twin of `grill-with-docs`; in a repo the stateful one wins |
| `wayfinder` | For foggy multi-session efforts; the feature map in SYSTEM_PROMPT.md already charts the way, and two days leave no room for its pace |
| `triage` | For incoming issues I did not write; solo project |
| `improve-codebase-architecture` | Upkeep after v1, not during |
| `resolving-merge-conflicts` | Solo, sequential tickets; reinstall if I run parallel agents on branches |
| `setup-pre-commit` | Husky / JS tooling; services are Python |
| `migrate-to-shoehorn`, `scaffold-exercises` | Unrelated to this project; model-invoked, so pure context cost |
| `in-progress/*` (`claude-handoff`, `implement-spec`, `loop-me`, `pr`, `retro`, `setup-ts-deep-modules`, `writing-*`) | Beta skills; `pr` is model-invoked. Revisit once stable |

```bash
npx skills list
npx skills remove grill-me wayfinder triage improve-codebase-architecture \
  resolving-merge-conflicts setup-pre-commit migrate-to-shoehorn scaffold-exercises
npx skills remove claude-handoff implement-spec loop-me pr retro \
  setup-ts-deep-modules writing-beats writing-fragments writing-shape
```

Skills from `in-progress/` may not have been installed at all; `npx skills list` tells.

## One-time setup

1. Place `AGENTS.md`, `SYSTEM_PROMPT.md`, `CONTEXT.md` at the repo root.
2. Remove the skills above.
3. Run `/setup-matt-pocock-skills`: GitHub Issues, single-context domain docs. It appends the `## Agent skills` block to `AGENTS.md`.
4. For Claude Code, create `CLAUDE.md` containing exactly these two lines, so both files load every session:
   ```
   @AGENTS.md
   @SYSTEM_PROMPT.md
   ```
5. Run `/git-guardrails-claude-code`.

## Phase 0: before the first feature

**Research** (`/research`, in the background):

- R1. HAPI FHIR JPA in Docker: memory settings, PostgreSQL wiring, running with no published port.
- R2. The riskiest assumption: that HAPI supports, out of the box, every search the services need (`EpisodeOfCare?patient`, `Encounter?episode-of-care`, `MedicationRequest?group-identifier`, `_include` / `_revinclude`).
- R3. Azure for Students: allowed VM sizes and regions, DNS label, Caddy TLS on the VM's hostname.

**Prototype** (`/prototype`, logic branch):

- P1. The ordonnance line state model: unpaid, paid, partially dispensed, dispensed, with deferred payment in emergencies. The partial-payment and partial-dispense combinations are the hard part to reason about on paper.

**Design**: produced in Claude Design from `docs/design/prd_for_design.md`. Once validated, the tokens and rules become a project skill written with `writing-for-agents`.