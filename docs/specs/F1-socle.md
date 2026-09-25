# PRD F1: Socle — noyau, passerelle, services, applications par acteur

## Problem Statement

Lafia has a settled architecture and nothing running. Every later feature (identité, soin, caisse, pharmacie, citoyen, accès d'urgence) needs the same foundation: a noyau that holds medical data and is reachable only by services, a gateway that is the only public entry, one application per actor on its own subdomain, and a shared way for services to speak FHIR and check tokens. Without it, each feature would reinvent plumbing, and the architecture invariants (services never call each other, applications never reach the noyau, least privilege per actor) would stay promises in a document instead of properties of the running system.

The challenge is also judged on a working deployed platform: the jury must be able to reach a public address on day 1, and every later feature must land on it continuously.

## Solution

A Docker Compose stack, deployed on an Azure VM and runnable identically on a laptop, that brings up:

- the **noyau**: HAPI FHIR R4 in default configuration on PostgreSQL, publishing no port;
- the **passerelle**: Caddy, the only public entry, routing one subdomain per application;
- the five **services** (`identite`, `soin`, `caisse`, `pharmacie`, `citoyen`), each a FastAPI skeleton that proves it reaches the noyau and verifies tokens;
- the four **applications** (`citoyen`, `soin`, `caisse`, `pharmacie`), each a Next.js skeleton on its own subdomain that shows its actor's name and whether its service is up;
- the shared library **`commun`** (FHIR client, token verification) and the web workspace with an empty **design** package, ready for F0.

The two networks make the invariants physical: an application cannot reach the noyau because it is not on the noyau's network, and the gateway forwards each subdomain's API calls only to its own service and to `identite`.

## User Stories

1. As a jury member, I want to open the public address of each application on day 1, so that I can see the platform is really deployed.
2. As a jury member, I want each application to tell me whether its service and the noyau are reachable, so that I can see the whole chain is alive, not a static mock-up.
3. As a developer, I want one command to bring up the whole stack locally, so that I can work on any feature without setup rituals.
4. As a developer, I want the local stack to use the same subdomain layout as production (`soin.localhost`, `caisse.localhost`, …), so that what works locally works deployed.
5. As a developer, I want one command to deploy the current `main` to the Azure VM, so that the public address follows the repository continuously.
6. As a developer, I want the noyau to run in HAPI's default configuration, so that Lafia stays conformant to the standard and project rules live in the services.
7. As a developer, I want the noyau to publish no port on the host, so that no one reaches medical data except through a service.
8. As a developer, I want each service to reach the noyau through a shared FHIR client, so that no service reimplements FHIR calls.
9. As a developer, I want the FHIR client to read the noyau's address from the environment, so that the same image runs locally and on Azure.
10. As a developer, I want each service to expose a health route that checks it reaches the noyau and reports the noyau's FHIR version, so that I can tell a broken service from a broken noyau.
11. As a developer, I want each service to verify tokens with the shared library, without calling `identite`, so that services stay independent at runtime.
12. As a security reviewer, I want tokens signed with a private key only `identite` holds, and verified with a public key every service holds, so that a compromised service cannot forge tokens.
13. As a security reviewer, I want a request without a token to a protected route to be refused with 401, so that no data leaks by default.
14. As a security reviewer, I want a request with an expired, malformed or wrongly signed token to be refused with 401, so that only live, genuine tokens open anything.
15. As a security reviewer, I want each service to accept only the roles it serves (soin: médecin, infirmier; caisse: caissier; pharmacie: pharmacien; citoyen: citoyen) and refuse others with 403, so that least privilege holds from the first route.
16. As an agent, I want my application to show who I am connected as (role, établissement), read from my verified token by my own service, so that I know which identity writes in the dossier.
17. As a security reviewer, I want each application's subdomain to forward API calls only to its own service and to `identite`, so that the caisse application has no path to clinical routes.
18. As a security reviewer, I want applications attached only to the gateway network, so that an application cannot reach the noyau even by a coding mistake.
19. As a security reviewer, I want the token carried in an `httpOnly`, `Secure`, `SameSite=Strict` cookie scoped to the application's subdomain, so that client JavaScript never reads it and a caisse cookie is never sent to the soin application.
20. As a developer, I want secrets (signing keys, database passwords, domain) read from environment variables with an example file in the repository and the real file ignored by git, so that no secret is ever committed.
21. As an operator, I want every container to carry an explicit memory limit, so that HAPI and four Next.js applications fit on an 8 GB VM without starving each other.
22. As an operator, I want the noyau's data to survive a restart of the stack, so that a redeploy does not wipe the dataset.
23. As an operator, I want Caddy to obtain and renew a TLS certificate for each subdomain automatically, so that every application is served over HTTPS with no manual step.
24. As an operator, I want containers to restart automatically after a crash or a VM reboot, so that the public address stays up during judging.
25. As a developer, I want the services to start only once the noyau answers, so that a cold start does not produce a burst of errors.
26. As a developer, I want the web workspace to hold the four applications and the design package, with the design package built into each application, so that F0 can fill the design system without touching the applications' structure.
27. As a developer, I want each application built as a Next.js standalone image, so that the containers stay small.
28. As a developer, I want each service built from its own image with `commun` included at build time, so that there is no runtime dependency between services.
29. As a future integrator (laboratoire, télémédecine), I want adding an actor to mean adding one service, one application and one gateway rule, so that the platform grows without modifying existing parts.
30. As a developer, I want each service's OpenAPI documentation reachable through the gateway, so that the application developer and third parties see the contract.
31. As a developer, I want a black-box test suite that runs against the running stack through the gateway, so that the architecture invariants are checked, not assumed.
32. As a developer, I want that suite to run the same way locally and against the deployed address, so that I can verify production after each deploy.

## Implementation Decisions

**Topology**

- One Compose project with two networks. **passerelle**: Caddy, the five services, the four applications. **noyau**: HAPI, its PostgreSQL, and the four domain services that speak FHIR (`soin`, `caisse`, `pharmacie`, `citoyen`). `identite` is on the passerelle network only: it owns its own database (added in F2) and never speaks FHIR.
- HAPI runs from the official image in default configuration, backed by PostgreSQL through environment settings only, with a persistent volume. No port is published to the host.
- Caddy is the only container publishing ports (80, 443).

**Gateway routing**

- The base domain comes from the environment. Locally it is `localhost`, giving `citoyen.localhost`, `soin.localhost`, `caisse.localhost`, `pharmacie.localhost`, with Caddy's internal certificates. On Azure it is the VM's domain, with automatic public certificates.
- For each application subdomain: `/api/<own service>/*` goes to its service, `/api/identite/*` goes to `identite`, everything else goes to the application. Any other `/api/*` path returns 404 at the gateway.

**Services**

- Five FastAPI services, one image each, `commun` built in. Each exposes under its own prefix:
  - `GET /api/<service>/sante`, public: for services on the noyau network, checks the noyau (FHIR `metadata`) and returns the service name, status and the noyau's FHIR version; `identite` returns its own status only.
  - `GET /api/<service>/session`, protected: returns the agent or citoyen identifier, role and établissement from the verified token. 401 without a valid token; 403 when the role is not one the service serves.
  - OpenAPI documentation under the service's prefix.
- Roles accepted per service: soin (médecin, infirmier), caisse (caissier), pharmacie (pharmacien), citoyen (citoyen), identite (any role, for `/moi` in F2).
- Route handlers stay thin; the role rule lives in each service's `regles`.

**`commun` library**

- **FHIR client**: base URL from environment; reads and writes FHIR resources as JSON; exposes a capability check used by `/sante`. Translation between domain terms and FHIR resources is added here by later features.
- **Token verification**: asymmetric signature (EdDSA or RS256); public key from environment; checks signature, expiry and required claims (subject, role, établissement; NPI for citoyen). Exposed to services as a FastAPI dependency returning the verified identity, plus a role guard.
- Token format, shared by F2 which issues real tokens:
  - `sub`: agent identifier (or citoyen scope identifier)
  - `role`: one of médecin, infirmier, caissier, pharmacien, citoyen
  - `etablissement`: Organization id (absent for citoyen)
  - `npi`: present for citoyen only
  - `exp`: short lifetime (minutes, not hours)
- The token is read from the application's session cookie, forwarded by the gateway. A bearer header is also accepted, for tests and third-party integrators.
- Audit (`AuditEvent` production) is not in F1: it lands with the first patient read in F3.

**Applications**

- An npm workspace at the web root holding `design` (an empty package with its build wiring, filled by F0) and four Next.js applications (App Router, TypeScript, standalone output).
- Each application has one page: its actor's name in French, its service's status from `/api/<service>/sante`, and, if a session cookie is present, the result of `/api/<service>/session`. No design work beyond what makes the page legible; F0 brings the design system.
- Server-side calls from an application to its service go through the gateway address on the passerelle network, never directly to the noyau.

**Operations**

- Environment variables: base domain, signing public key (services), signing private key (`identite`, used from F2), database credentials, noyau URL. An example file is committed; the real file is git-ignored.
- Memory limits: HAPI first (its JVM heap bounded explicitly), then services and applications. The total fits 8 GB with headroom.
- `restart: unless-stopped` on every container; health checks on the noyau and the services; services depend on a healthy noyau.
- Azure: Ubuntu 24.04 VM, 2 vCPU, 8 GB; only ports 80 and 443 open; one DNS record per subdomain or a wildcard. Deployment: pull `main` on the VM and bring the stack up; one documented command.

## Testing Decisions

- **What a good test is here:** it treats the stack as a black box and asserts behaviour a user or attacker can observe (status codes, JSON bodies, reachability), never internal structure. It uses resource ids and synthetic identities only.
- **Seam 1, the gateway (main seam):** an HTTP test suite run against the running Compose stack through Caddy, addressing each application by its subdomain. It covers:
  - each subdomain serves its application page;
  - `/api/<own service>/sante` returns 200 with the noyau's FHIR version, proving application subdomain → gateway → service → noyau;
  - cross-actor paths are closed: `caisse.<domaine>/api/soin/…` and similar return 404;
  - `/session` returns 401 without a token, 401 with an expired, malformed or foreign-key token, 403 with a valid token of a wrong role, 200 with the verified claims otherwise;
  - `/api/identite/sante` is reachable from every subdomain.
  Test tokens are signed with a test key pair supplied through the test environment.
- **Seam 2, network isolation:** from inside each application container, the noyau is unreachable; on the host, HAPI publishes no port. This is the only check outside the HTTP seam, because invariant 5 is only true if a network test proves it.
- The same suite runs locally and against the deployed domain by changing the base domain.
- No unit tests on `commun` in F1: the FHIR client and token verification are exercised through the gateway seam.
- Prior art: none; the repository has no code yet. This suite becomes the prior art for every later feature's service-seam tests.

## Out of Scope

- Agent accounts, login, token issuance, code carnet, the `identite` database (F2).
- The synthetic dataset and tarifs (F2).
- Any domain route: patients, cas, visites, ordonnances, encaissement, délivrance, carnet (F3–F6).
- `AuditEvent` production and the relation de soin (F3).
- The design system: tokens, pictograms, components (F0).
- CI pipelines, monitoring, backups beyond the persistent volume.
- The laboratoire service and application (designed, not built).

## Further Notes

- Canonical references: `SYSTEM_PROMPT.md` (invariants, security statement), `CONTEXT.md` (vocabulary), ADR 0001 (one application per actor). ADR 0002 and 0003 constrain the token claims defined here.
- Open point carried from the technical document: the encaissement resource (`Invoice` vs `PaymentReconciliation`) is decided in F4, not here.
- Local subdomains rely on browsers resolving `*.localhost` to the loopback address; test clients set the `Host` header explicitly.
