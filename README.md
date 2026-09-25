# Lafia

Interoperable foundation for Benin's national digital health record: one FHIR core, the **noyau**, holds all medical data; independent domain services read and write it; each actor has its own application on its own subdomain. The brief and the architecture invariants are in `SYSTEM_PROMPT.md`, the vocabulary in `CONTEXT.md`. How the running system works, piece by piece and request by request, is in `docs/architecture.md`.

## Run the stack

Requires Docker with Compose v2. From a clean clone:

```sh
docker compose up -d --build --wait
```

The first start takes a few minutes while HAPI creates its schema. Then `https://soin.localhost` serves the soin application, showing its service's status, the noyau's FHIR version and, with a session cookie, the connected role and établissement; `https://soin.localhost/api/soin/sante` reports the same as JSON, and the service's OpenAPI documentation is at `https://soin.localhost/api/soin/docs`. `https://soin.localhost/api/identite/sante` reaches the identite service.

Locally, the gateway signs `*.localhost` certificates with Caddy's internal authority, so a browser warns until you trust its root, found in the `passerelle` container at `/data/caddy/pki/authorities/local/root.crt`.

The noyau's data lives in the `noyau-donnees` volume: `docker compose down` keeps it, `docker compose down -v` erases it.

## Configuration

`.env.example` lists every variable. Without a `.env`, the stack runs on local development values; in production, copy the example to `.env` (git-ignored) and set every value. `JETON_CLE_PUBLIQUE` may stay empty on `localhost` only, where services fall back to the development key; on any other domain they refuse to start without a key of their own.

## Web workspace

The applications and the design system form an npm workspace in `web/`, on Node.js 22. Compose builds each application's image on its own; to work on the code:

```sh
cd web
npm install
npm run typecheck    # every package
npm run build        # every application, as Next.js standalone output
```

## Tests

A black-box suite runs against the running stack through the gateway, addressing each application by its subdomain. It needs [uv](https://docs.astral.sh/uv/):

```sh
uv run --project tests pytest tests
```

The network isolation checks (`tests/test_isolement.py`) use `docker` on the machine that runs the targeted stack, and are skipped when that stack runs elsewhere.

The same suite checks another deployment by changing the base domain: `LAFIA_DOMAINE=<domaine> uv run --project tests pytest tests`. Locally it connects to `127.0.0.1` and trusts Caddy's internal authority; `LAFIA_ADRESSE` forces the gateway's IP address elsewhere, for instance before DNS is in place.

The suite signs its own session tokens with `JETON_CLE_PRIVEE`, the private half of the targeted stack's `JETON_CLE_PUBLIQUE`, as the base64 line of its PEM. Locally it defaults to the development key, whose private half is public in `tests/conftest.py`; elsewhere, without it, the tests that need a token are skipped.

## Layout

```
Caddyfile            gateway: one subdomain per application
docker-compose.yml   the stack: gateway, noyau, services, applications
commun/              shared library, built into each service image: FHIR client, token verification
services/<name>/     one FastAPI service per domain: soin, identite, …
web/design/          design system, built into each application
web/<acteur>/        one Next.js application per actor: soin, …
tests/               black-box suite through the gateway, network isolation checks
docs/                how it works (architecture.md), specs, ADRs
```
