# Lafia

Interoperable foundation for Benin's national digital health record: one FHIR core, the **noyau**, holds all medical data; independent domain services read and write it; each actor has its own application on its own subdomain. The brief and the architecture invariants are in `SYSTEM_PROMPT.md`, the vocabulary in `CONTEXT.md`. How the running system works, piece by piece and request by request, is in `docs/architecture.md`.

## Run the stack

Requires Docker with Compose v2. From a clean clone:

```sh
docker compose up -d --build --wait
```

The first start takes a few minutes while HAPI creates its schema. Then `https://soin.localhost/api/soin/sante` reports the noyau's FHIR version, and the service's OpenAPI documentation is at `https://soin.localhost/api/soin/docs`.

Locally, the gateway signs `*.localhost` certificates with Caddy's internal authority, so a browser warns until you trust its root, found in the `passerelle` container at `/data/caddy/pki/authorities/local/root.crt`.

The noyau's data lives in the `noyau-donnees` volume: `docker compose down` keeps it, `docker compose down -v` erases it.

## Configuration

`.env.example` lists every variable. Without a `.env`, the stack runs on local development values; in production, copy the example to `.env` (git-ignored) and set every value.

## Tests

A black-box suite runs against the running stack through the gateway, addressing each application by its subdomain. It needs [uv](https://docs.astral.sh/uv/):

```sh
uv run --project tests pytest tests
```

The same suite checks another deployment by changing the base domain: `LAFIA_DOMAINE=<domaine> uv run --project tests pytest tests`. Locally it connects to `127.0.0.1` and trusts Caddy's internal authority; `LAFIA_ADRESSE` forces the gateway's IP address elsewhere, for instance before DNS is in place.

## Layout

```
Caddyfile            gateway: one subdomain per application
docker-compose.yml   the stack: gateway, noyau, services
commun/              shared library, built into each service image: FHIR client
services/<name>/     one FastAPI service per domain: soin, …
tests/               black-box suite through the gateway
docs/                how it works (architecture.md), specs, ADRs
```
