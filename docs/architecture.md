# How Lafia works

This page describes the running system as it exists in the repository: what each piece does, what it can reach, and what happens to a request. The reasons behind the design are in `SYSTEM_PROMPT.md` and `docs/adr/`; the plan and its status are in the GitHub issues.

## The pieces

Today the stack runs four containers, defined in `docker-compose.yml`:

| Container | Software | Role | Published port |
|---|---|---|---|
| `passerelle` | Caddy | The only door from outside. Terminates HTTPS, reads the subdomain and the path, forwards the request to the right container. | 80, 443 |
| `soin` | Python, FastAPI | The **service** for care. Exposes its own API under `/api/soin`, and reads and writes medical data by speaking FHIR to the noyau. | none |
| `noyau` | HAPI FHIR R4 | The **noyau**. Stores all medical data as standard FHIR resources and exposes the standard FHIR REST API. Runs in HAPI's default configuration. | none |
| `base-noyau` | PostgreSQL | Where HAPI keeps its data on disk, in the `noyau-donnees` volume. | none |

`commun/` is not a container. It is a Python library, copied into each service's image when the image is built. Today it holds the FHIR client every service uses to talk to the noyau.

Still to come: the `soin` application (Next.js), the `identite` service, and the `caisse`, `pharmacie` and `citoyen` services, each with its application.

## Two kinds of API

Two different APIs are in play, and keeping them apart explains most of the design.

**The service API** is what an application calls. Its routes use Lafia's vocabulary and are shaped for one actor: `/api/soin/sante` today, later `/api/soin/patients?npi=…` or `POST /api/soin/cas`. A service is where Lafia's rules live: who is asking, with which role, whether a relation de soin exists, and which access gets written to the audit trail.

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
2. **Routing.** Caddy reads the `Caddyfile`. The site block `soin.{$LAFIA_DOMAINE}` sends `/api/soin/*` to `soin:8000` and answers 404 to everything else. `soin` is the container's name, which Docker's internal DNS resolves on the `passerelle` network. Caddy forwards the path unchanged, so the service receives `/api/soin/sante`.
3. **The service.** FastAPI matches the route in `services/soin/src/soin/service.py`. The handler does no FHIR work itself: it asks the FHIR client for the noyau's version.
4. **The FHIR client.** `ClientFhir` in `commun/src/commun/fhir.py` reads the noyau's address from the `NOYAU_URL` environment variable (`http://noyau:8080/fhir`). It sends `GET metadata` with `Accept: application/fhir+json` and waits at most 5 seconds.
5. **The noyau.** HAPI answers with its `CapabilityStatement`, the FHIR resource in which a server describes what it supports. Its `fhirVersion` is `4.0.1`, the number of FHIR R4. The service then builds its JSON answer.

## Reading `/api/soin/sante`

`/sante` checks the whole chain, and each broken link gives a different answer:

| What you get | Who answers | What it means |
|---|---|---|
| `200` `{"service":"soin","statut":"disponible","noyau":{"statut":"disponible","version_fhir":"4.0.1"}}` | soin | The whole chain works. |
| `503` `{"service":"soin","statut":"indisponible","noyau":{"statut":"injoignable","version_fhir":null}}` | soin | The service runs but cannot reach the noyau: HAPI is stopped or still starting, or its database is down. |
| `502`, no JSON | Caddy | Caddy cannot reach the service: `soin` is down. |
| `404` | Caddy or soin | The path is not routed: Caddy for anything outside `/api/soin/*`, soin for an unknown route under it. |

## Who can reach whom

The network layout enforces the architecture rules. Code does not have to remember them.

```
            outside (your machine, the internet)
                         │ 80, 443
 ┌───────────────────────┼───────────────────────┐
 │ network passerelle    ▼                       │
 │                  passerelle                   │
 │                       │                       │
 │                     soin      (later: identite, caisse, pharmacie,
 │                       │        citoyen, and the four applications)
 └───────────────────────┼───────────────────────┘
 ┌───────────────────────┼───────────────────────┐
 │ network noyau         ▼          internal:    │
 │                     noyau  ──  base-noyau     │
 │                                no internet    │
 └───────────────────────────────────────────────┘
```

| From | Can reach | Cannot reach |
|---|---|---|
| Outside | `passerelle`, on 80 and 443 | Anything else: no other container publishes a port. |
| `passerelle` | The containers the `Caddyfile` routes to | `noyau` and `base-noyau`: Caddy is not on the `noyau` network. |
| `soin` | `noyau`, over FHIR | `base-noyau`'s data: only HAPI holds the database password. |
| `noyau` | `base-noyau` | The internet: the `noyau` network is internal. |
| An application (to come) | Its own service and `identite`, through the gateway | `noyau`: applications are only on the `passerelle` network. |

