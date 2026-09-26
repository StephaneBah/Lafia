# Lafia

Interoperable foundation for Benin's national digital health record: one FHIR core, the **noyau**, holds all medical data; independent domain services read and write it; each actor has its own application on its own subdomain. The brief and the architecture invariants are in `SYSTEM_PROMPT.md`, the vocabulary in `CONTEXT.md`. How the running system works, piece by piece and request by request, is in `docs/architecture.md`.

## Run the stack

Requires Docker with Compose v2. From a clean clone:

```sh
docker compose up -d --build --wait
```

The first start takes a few minutes while HAPI creates its schema. Then each actor's application is served on its own subdomain: `https://soin.localhost`, `https://caisse.localhost`, `https://pharmacie.localhost` and `https://citoyen.localhost`. Each page shows its service's status, the noyau's FHIR version and, with a session cookie, the connected role, with the établissement for an agent; a citoyen's page never shows their NPI. On each subdomain, `/api/<actor>/sante` reports the same as JSON (for instance `https://caisse.localhost/api/caisse/sante`), the service's OpenAPI documentation is at `/api/<actor>/docs`, and `/api/identite/sante` reaches the identite service. Any other `/api/*` path answers 404: `caisse.localhost` has no route to soin's service.

Locally, the gateway signs `*.localhost` certificates with Caddy's internal authority, so a browser warns until you trust its root, found in the `passerelle` container at `/data/caddy/pki/authorities/local/root.crt`.

At every start, the `chargement` container writes the synthetic demo dataset from `donnees/` into the noyau (établissements, officines, agents, patients, tarifs), then exits. It never deletes anything, so a restart or a redeploy keeps what users created. The noyau's data lives in the `noyau-donnees` volume: `docker compose down` keeps it. To start over from the demo dataset alone:

```sh
docker compose down -v && docker compose up -d --build --wait
```

## Deploy

The live stack runs on an Azure VM and serves `https://soin.lafia.stephanebah.page`, `https://caisse.lafia.stephanebah.page`, `https://pharmacie.lafia.stephanebah.page` and `https://citoyen.lafia.stephanebah.page`. A wildcard DNS record points `*.lafia.stephanebah.page` at the VM; its firewall opens 80 and 443, and SSH to the operator only.

Each deploy of the current `main`, from your machine:

```sh
ssh -i <vm-key.pem> azureuser@lafia.stephanebah.page lafia/deploiement/deployer.sh
```

Setting up a server from scratch, checking a deployment and fixing common failures: `docs/deploiement.md`.

## Configuration

`.env.example` lists every variable. Without a `.env`, the stack runs on local development values; in production, copy the example to `.env` (git-ignored) and set every value. `JETON_CLE_PUBLIQUE` may stay empty on `localhost` only, where services fall back to the development key; on any other domain they refuse to start without a key of their own.

## Web workspace

The applications, the code they share (`web/commun/`) and the design system (`web/design/`) form an npm workspace in `web/`, on Node.js 22. Compose builds each application's image on its own; to work on the code:

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

The network isolation checks (`tests/test_isolement.py`) and the dataset checks (`tests/test_donnees.py`) use `docker` on the machine that runs the targeted stack, and are skipped when that stack runs elsewhere.

The same suite checks another deployment by changing the base domain: `LAFIA_DOMAINE=<domaine> uv run --project tests pytest tests`. Locally it connects to `127.0.0.1` and trusts Caddy's internal authority; `LAFIA_ADRESSE` forces the gateway's IP address elsewhere, for instance before DNS is in place.

The suite signs its own session tokens with `JETON_CLE_PRIVEE`, the private half of the targeted stack's `JETON_CLE_PUBLIQUE`, as the base64 line of its PEM. Locally it defaults to the development key, whose private half is public in `tests/conftest.py`; elsewhere, without it, the tests that need a token are skipped. Against the live stack, it is read from the VM's `.env` (`docs/deploiement.md`, Check).

## Layout

```
Caddyfile            gateway: one subdomain per actor, one `import acteur <name>` line each
docker-compose.yml   the stack: gateway, noyau, dataset loader, services, applications
deploiement/         preparing the VM once, deploying main to it
commun/              shared library, built into each service image: service skeleton, token verification, FHIR client and translation
services/<name>/     one FastAPI service per domain: soin, caisse, pharmacie, citoyen, identite
services/Dockerfile  one image per service, commun included
donnees/             the synthetic demo dataset, in Lafia's vocabulary, and the loader that writes it into the noyau
web/commun/          shared application code, built into each application: service through the gateway, status page
web/design/          design system, built into each application
web/<acteur>/        one Next.js application per actor: soin, caisse, pharmacie, citoyen
tests/               black-box suite through the gateway, one table of actors, network isolation and dataset checks
docs/                how it works (architecture.md), deploying (deploiement.md), specs, ADRs
```
