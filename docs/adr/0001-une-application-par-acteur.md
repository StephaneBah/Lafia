# 0001. One application per actor, paired with its service

- Status: accepted
- Date: 2026-09-25

## Context

Lafia is a noyau with independent services around it. The interfaces were first planned as React apps served as static files; we now build them with Next.js. A single Next.js app for every profile would put every actor's screens, cookies and data access in one process, and a Next.js server can fetch data on its own, opening a path around the services where tokens are checked, roles applied and `AuditEvent`s written.

## Decision

- **One Next.js app per actor**: `web/citoyen`, `web/soin`, `web/caisse`, `web/pharmacie`, in an npm workspace. The pattern repeats the services layer: a laboratoire or a third party adds its own app next to its own service.
- **Each app calls its own service plus `identite`**, and nothing else. If the caisse app needs data, `caisse` exposes it by reading the noyau.
- **Each app has its own subdomain** (`soin.<domaine>`, `caisse.<domaine>`, …). Caddy routes the subdomain to the app and `/api/*` on that subdomain to the paired service and to `identite`. Session cookies are therefore isolated per actor.
- **Each app runs as a Next.js standalone container**, with a memory limit. Apps are attached to the gateway network only, never to the noyau's network, so they cannot reach HAPI even by mistake.
- **The design system is a workspace package, `web/design/`**: tokens, pictograms, components. It is built into each app, like `commun/` for services, and is never a runtime dependency.
- **The token lives in an `httpOnly`, `Secure`, `SameSite=Strict` cookie** set on the app's subdomain. Client JavaScript never reads it.

## Consequences

- Four Next.js containers, about 150 MB each, next to HAPI on an 8 GB VM: memory limits are mandatory.
- DNS needs one record per app, or a wildcard.
- Least privilege is visible in the architecture, not only in code: the caisse app has no route to clinical data.
- Rejected: one app with a route group per profile (shared process and origin across actors); static export (no dynamic routes such as `/ordonnances/[numero]` without client-only routing); copying the design system into each app (drift within days).
