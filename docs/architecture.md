# How Lafia works

This page describes the running system as it exists in the repository: what each piece does, what it can reach, and what happens to a request. The reasons behind the design are in `SYSTEM_PROMPT.md` and `docs/adr/`; the plan and its status are in the GitHub issues.

## The pieces

Today the stack runs twelve containers, defined in `docker-compose.yml`. Four actors, soin, caisse, pharmacie and citoyen, each have one application and one service:

| Container | Software | Role | Published port |
|---|---|---|---|
| `passerelle` | Caddy | The only door from outside. Terminates HTTPS, reads the subdomain and the path, forwards the request to the right container. | 80, 443 |
| `application-soin`, `application-caisse`, `application-pharmacie`, `application-citoyen` | Node.js, Next.js | The **application** of one actor (soignants, caissiers, pharmaciens, citoyens): the pages served on `soin.<domaine>`, `caisse.<domaine>`, `pharmacie.<domaine>`, `citoyen.<domaine>`. Its server asks its own service for data, through the gateway. It stores no medical data and never speaks FHIR. | none |
| `soin`, `caisse`, `pharmacie`, `citoyen` | Python, FastAPI | The **service** of one actor: care, cashier, pharmacy, the citoyen's own carnet. Each exposes its own API under `/api/<service>`, and reads and writes medical data by speaking FHIR to the noyau. | none |
| `identite` | Python, FastAPI | The **service** for identity. Exposes its own API under `/api/identite`, reachable from every application's subdomain. It never speaks FHIR and is not on the noyau's network. Today it only reports its health; agent accounts, sign-in and token issuance arrive with F2. | none |
| `noyau` | HAPI FHIR R4 | The **noyau**. Stores all medical data as standard FHIR resources and exposes the standard FHIR REST API. Runs in HAPI's default configuration. | none |
| `base-noyau` | PostgreSQL | Where HAPI keeps its data on disk, in the `noyau-donnees` volume. | none |

`commun/` is not a container. It is a Python library, copied into each service's image when the image is built. Today it holds what every service shares: the service skeleton (the FastAPI application, its `/sante` route and its OpenAPI contract under the service's prefix), the FHIR client every service uses to talk to the noyau, and the token verification every service uses to know who is asking. A service's own code holds only its own routes and rules.

`web/` is not a container either. It is an npm workspace holding the applications (`web/soin/`, `web/caisse/`, `web/pharmacie/`, `web/citoyen/`) and two packages they share. `web/commun/` is to the applications what `commun/` is to the services: how an application reaches its service through the gateway, and the page every application shows today. `web/design/` is the design system. Both are compiled into each application when its image is built, the way `commun/` is copied into each service: nothing of them is loaded at runtime. The design system is empty until F0 fills it; today it only gives the page a legible base stylesheet.

## Two kinds of API

Two different APIs are in play, and keeping them apart explains most of the design.

**The service API** is what an application's server calls, through the gateway. Its routes use Lafia's vocabulary and are shaped for one actor: `/api/soin/sante` today, later `/api/soin/patients?npi=…` or `POST /api/soin/cas`. A service is where Lafia's rules live: who is asking, with which role, whether a relation de soin exists, and which access gets written to the audit trail.

**The FHIR API** is the noyau's. It is the international HL7 FHIR standard: `GET /fhir/metadata`, `GET /fhir/Patient?identifier=…`, `POST /fhir/EpisodeOfCare`. It is generic and knows nothing about roles or Lafia's rules, so only services may call it.

A service translates between the two. It receives a business request, checks who is asking, turns the request into one or more FHIR calls to the noyau, and returns a business answer. For example, opening a cas de visite will become a `POST /api/soin/cas` on the service, which the service turns into a FHIR `EpisodeOfCare` written to the noyau. The FHIR side of that translation lives in `commun/`, so no service reimplements it.

## Following one request

Here is what happens to `GET https://soin.localhost/api/soin/sante`:

```
 client (browser, curl, test suite)
   │ 1. HTTPS to soin.localhost, port 443
   ▼
 passerelle (Caddy)                        network: passerelle
   │ 2. site soin.localhost, path /api/soin/*  →  soin:8000
   ▼
 soin (FastAPI)                            networks: passerelle + noyau
   │ 3. route /api/soin/sante calls ClientFhir.version_fhir()
   │ 4. GET http://noyau:8080/fhir/metadata
   ▼
 noyau (HAPI FHIR)                         network: noyau
   │ 5. answers its CapabilityStatement, fhirVersion 4.0.1
   ▼
 base-noyau (PostgreSQL)
```