One rule is a convention rather than a network property: **services never call each other**. They share the `passerelle` network, so nothing physically stops one from calling another; the rule is kept in code and review.

## Starting up and staying up

`docker compose up -d --build --wait` starts the containers in dependency order:

1. `base-noyau` is healthy once PostgreSQL accepts connections (`pg_isready`).
2. `noyau` starts next. It is healthy once HAPI's own probe, shipped in the official image, reports Spring and its database up. On the very first start HAPI creates its schema, which takes a few minutes.
3. `soin` starts once the noyau is healthy. It is healthy when it answers its own OpenAPI contract.

`--wait` returns when every container is healthy. Each container has `restart: unless-stopped`, so it comes back after a crash or a reboot. Each also has a memory limit, so the whole stack fits on one virtual machine: HAPI gets 2 GB with a 1 GB Java heap.

Docker's health checks and `/sante` answer different questions. Docker checks each container on its own, which tells you which one is broken. `/sante` checks the chain from the outside, which tells you whether a request can get through.

## Configuration

Variables come from a `.env` file at the root, which git ignores. `.env.example` lists them all:

| Variable | Used by | Local default |
|---|---|---|
| `LAFIA_DOMAINE` | Caddy: every application is served on `<application>.<domaine>` | `localhost` |
| `NOYAU_BASE_MOT_DE_PASSE` | PostgreSQL and HAPI | `noyau-local` |

Without a `.env`, the local defaults apply. In production every variable is set in `.env`. `NOYAU_URL` is set in `docker-compose.yml`: it is an internal address that never changes between deployments.

## Try it yourself

```sh
docker compose up -d --build --wait    # start; the first time takes a few minutes
docker compose ps                      # which containers run, which are healthy
curl -k --resolve soin.localhost:443:127.0.0.1 https://soin.localhost/api/soin/sante
docker compose logs -f soin            # follow a container's log
docker compose stop noyau              # watch /sante turn into a 503 …
docker compose start noyau             # … and back
uv run --project tests pytest tests    # the black-box suite
docker compose down                    # stop and keep the data (down -v erases it)
```

In Windows PowerShell 5, type `curl.exe`, because `curl` is an alias for another command there. `-k` skips certificate checks; `--resolve` points `soin.localhost` at this machine.

In a browser, open `https://soin.localhost/api/soin/docs`. This is the service's OpenAPI documentation: every route, its answers, and a *Try it out* button. The browser warns about the certificate until you trust Caddy's local authority, whose root is at `/data/caddy/pki/authorities/local/root.crt` in the `passerelle` container.

## The test suite

`tests/` holds a black-box suite. It talks to the stack only through the gateway, as a user or an attacker would, and asserts what they can observe: status codes and JSON bodies.

- Each application is addressed by its subdomain. Locally, the suite connects to `127.0.0.1` and sends the subdomain as the requested host.
- Certificates are verified. Locally, the suite first reads Caddy's root certificate from the `passerelle` container; elsewhere, it uses the public authorities.
- `LAFIA_DOMAINE=<domaine>` points the same suite at another deployment.

## Where the code is

| File | What it holds |
|---|---|
| `docker-compose.yml` | Containers, networks, volumes, health checks, memory limits |
| `Caddyfile` | Routing: which subdomain and path go to which container |
| `commun/src/commun/fhir.py` | `ClientFhir`: the only way a service talks to the noyau |
| `services/soin/src/soin/service.py` | The `soin` FastAPI application and its `/sante` route |
| `services/soin/Dockerfile` | The `soin` image: `commun` and `soin` installed, health probe |
| `tests/` | The black-box suite and how it reaches the gateway |

## How the picture grows

Every later feature repeats the same pattern:

- **The application of an actor** is a Next.js container on the `passerelle` network. Caddy sends its subdomain's non-API paths to it. It calls its own service and `identite` through the gateway, and never FHIR.
- **A new service** is a FastAPI container built with `commun`, on both networks if it speaks FHIR. The actor's site block in the `Caddyfile` gains an `/api/<service>/*` route to it.
- **A new actor** (caisse, pharmacie, citoyen, later a laboratoire) means one service, one application and one new site block in the `Caddyfile`. Nothing existing changes.
- **Deployment** runs the same stack on a virtual machine, with `LAFIA_DOMAINE` set to the real domain.
