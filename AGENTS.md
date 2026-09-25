# Lafia

Interoperable foundation for Benin's national digital health record: one FHIR core holds all medical data, independent domain services read and write it.

Read `SYSTEM_PROMPT.md` before any grilling, spec, ticket or implementation: it holds the project brief, the architecture invariants and the health-data security statement. Every domain term comes from `CONTEXT.md`.

## Sessions

- One feature per session. A session either runs `/grill-with-docs` → `/to-spec` → `/to-tickets` for one feature, or `/implement`s one ticket.
- At each phase boundary, state what the phase produced and propose the next move: continue, `/clear` once the output is published, or `/handoff` when the window is past half full.
- Tickets are vertical slices: each one ends on behaviour reachable through a service endpoint and covered by a test.

## Repository map

```
commun/          shared library: FHIR client, token verification, audit
services/<name>/ identite, soin, caisse, pharmacie, citoyen
donnees/         synthetic dataset and its loader
web/design/      design system: tokens, pictograms, components (workspace package)
web/<acteur>/    one Next.js application per actor: citoyen, soin, caisse, pharmacie
tests/           black-box suite against the running stack, through the gateway
docs/            architecture, specs, ADRs (docs/adr/), design (docs/design/)
```

Commands live in `docker-compose.yml`, each service's `pyproject.toml`, the `web/` workspace's `package.json` and `tests/pyproject.toml`; `README.md` lists the ones to start the stack and run the suite.

`SYSTEM_PROMPT.md` and `CONTEXT.md` are canonical. The HTML files at the root are the French deliverables derived from them.

## Conventions

- Name modules, routes, identifiers and UI text with the French terms of `CONTEXT.md` (`cas`, `visite`, `ordonnance`). FHIR resource names stay in English, as the standard defines them.
- Business rules live in each service's `regles/`; FHIR translation lives in `commun/fhir`; route handlers stay thin.
- Test at the service seam: HTTP request in, FHIR resources out, against a real HAPI container and synthetic data.
- A decision that is hard to reverse becomes an ADR in `docs/adr/`.
- A change to how the running system works (a container, a network, a route through the gateway, what can reach what) updates `docs/architecture.md` in the same commit.

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues for `StephaneBah/Lafia`, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