1. **Reaching the gateway.** `soin.localhost` means this machine: browsers resolve any `*.localhost` name to `127.0.0.1`. Windows does not do this for other programs, so `curl` and the test suite must be told explicitly (see [Try it yourself](#try-it-yourself)). The host's port 443 belongs to Caddy, the only container that publishes ports. Caddy presents a certificate for `soin.localhost`. Locally, Caddy signs that certificate with its own internal authority; on a real domain it obtains one from a public authority. Plain HTTP on port 80 is redirected (308) to HTTPS.
2. **Routing.** Caddy reads the `Caddyfile`. Every actor gets the same site block, written once as the `acteur` snippet and imported once per actor: `import acteur soin` gives the site `soin.{$LAFIA_DOMAINE}`, which sends `/api/soin/*` to `soin:8000` and `/api/identite/*` to `identite:8000`, answers 404 to any other `/api/*` path, and sends everything else to the application, `application-soin:3000`. `soin` is the container's name, which Docker's internal DNS resolves on the `passerelle` network. Caddy forwards the path unchanged, so the service receives `/api/soin/sante`.
3. **The service.** FastAPI matches the route. Every service gets its `/sante` from `creer_service()` in `commun/src/commun/service.py`, which builds the service's FastAPI app around its own routes. The handler does no FHIR work itself: it asks the FHIR client for the noyau's version.
4. **The FHIR client.** `ClientFhir` in `commun/src/commun/fhir.py` reads the noyau's address from the `NOYAU_URL` environment variable (`http://noyau:8080/fhir`). It sends `GET metadata` with `Accept: application/fhir+json` and waits at most 5 seconds.
5. **The noyau.** HAPI answers with its `CapabilityStatement`, the FHIR resource in which a server describes what it supports. Its `fhirVersion` is `4.0.1`, the number of FHIR R4. The service then builds its JSON answer.

## Reading `/api/soin/sante`

`/sante` checks the whole chain, and each broken link gives a different answer. caisse, pharmacie and citoyen answer the same way under their own prefix, since their `/sante` comes from the same place:

| What you get | Who answers | What it means |
|---|---|---|
| `200` `{"service":"soin","statut":"disponible","noyau":{"statut":"disponible","version_fhir":"4.0.1"}}` | soin | The whole chain works. |
| `503` `{"service":"soin","statut":"indisponible","noyau":{"statut":"injoignable","version_fhir":null}}` | soin | The service runs but cannot reach the noyau: HAPI is stopped or still starting, or its database is down. |
| `502`, no JSON | Caddy | Caddy cannot reach the service: `soin` is down. |
| `404` | Caddy or soin | The path is not routed: Caddy for any `/api/*` path outside `/api/soin/*` and `/api/identite/*`, soin for an unknown route under it. |

`https://soin.localhost/api/identite/sante` answers `{"service":"identite","statut":"disponible"}`: identite reports only its own state, since it has no noyau to reach.

## Who is asking: session tokens

Every protected route answers only to a signed token. Here is what happens to `GET https://soin.localhost/api/soin/session`:

1. **The token travels in a cookie.** Each application's session cookie is named `__Host-session`. Caddy forwards it to the service unchanged. The `__Host-` prefix makes the browser keep the cookie `Secure`, without a `Domain` and on the path `/`, so it goes back only to the subdomain that set it: a caisse cookie never reaches soin. identite will set it `httpOnly` and `SameSite=Strict` when it issues it (F2), so client JavaScript never reads it. Tests and third-party integrators may send the same token in an `Authorization: Bearer` header instead.
2. **The service verifies it alone.** `VerificateurDeJetons` in `commun/src/commun/jeton.py` checks the signature (EdDSA, Ed25519) against the public key in `JETON_CLE_PUBLIQUE`, the expiry, a lifetime of at most one hour, and the claims. The service never calls identite to do so. A token belongs either to an `Agent` (a role and an établissement) or to a `Citoyen` (an NPI), the two kinds of user in `CONTEXT.md`.
3. **The service decides whether it serves that role.** soin serves médecin and infirmier, caisse serves caissier, pharmacie serves pharmacien. Each rule is in the service's own `regles/acces.py`, for instance `services/soin/src/soin/regles/acces.py`, and is enforced by the `agent` guard of `VerificateurDeJetons`. `/api/caisse/session` and `/api/pharmacie/session` behave like soin's, each with its own roles. citoyen serves the citoyen alone: the `citoyen` guard refuses every agent with 403, whatever the role, and `services/citoyen/src/citoyen/regles/acces.py` decides what the service gives back of the citoyen: never the NPI.

A token carries these claims:

| Claim | Content |
|---|---|
| `sub` | The agent's identifier, or the citoyen's |
| `role` | `médecin`, `infirmier`, `caissier`, `pharmacien` or `citoyen` |
| `etablissement` | The id of the agent's `Organization`; absent from a citoyen token |
| `npi` | The citoyen's NPI; only in a citoyen token |
| `exp` | Expiry, minutes after issue; a token expiring more than an hour ahead is refused |

| What you get | What it means |
|---|---|
| `200` `{"sub":"…","role":"médecin","etablissement":"…"}` | A valid token of a soignant. |
| `200` `{"sub":"…","role":"citoyen"}`, from `/api/citoyen/session` | A valid token of a citoyen. The NPI stays in the service, which will use it to choose the carnet it opens (F6); it never goes back to the application, which has no use for it. |
| `401` | No token; or a token that is malformed, expired, valid for more than an hour, signed with another key, unsigned, or whose claims break the format above. |
| `403` | A valid token of a role the service does not serve: for soin, caissier, pharmacien, citoyen; for citoyen, every agent. |

Only identite will hold the private key that signs tokens, from F2 on. A service holds only the public key: it can verify tokens but cannot forge them, even if compromised. Until F2 no one issues real tokens; the test suite signs its own (see [The test suite](#the-test-suite)).

## Following a page

Here is what happens when a browser opens `https://soin.localhost/`:

```
 browser
   │ 1. HTTPS to soin.localhost, path /
   ▼
 passerelle (Caddy), public entry :443
   │ 2. site soin.localhost, not /api/*  →  application-soin:3000
   ▼
 application-soin (Next.js)                network: passerelle only
   │ 3. renders the page; its server needs the service's state
   │ 4. GET http://soin.localhost:8080/api/soin/sante
   ▼
 passerelle (Caddy), internal entry :8080
   │ 5. same site, same rules: /api/soin/*  →  soin:8000
   ▼
 soin  →  noyau                            as in the request above
```

1. **The public request.** The browser reaches Caddy exactly as for `/api/soin/sante`.
2. **To the application.** The path is not under `/api/`, so Caddy forwards it to the Next.js server in `application-soin`.
3. **Rendering on the server.** The page (`web/soin/src/app/page.tsx`) shows `EtatDeLActeur` from `web/commun/src/etat.tsx`, the same page every application shows today with its own title and service. It is rendered on every request, never at build time, so it shows the state of the moment. Nothing runs in the browser to fetch data: the HTML arrives complete.
4. **Back through the gateway.** The application's server asks its service for its state (`web/commun/src/service.ts`). If the browser sent a session cookie, it also asks `/api/soin/session`, passing the cookie on: the application never reads the token itself, the service verifies it. It does not call `soin:8000` directly: it calls the gateway, at the address in `PASSERELLE_URL`, `http://soin.localhost:8080`. On the `passerelle` network, Docker's DNS resolves `soin.localhost` to the `passerelle` container, which carries that name as a network alias.
5. **The internal entry.** Port 8080 is Caddy's internal entry. It speaks plain HTTP, because the request never leaves the `passerelle` network, and no port is published for it on the host. It shares the site block of `soin.localhost`, so an application's server gets exactly the routes its subdomain gets from the outside, and no more. From there the request follows the same path as `/api/soin/sante` above.

The page shows "Soin" ("Caisse", "Pharmacie", "Mon carnet" on the other subdomains), the service's status and the noyau's: `disponible, FHIR 4.0.1` when the whole chain answers. With a session the service accepts, it shows the connected role and, for an agent, the établissement; a citoyen sees `Connecté comme citoyen`, never their NPI, which the page does not receive. Otherwise it shows `Session : aucune`. When the service answers 503, the page shows the noyau as `injoignable`. When the service does not answer at all, the page shows the service as `injoignable` and the noyau as `inconnu`. The page itself always renders, as long as the application runs.

## Who can reach whom

The network layout enforces the architecture rules. Code does not have to remember them.

```
            outside (your machine, the internet)
                         │ 80, 443
 ┌────────────────────────────┼────────────────────────────┐
 │ network passerelle         ▼                            │
 │  application-soin                                       │
 │  application-caisse ──  passerelle  ── identite         │
 │  application-pharmacie      │                           │
 │  application-citoyen        │                           │
 │                             │                           │
 │          soin    caisse    pharmacie    citoyen         │
 │            │        │          │           │            │
 └────────────┼────────┼──────────┼───────────┼────────────┘
 ┌────────────┼────────┼──────────┼───────────┼────────────┐
 │ network    └────────┴────┬─────┴───────────┘  internal: │
 │ noyau                    ▼                  no internet │
 │                        noyau  ──  base-noyau            │
 └─────────────────────────────────────────────────────────┘
```

| From | Can reach | Cannot reach |
|---|---|---|
| Outside | `passerelle`, on 80 and 443 | Anything else: no other container publishes a port, and Caddy's internal entry (8080) is not published either. |
| `passerelle` | The containers the `Caddyfile` routes to | `noyau` and `base-noyau`: Caddy is not on the `noyau` network. |
| `application-soin`, `application-caisse`, `application-pharmacie`, `application-citoyen` | Its own service and `identite`, through the gateway | `noyau`, by name or by address: the application is only on the `passerelle` network. Another actor's service: the gateway answers 404 to `/api/soin/*` on `caisse.<domaine>`, and so on. |
| `soin`, `caisse`, `pharmacie`, `citoyen` | `noyau`, over FHIR | `base-noyau`'s data: only HAPI holds the database password. |
| `identite` | Nothing: it only answers the gateway | `noyau`, by name or by address: identite is only on the `passerelle` network. |
| `noyau` | `base-noyau` | The internet: the `noyau` network is internal. |

The test suite checks the first, third and fifth rows from the machine that runs the stack: only `passerelle` publishes ports, and from inside each application container and `identite` the noyau gives no answer, whether called by its name or by its IP address. Through the gateway, it checks that no subdomain reaches another actor's service.

Two rules are conventions rather than network properties. **Services never call each other**: they share the `passerelle` network, so nothing physically stops one from calling another. **An application calls only the gateway**: it could open a connection to `soin:8000` directly. Both rules are kept in code and review. Going through the gateway keeps a single place, the `Caddyfile`, that decides what each subdomain can reach, for the browser and for the application's server alike.

## Starting up and staying up

`docker compose up -d --build --wait` starts the containers in dependency order:

1. `base-noyau` is healthy once PostgreSQL accepts connections (`pg_isready`).
2. `noyau` starts next. It is healthy once HAPI's own probe, shipped in the official image, reports Spring and its database up. On the very first start HAPI creates its schema, which takes a few minutes.
3. `soin`, `caisse`, `pharmacie` and `citoyen` start once the noyau is healthy. Each is healthy when it answers its own OpenAPI contract, and refuses to start without a readable `JETON_CLE_PUBLIQUE`, except on `localhost` (see [Configuration](#configuration)). `identite` needs nothing to start; it is healthy when it answers its OpenAPI contract too.
4. Each application needs only the gateway to start: it asks its service for its state on each page, not at startup. It is healthy once its server listens.

`--wait` returns when every container is healthy. Each container has `restart: unless-stopped`, so it comes back after a crash or a reboot. Each also has a memory limit, so the whole stack fits on one virtual machine: HAPI gets 2 GB with a 1 GB Java heap, PostgreSQL 512 MB, the gateway 128 MB, each service and each application 256 MB, about 4.9 GB in all.

`docker-compose.yml` writes what services and applications share once. `x-service-fhir` holds what every service that speaks FHIR needs: both networks, a healthy noyau before starting, `NOYAU_URL`, `JETON_CLE_PUBLIQUE` and `LAFIA_DOMAINE`. `x-application` holds what every application needs: the `passerelle` network only, and the gateway before starting. Each service is built by `services/Dockerfile` with its name as `SERVICE`, `commun` included; each application by `web/Dockerfile` with its name as `APPLICATION`.

Docker's health checks and `/sante` answer different questions. Docker checks each container on its own, which tells you which one is broken. `/sante` checks the chain from the outside, which tells you whether a request can get through.

## Configuration

Variables come from a `.env` file at the root, which git ignores. `.env.example` lists them all:

| Variable | Used by | Local default |
|---|---|---|
| `LAFIA_DOMAINE` | Caddy: every application is served on `<application>.<domaine>`. soin, caisse, pharmacie, citoyen: the development key is allowed on `localhost` only | `localhost` |
| `NOYAU_BASE_MOT_DE_PASSE` | PostgreSQL and HAPI | `noyau-local` |
| `JETON_CLE_PUBLIQUE` | soin, caisse, pharmacie, citoyen, to verify tokens: the base64 line of an Ed25519 public key PEM | Empty: the development key, on `localhost` only |

Without a `.env`, the local defaults apply. In production every variable is set in `.env`. The token key is guarded in code: the development key's private half is public in `tests/conftest.py`, so `commun` uses that key only when `LAFIA_DOMAINE` is `localhost` and `JETON_CLE_PUBLIQUE` is empty. On any other domain a service refuses to start without a key, and refuses the development key: a deployed stack never accepts a token anyone can sign. Two addresses are set in `docker-compose.yml` instead, because they are internal: `NOYAU_URL`, where a service finds the noyau, and `PASSERELLE_URL`, where an application's server finds the gateway's internal entry for its subdomain (`http://soin.<domaine>:8080`).

## Try it yourself

```sh
docker compose up -d --build --wait    # start; the first time takes a few minutes
docker compose ps                      # which containers run, which are healthy
curl -k --resolve soin.localhost:443:127.0.0.1 https://soin.localhost/api/soin/sante
curl -k --resolve soin.localhost:443:127.0.0.1 https://soin.localhost/    # the soin page
curl -k --resolve soin.localhost:443:127.0.0.1 https://soin.localhost/api/identite/sante
curl -k --resolve soin.localhost:443:127.0.0.1 https://soin.localhost/api/soin/session    # 401: no token
curl -k --resolve caisse.localhost:443:127.0.0.1 https://caisse.localhost/    # the caisse page
curl -k --resolve caisse.localhost:443:127.0.0.1 https://caisse.localhost/api/soin/sante    # 404: not caisse's service
curl -k --resolve citoyen.localhost:443:127.0.0.1 https://citoyen.localhost/    # the citoyen page, Mon carnet
docker compose logs -f soin            # follow a container's log
docker compose stop noyau              # watch /sante turn into a 503 …
docker compose start noyau             # … and back
uv run --project tests pytest tests    # the black-box suite
docker compose down                    # stop and keep the data (down -v erases it)
```

In Windows PowerShell 5, type `curl.exe`, because `curl` is an alias for another command there. `-k` skips certificate checks; `--resolve` points the subdomain at this machine.

In a browser, open `https://soin.localhost` for the soin application, and `https://soin.localhost/api/soin/docs` for the service's documentation. The documentation lists every route, its answers, and a *Try it out* button. The browser warns about the certificate until you trust Caddy's local authority, whose root is at `/data/caddy/pki/authorities/local/root.crt` in the `passerelle` container.

## The test suite

`tests/` holds a black-box suite. It talks to the stack only through the gateway, as a user or an attacker would, and asserts what they can observe: status codes, JSON bodies, and the text of pages.

- Each application is addressed by its subdomain. Locally, the suite connects to `127.0.0.1` and sends the subdomain as the requested host.
- Certificates are verified. Locally, the suite first reads Caddy's root certificate from the `passerelle` container; elsewhere, it uses the public authorities.
- `LAFIA_DOMAINE=<domaine>` points the same suite at another deployment.
- The suite signs its own tokens with the private key in `JETON_CLE_PRIVEE`, whose public half the targeted stack holds. Locally, without it, the suite uses the development key, which a stack served on `localhost` accepts when it has no key of its own. Against another deployment, without it, the tests that need a token are skipped.
- `tests/test_acteurs.py` runs the same checks for every actor, from one table: each actor's title and the roles its service serves. Session tests take every admitted agent role, every refused role and every invalid token, each by cookie and by `Authorization` header; the cross-actor test asks each subdomain for every other actor's `/sante` and expects 404. `tests/test_citoyen.py` holds what only the citoyen has: a session without the NPI, and a page that never contains it, anywhere in its HTML.
- Network isolation cannot be seen through the gateway, so `tests/test_isolement.py` checks it with `docker`, on the machine that runs the stack: it reads which ports each container publishes, and sends HTTP probes from inside each application container. Each probe first reaches the gateway, so a probe that cannot run is never mistaken for an unreachable noyau. These checks run only when the stack on this machine is the one the suite targets, that is when its gateway serves `LAFIA_DOMAINE`; otherwise they are skipped, since this machine's containers would say nothing about the stack under test.

## Where the code is

| File | What it holds |
|---|---|
| `docker-compose.yml` | Containers, networks, volumes, health checks, memory limits |
| `Caddyfile` | Routing: the `acteur` site block, imported once per actor, publicly and on the internal entry |
| `commun/src/commun/service.py` | `creer_service()`: a service's FastAPI app, its `/sante` and its OpenAPI contract under `/api/<service>`; `client_fhir`, the dependency that hands a route the noyau's client |
| `commun/src/commun/fhir.py` | `ClientFhir`: the only way a service talks to the noyau |
| `commun/src/commun/jeton.py` | `VerificateurDeJetons`: token verification, the `porteur` dependency returning the verified `Agent` or `Citoyen`, the `agent` role guard, and the `citoyen` guard |
| `services/<service>/src/<service>/service.py` | A service's own routes, `/session` today, handed to `creer_service()` |
| `services/<service>/src/<service>/regles/acces.py` | Who a service serves: the roles soin, caisse and pharmacie admit; for citoyen, what the service gives back of the citoyen, never the NPI |
| `services/identite/` | The `identite` service: only `/sante` until F2 |
| `services/Dockerfile` | One image per service, `commun` included, with its health probe: `docker build --build-arg SERVICE=soin --build-context commun=commun services` |
| `web/package.json` | The npm workspace: the applications and the two shared packages |
| `web/commun/src/service.ts` | How an application asks its service, through the gateway: its state, and the session of the cookie |
| `web/commun/src/etat.tsx` | `EtatDeLActeur`: the page every application shows today, rendered on the server at each request |
| `web/design/` | The design system package, compiled into each application |
| `web/<acteur>/src/app/` | An application's pages and layout: its title, and `EtatDeLActeur` with its own service |
| `web/Dockerfile` | One image per application: `docker build --build-arg APPLICATION=soin web` |
| `tests/` | The black-box suite, how it reaches the gateway, the actor table, and the network isolation checks |

## How the picture grows

Every later feature repeats the same pattern:

- **The application of an actor** is a Next.js workspace in `web/<acteur>/`, built by `web/Dockerfile` into a container that merges `x-application`: the `passerelle` network only. It gets `@lafia/commun` and `@lafia/design` compiled in. The gateway carries its subdomain as a network alias so the application's server reaches the internal entry. It calls its own service and `identite` through the gateway, and never FHIR.
- **The service of an actor** is `services/<acteur>/`: its routes, handed to `creer_service()` from `commun`, and its `regles/`, which say whom it serves, enforced with the guards of `VerificateurDeJetons`: `agent` with the roles it admits, or `citoyen`. `services/Dockerfile` builds it with `commun`; if it speaks FHIR, its Compose entry merges `x-service-fhir`, which puts it on both networks and gives it `NOYAU_URL`, `JETON_CLE_PUBLIQUE` and `LAFIA_DOMAINE`.
- **A new actor** (a laboratoire, later) means one service, one application, and one line in the `Caddyfile`, `import acteur <nom>`, which routes `/api/<nom>/*` to its service, `/api/identite/*` to identite, and nothing else under `/api/`. The test suite gains one row in the actor table of `tests/test_acteurs.py`, its subdomain in `tests/test_identite.py`, and its application in the isolation probes of `tests/test_isolement.py`. Nothing existing changes.
- **Deployment** runs the same stack on a virtual machine, with `LAFIA_DOMAINE` set to the real domain.
