<p align="center"><img src="web/design/assets/Logo/lafia-logo.svg" alt="Lafia" width="180"></p>

<p align="center"><strong>The foundation of Benin's national digital health record.</strong><br>
One record per citizen, found by their NPI alone, that follows the person from the health centre to the cashier, the pharmacy and their own phone.</p>

<p align="center"><a href="https://lafia.stephanebah.page">lafia.stephanebah.page</a></p>

---

Today a Beninese citizen's medical memory is scattered: the paper booklet gets lost, each facility keeps its own register, a lab result exists as one physical copy, and the patient is the only link between their carers. Lafia is not one more application on top of that problem. It is the ground applications stand on: one core that holds medical data in an international standard, one contract that decides who reaches what, and services that plug into both.

## The foundation

![The FHIR noyau at the centre; around it, the contract that decides who reaches what; today's and tomorrow's services plug into it; one door to the outside.](docs/fondation.svg)

**The noyau.** Every medical fact lives in one place: each visite, mesure, diagnostic, ordonnance, délivrance, and each access to the record, as a standard **HL7 FHIR R4** resource in an unmodified HAPI FHIR server. The patient is identified by their NPI; Lafia invents no identifier of its own. Records are append-only: a correction is a new version, and history stays readable. The noyau publishes no port and has no route to the internet; no application can reach it.

**The contract.** Between the noyau and anyone who wants its data stand the same four rules, enforced by every service:

- **Signed tokens.** identite alone holds the signing key. Each service verifies a token by itself, with the public key: a compromised service cannot forge one.
- **Least privilege.** Each role reaches what its work needs. The caissier sees an ordonnance and its amounts, never the diagnostic; the pharmacien sees the paid lines and the allergies.
- **Relation de soin.** A soignant opens a dossier only when their établissement is treating that patient. A vital emergency opens it anyway, with a stated reason.
- **Every access traced.** Each read or write of a dossier writes an `AuditEvent` into the noyau, and the citoyen sees in their own carnet who opened it, and when.

**The services.** Each actor has its own service and its own application, on its own subdomain. A service translates its actor's work into FHIR; services never call each other. The only door from outside is the gateway, which sends each subdomain to its own service and nothing else. The network enforces this, and the test suite checks it.

## Built to grow

Four actors run on the foundation today:

| Service | For | What it does |
|---|---|---|
| **soin** | médecins, infirmiers | Find a patient by NPI, follow the cas de visite, write the visite, issue the ordonnance |
| **caisse** | caissiers | Open an ordonnance by its numéro, collect payment without re-typing a line |
| **pharmacie** | pharmaciens, officines | Hand over the paid lines, stop on an allergy, record a partial délivrance |
| **citoyen** | citoyens | A carnet that reads in pictures, and the journal of who opened the dossier |
| **numerisation** | agents de numérisation | At a desk, turn a citoyen's paper medical past into Documents of their dossier, after checking an identity document |
| **relecture** | agents de relecture, soignants | Triage numérised Documents without knowing whose they are, then validate the facts a machine reading proposes (today an Extraction de démonstration) |
| **identite** | everyone | Sign-in, signed session tokens, the code carnet printed on each reçu |

Tomorrow's services join the same way: one service that speaks FHIR to the noyau, one application, one line in the gateway. No data is copied, no database is added, no existing code changes.

- **Laboratoire**: results filed straight into the cas de visite, without paper.
- **Télémédecine**: a remote visite, kept in the same cas.
- **Assistant IA de compte rendu**: the soignant dictates, the assistant drafts the visite; nothing is saved without the soignant's approval.
- **Paiement différé**: care first for vital emergencies, payment settled later.
- **Lafia Insights**: dashboards for the ministry and the ARS, computed on anonymised extracts, never on the live record.

Nothing in the critical path depends on a cloud provider: the whole stack is Docker Compose on one virtual machine, ready to be hosted on the State's own infrastructure.

## Read further

- [`docs/architecture.md`](docs/architecture.md): how the running system works, piece by piece and request by request.
- [`docs/adr/`](docs/adr/): the decisions that are hard to reverse, and why.
- [`SYSTEM_PROMPT.md`](SYSTEM_PROMPT.md): the brief, the architecture invariants and the health-data security statement.
- [`CONTEXT.md`](CONTEXT.md): the vocabulary, from cas de visite to relation de soin.
- [`docs/design/charte-graphique.md`](docs/design/charte-graphique.md): the design system, made to be understood without reading.

All data in the repository and on the live platform is synthetic.

## Run the stack

Requires Docker with Compose v2. From a clean clone:

```sh
docker compose up -d --build --wait
```

The first start takes a few minutes while HAPI creates its schema. The product site is then served on `https://localhost`, with a door to each application and its demo accounts, and each application on its own subdomain: `https://soin.localhost`, `https://caisse.localhost`, `https://pharmacie.localhost`, `https://citoyen.localhost`, `https://numerisation.localhost`, `https://relecture.localhost`. On soin, caisse, pharmacie, numerisation and relecture, `/connexion` lists the demo accounts with their mots de passe. On each subdomain, `/api/<actor>/sante` reports the state of the service and the noyau, `/api/<actor>/docs` is the service's OpenAPI documentation, and `/api/identite/sante` reaches identite. Any other `/api/*` path answers 404: `caisse.localhost` has no route to soin's service.

Locally, the gateway signs `*.localhost` certificates with Caddy's internal authority, so a browser warns until you trust its root, found in the `passerelle` container at `/data/caddy/pki/authorities/local/root.crt`.

At every start, the `chargement` container writes the synthetic dataset from `donnees/` into the noyau (établissements, officines, agents, patients, tarifs, a clinical history), then exits, and identite loads the demo accounts and codes carnet from the same files. Neither deletes anything, so a restart or a redeploy keeps what users created; `docker compose down` keeps the `noyau-donnees` and `identite-donnees` volumes. To start over from the dataset alone:

```sh
docker compose down -v && docker compose up -d --build --wait
```

## Deploy

The live stack runs on an Azure VM and serves the product site on `https://lafia.stephanebah.page` and the applications on `https://soin.lafia.stephanebah.page`, `https://caisse.…`, `https://pharmacie.…`, `https://citoyen.…`, `https://numerisation.…` and `https://relecture.…`. A DNS record for the domain and a wildcard for its subdomains point at the VM; its firewall opens 80 and 443, and SSH to the operator only.

Each deploy of the current `main`, from your machine:

```sh
ssh -i <vm-key.pem> azureuser@lafia.stephanebah.page lafia/deploiement/deployer.sh
```

Setting up a server from scratch, checking a deployment and fixing common failures: `docs/deploiement.md`.

## Configuration

`.env.example` lists every variable. Without a `.env`, the stack runs on local development values; in production, `deploiement/preparer-vm.sh` writes `.env` (git-ignored) with every value. `JETON_CLE_PRIVEE`, which identite alone reads to sign tokens, and `JETON_CLE_PUBLIQUE`, which services read to verify them, may stay empty on `localhost` only, where both sides fall back to the development key pair; on any other domain they refuse to start without a key of their own.

## Web workspace

The applications, the code they share (`web/commun/`) and the design system (`web/design/`) form an npm workspace in `web/`, on Node.js 22. Compose builds each application's image on its own; to work on the code:

```sh
cd web
npm install
npm run typecheck    # every package
npm run build        # every application, as Next.js standalone output
```

## Tests

A black-box suite runs against the running stack through the gateway, as a user or an attacker would, addressing each application by its subdomain. It needs [uv](https://docs.astral.sh/uv/):

```sh
uv run --project tests pytest tests
```

The network isolation checks (`tests/test_isolement.py`) and the dataset checks (`tests/test_donnees.py`) use `docker` on the machine that runs the targeted stack, and are skipped when that stack runs elsewhere.

The same suite checks another deployment by changing the base domain: `LAFIA_DOMAINE=<domaine> uv run --project tests pytest tests`. Locally it connects to `127.0.0.1` and trusts Caddy's internal authority; `LAFIA_ADRESSE` forces the gateway's IP address elsewhere, for instance before DNS is in place.

The suite gets its session tokens by signing in with the demo accounts, read from `donnees/`: it never holds a deployment's private key. Tokens of a wrong shape are forged with the development key, which only a stack served on `localhost` accepts; those tests are skipped elsewhere. Lockout tests use accounts and NPIs reserved for them, never listed on a sign-in page.

Each run counts about twenty failed sign-ins against the machine's address, and identite refuses an address after 50 within 15 minutes: a third run within 15 minutes fails. Locally, clear the counters first:

```sh
docker compose exec base-identite psql -U identite -c "TRUNCATE tentative"
```

## Layout

```
Caddyfile            gateway: one subdomain per actor, one `import acteur <name>` line each
docker-compose.yml   the stack: gateway, noyau, dataset loader, services, identite's database, applications
deploiement/         preparing the VM once, deploying main to it
commun/              shared library, built into each service image: service skeleton, token contract and verification, FHIR client and translation
services/<name>/     one FastAPI service per domain: soin, caisse, pharmacie, citoyen, numerisation, relecture, identite; extraction, internal
services/Dockerfile  one image per service, commun included
donnees/             the synthetic dataset, in Lafia's vocabulary, and the loader that writes it into the noyau; identite reads its accounts from it
web/commun/          shared application code, built into each application: service and identite through the gateway, sign-in page, token renewal
web/design/          design system, built into each application
web/<acteur>/        one Next.js application per actor: soin, caisse, pharmacie, citoyen, numerisation, relecture
web/site/            the product site, on the domain itself; calls no service
tests/               black-box suite through the gateway, one table of actors, network isolation and dataset checks
docs/                how it works (architecture.md), deploying (deploiement.md), specs, ADRs, design
```
