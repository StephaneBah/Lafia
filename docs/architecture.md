# How Lafia works

This page describes the running system as it exists in the repository: what each piece does, what it can reach, and what happens to a request. The reasons behind the design are in `SYSTEM_PROMPT.md` and `docs/adr/`; the plan and its status are in the GitHub issues.

## The pieces

Today the stack runs fourteen containers, defined in `docker-compose.yml`, and a fifteenth that loads the demo dataset at each start, then stops. Four actors, soin, caisse, pharmacie and citoyen, each have one application and one service; the product site, on the domain itself, has neither service nor data:

| Container | Software | Role | Published port |
|---|---|---|---|
| `passerelle` | Caddy | The only door from outside. Terminates HTTPS, reads the subdomain and the path, forwards the request to the right container. | 80, 443 |
| `application-soin`, `application-caisse`, `application-pharmacie`, `application-citoyen` | Node.js, Next.js | The **application** of one actor (soignants, caissiers, pharmaciens, citoyens): the pages served on `soin.<domaine>`, `caisse.<domaine>`, `pharmacie.<domaine>`, `citoyen.<domaine>`. Its server asks its own service for data, through the gateway. It stores no medical data and never speaks FHIR. | none |
| `application-site` | Node.js, Next.js | The **product site**, served on the domain itself (`<domaine>`): what Lafia changes, how it is designed, a door to each application with a few of its demo accounts, and the services to come. It calls no service, not even identite: its only setting is the domain, for its links. | none |
| `soin`, `caisse`, `pharmacie`, `citoyen` | Python, FastAPI | The **service** of one actor: care, cashier, pharmacy, the citoyen's own carnet. Each exposes its own API under `/api/<service>`, and reads and writes medical data by speaking FHIR to the noyau. | none |
| `identite` | Python, FastAPI | The **service** for identity. Signs agents, officines and citoyens in, issues the session tokens every service verifies, and issues codes carnet. Exposes its own API under `/api/identite`, reachable from every application's subdomain. It never speaks FHIR and is not on the noyau's network. See [Signing in](#signing-in). | none |
| `noyau` | HAPI FHIR R4 | The **noyau**. Stores all medical data as standard FHIR resources and exposes the standard FHIR REST API. Runs in HAPI's default configuration. | none |
| `base-noyau` | PostgreSQL | Where HAPI keeps its data on disk, in the `noyau-donnees` volume. | none |
| `base-identite` | PostgreSQL | Where identite keeps accounts, codes carnet, sessions and failure counters, in the `identite-donnees` volume. No medical data, and no secret in clear. Only identite reaches it. | none |
| `chargement` | Python | Writes the demo dataset from `donnees/` into the noyau at every `docker compose up`, then exits. See [The demo dataset](#the-demo-dataset). | none |

`commun/` is not a container. It is a Python library, copied into each service's image when the image is built. Today it holds what every service shares: the service skeleton (the FastAPI application, its `/sante` route and its OpenAPI contract under the service's prefix), the token contract (what a token says about its holder, which identite writes and every service reads back) and the token verification every service uses to know who is asking, and, under `commun/src/commun/fhir/`, everything FHIR: the client every service uses to talk to the noyau, the code and identifier systems Lafia uses, and the translation of the things Lafia names (`commun/src/commun/modele.py`: établissement, officine, agent, patient, tarif) into FHIR resources. A service's own code holds only its own routes and rules.

`donnees/` is not a service either. It holds the demo dataset, hand-written in Lafia's vocabulary, and the loader that writes it into the noyau; both are built into the `chargement` image. The same package is built into identite's image, which reads its accounts from it.

`web/` is not a container either. It is an npm workspace holding the applications (`web/soin/`, `web/caisse/`, `web/pharmacie/`, `web/citoyen/`), the product site (`web/site/`), and two packages they share. `web/commun/` is to the applications what `commun/` is to the services: how an application reaches its service and identite through the gateway, the sign-in page, the home page every application shows today, and the renewal of an expired token before a page renders. `web/design/` is the design system: the tokens, the Atkinson Hyperlegible fonts served by Lafia itself, the logo, pictograms, icons and illustrations, and the React components every surface is built from (`docs/design/` describes them). Both are compiled into each application when its image is built, the way `commun/` is copied into each service: nothing of them is loaded at runtime. The site uses the design system only.

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
2. **Routing.** Caddy reads the `Caddyfile`. Every actor gets the same site block, written once as the `acteur` snippet and imported once per actor: `import acteur soin` gives the site `soin.{$LAFIA_DOMAINE}`, which sends `/api/soin/*` to `soin:8000` and `/api/identite/*` to `identite:8000`, answers 404 to any other `/api/*` path, and sends everything else to the application, `application-soin:3000`. `soin` is the container's name, which Docker's internal DNS resolves on the `passerelle` network. Caddy forwards the path unchanged, so the service receives `/api/soin/sante`. The domain itself is a site block of its own, which sends every path to `application-site:3000` except `/api/*`, answered 404: the product site reaches no service. On every response of every site block, page, API answer or refusal, Caddy sets the security headers, written once as the `en-tetes` snippet (HTTPS only, no content-type guessing, never inside another site's frame, no referrer sent to another site, no geolocation or microphone) and removes the headers that would name the software behind it: `Server`, `X-Powered-By`, `Via`. HTTP/3 is off, since it would need UDP 443, which the stack does not publish.
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

Every protected route answers only to a signed token, which identite issues when someone signs in (see [Signing in](#signing-in)). Here is what happens to `GET https://soin.localhost/api/soin/session`:

1. **The token travels in a cookie.** identite sets it in the application's `__Host-session` cookie, `HttpOnly`, `Secure`, `SameSite=Strict`, on the path `/` and without a `Domain`: the browser sends it back only to the subdomain where the sign-in happened, so a caisse cookie never reaches soin, and client JavaScript never reads it. Caddy forwards it to the service unchanged. Tests and third-party integrators may send the same token in an `Authorization: Bearer` header instead.
2. **The service verifies it alone.** `VerificateurDeJetons` in `commun/src/commun/jeton.py` checks the signature (EdDSA, Ed25519) against the public key in `JETON_CLE_PUBLIQUE`, the expiry, a lifetime of at most one hour, and the claims. The service never calls identite to do so. A token belongs to one of three holders: an `Agent` (a role and an établissement), an `Officine` (no établissement: an officine is not one), or a `Citoyen` (an NPI).
3. **The service decides whether it serves that holder.** soin serves médecin and infirmier, caisse serves caissier, pharmacie serves pharmacien and the officine. Each rule is in the service's own `regles/acces.py`, for instance `services/soin/src/soin/regles/acces.py`, and is enforced by a guard of `VerificateurDeJetons`: `agent` for soin and caisse, `agent_ou_officine` for pharmacie. citoyen serves the citoyen alone: the `citoyen` guard refuses every agent and officine with 403, and `services/citoyen/src/citoyen/regles/acces.py` decides what the service gives back of the citoyen: never the NPI.

A token carries these claims (ADR 0004), and `exp`:

| Holder | `sub` | `role` | Other claim |
|---|---|---|---|
| Agent | The agent's `Practitioner` id in the noyau | `médecin`, `infirmier`, `caissier`, `pharmacien` | `etablissement`: the `Organization` id of the établissement where they signed in |
| Officine | The officine's `Organization` id | `officine` | None |
| Citoyen | Drawn at random at each sign-in, never derived from the NPI | `citoyen` | `npi` |

identite issues tokens that live 15 minutes; a service refuses one that expires more than an hour ahead. identite writes the claims with `revendications()` from `commun/src/commun/jeton.py`, and the services read them back in the same module, so the contract is written once.

| What you get | What it means |
|---|---|
| `200` `{"sub":"agent-01","role":"médecin","etablissement":"cnhu-hkm"}` | A valid token of a soignant. `sub` is the agent's `Practitioner`, so a service can name the author of a write without asking identite. |
| `200` `{"sub":"officine-zogbo","role":"officine"}`, from `/api/pharmacie/session` | A valid token of an officine. |
| `200` `{"sub":"…","role":"citoyen"}`, from `/api/citoyen/session` | A valid token of a citoyen. The NPI stays in the service, which will use it to choose the carnet it opens (F6); it never goes back to the application, which has no use for it. |
| `401` | No token; or a token that is malformed, expired, valid for more than an hour, signed with another key, unsigned, or whose claims break the table above, such as an officine token naming an établissement or an NPI. |
| `403` | A valid token of a holder the service does not serve: for soin, caissier, pharmacien, officine and citoyen; for citoyen, every agent and officine. |

A service holds only the public key: it can verify tokens but cannot forge them, even if compromised. The private key that signs them, `JETON_CLE_PRIVEE`, is read by identite alone. Neither the operator's shell nor the test suite holds it: the suite gets its tokens by signing in (see [The test suite](#the-test-suite)).

## Signing in

identite is where people sign in. It keeps accounts in its own PostgreSQL database, `base-identite`, and hands out tokens. Here is what happens when a médecin submits the sign-in form of `https://soin.localhost/connexion`:

```
 browser, on the page soin.localhost/connexion
   │ 1. POST https://soin.localhost/api/identite/connexion
   │    form: identifiant, mot_de_passe; header Origin: https://soin.localhost
   ▼
 passerelle (Caddy)                        /api/identite/*  →  identite:8000, with X-Forwarded-For
   ▼
 identite (FastAPI)                        networks: passerelle + identite
   │ 2. the application from Host: soin; the form's Origin must be soin's
   │ 3. guessing limits; the mot de passe against its argon2id hash
   │ 4. the role must be one soin signs in: médecin or infirmier
   │ 5. opens a session, signs a token
   ▼
 base-identite (PostgreSQL)                network: identite only

 browser  ←  303 to /, Set-Cookie: __Host-session (the token), __Host-renouvellement (the session)
```

1. **The form goes straight to identite.** The sign-in page belongs to the application, but its form posts to `/api/identite/connexion` on the same subdomain, which Caddy routes to identite. The application never sees the mot de passe, nor the token identite sets in return.
2. **Which application.** identite reads the application from the request's host, `<application>.<domaine>`, whether it comes through the gateway's public entry or its internal one. It accepts a form only when its `Origin` is that application's own, `https://soin.localhost`; any other origin, or none, gets 403, so that a hostile page cannot sign someone in under an attacker's account. The browser sends that origin because the gateway's referrer policy is `same-origin`: it sends nothing to another site, but keeps the origin on requests to its own; under `no-referrer`, a browser would send `Origin: null`, and every sign-in would be refused.
3. **Guessing limits.** Every attempt counts as a failure until it succeeds, and each counter is updated under a row lock, so attempts sent at the same time are counted one by one. The rules live in `services/identite/src/identite/regles/tentatives.py`. Five failures on one identifiant or NPI lock it for 15 minutes, even against the right credentials: a guesser learns nothing from a locked account. A success resets its counter. 50 failures from one address within 15 minutes refuse that address until the window passes, so that one machine cannot spray guesses across many NPIs. The address is the one Caddy forwards in `X-Forwarded-For`, which replaces any value the client sends. An unknown identifiant is counted and checked against a dummy hash: it takes as long as a wrong mot de passe, and gets the same answer.
4. **One role, one application.** soin signs in médecins and infirmiers, caisse caissiers, pharmacie pharmaciens and officines, citoyen the citoyen. The check comes after the mot de passe: someone who does not know it never learns which application an identifiant opens.
5. **The session.** identite stores a session, named by a random identifier it keeps only as a SHA-256 hash, and signs a token for its holder. Both cookies are `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/`, without `Domain`: `__Host-session` holds the token, with a `Max-Age` of its 15 minutes; `__Host-renouvellement` holds the session's identifier, with a `Max-Age` of the session's remaining life.

A refused sign-in goes back to the sign-in page with no cookie: `/connexion?erreur=identifiants` for a wrong identifiant or mot de passe, one message for both; `erreur=application` when the account does not open this application; `erreur=verrouille` after too many failures. The page shows the matching message.

**Sessions and renewal.** An agent's or an officine's session lasts 12 hours at most and ends after 30 minutes without renewal; a citoyen's lasts one hour at most. When the token expires, the browser drops its cookie and keeps the session's. Before rendering any page, the application's server (`web/commun/src/renouvellement.ts`, called by each application's `src/proxy.ts`) sees the token missing and the session present, and asks identite for a new token: `POST /api/identite/session/renouveler`, through the gateway's internal entry, with the session cookie. identite answers 204 with both cookies set again, and the application redirects the browser to the same address with them; a renewal counts as activity. When the session is over, identite answers 401 and clears both cookies, and the page renders without a session. The application passes cookies along and never reads the token. Déconnexion, a form on the home page (`POST /api/identite/deconnexion`), deletes the session and clears both cookies; the token already issued stays valid until it expires, 15 minutes at most.

**The citoyen** signs in with their NPI and the code carnet printed on their latest reçu, on the citoyen application only; its sign-in screen arrives with F6. The code is six characters without `0 O 1 I L`, shown as `K7M-4PX`, and may be typed with or without its dash, in capitals or not. An unknown NPI, a malformed one and a wrong code get the same answer. Each sign-in draws a new random `sub`.

**Codes carnet.** At the end of a visite, the soin application asks identite for a code with the soignant's session: `POST /api/identite/codes-carnet` with `{"npi": "…"}`. identite admits médecins and infirmiers only, draws a code, stores its hash against the NPI with the agent and the établissement that asked, and returns it once, to be printed on the reçu. The new code replaces the NPI's previous one: an old reçu opens nothing (ADR 0005).

identite's routes, all under `/api/identite`:

| Route | Who | Answer |
|---|---|---|
| `POST /connexion` | Form: `identifiant`, `mot_de_passe` | 303 to `/` with both cookies, or to `/connexion?erreur=…`; 403 for a form from another origin |
| `POST /citoyen/connexion` | Form: `npi`, `code` | The same, on the citoyen application only |
| `POST /session/renouveler` | The session cookie | 204 with a new token; 401 and both cookies cleared when the session is over, closed, or opened on another application |
| `POST /deconnexion` | Form | 303 to `/connexion`, the session closed and both cookies cleared |
| `GET /session` | Any valid token | An agent: `{sub, role, etablissement, nom, nom_etablissement}`; an officine: `{sub, role, nom}`; a citoyen: `{sub, role}`, never the NPI |
| `POST /codes-carnet` | Médecin, infirmier | 201 `{code}`; 403 for any other role; 422 for an NPI that is not 13 digits |
| `GET /comptes-de-demonstration` | Public | The demo accounts of the roles the application signs in, with their mots de passe; never the accounts reserved for tests |
| `GET /sante` | Public | `{"service":"identite","statut":"disponible"}` |

**What identite keeps.** Accounts (identifiant, argon2id hash of the mot de passe, role, `sub`, établissement, and the names applications show), one code carnet per NPI (its argon2id hash, who asked, when), sessions (the SHA-256 hash of their identifier, the holder, the application, the start and the end) and failure counters (keyed by the SHA-256 hash of an identifiant, an NPI or an address). Nothing in it opens an account or a carnet. identite creates its schema at startup, then loads the accounts of the demo dataset: each is created or updated by its identifiant, and accounts absent from the files are left alone. It inserts the demo codes carnet only for NPIs that have none, never over a code issued since. Its logs carry account identifiers and outcomes, never an NPI, a name, a mot de passe or a code.

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
3. **Rendering on the server.** Before any page, the application's `proxy.ts` renews an expired token (see [Signing in](#signing-in)). The page (`web/soin/src/app/page.tsx`) shows `EtatDeLActeur` from `web/commun/src/etat.tsx`, the same page every application shows today with its own title and service. It is rendered on every request, never at build time, so it shows the state of the moment. Nothing runs in the browser to fetch data: the HTML arrives complete.
4. **Back through the gateway.** The application's server asks its service for its state (`web/commun/src/service.ts`). If the browser sent a session cookie, it also asks identite who holds it, `/api/identite/session`, passing the cookie on: the application never reads the token itself, identite verifies it and names its holder. It does not call `soin:8000` directly: it calls the gateway, at the address in `PASSERELLE_URL`, `http://soin.localhost:8080`. On the `passerelle` network, Docker's DNS resolves `soin.localhost` to the `passerelle` container, which carries that name as a network alias.
5. **The internal entry.** Port 8080 is Caddy's internal entry. It speaks plain HTTP, because the request never leaves the `passerelle` network, and no port is published for it on the host. It shares the site block of `soin.localhost`, so an application's server gets exactly the routes its subdomain gets from the outside, and no more. From there the request follows the same path as `/api/soin/sante` above.

The page shows "Soin" ("Caisse", "Pharmacie", "Mon carnet" on the other subdomains), the service's status and the noyau's: `disponible, FHIR 4.0.1` when the whole chain answers. With a session, it shows the connected role and, for an agent, their name and the name of their établissement, for an officine its name, with a button to sign out; a citoyen sees `Connecté comme citoyen`, never their NPI, which the page does not receive. Otherwise it shows `Session : aucune`, and on soin, caisse and pharmacie a link to `/connexion`, the sign-in page, which lists the application's demo accounts. When the service answers 503, the page shows the noyau as `injoignable`. When the service does not answer at all, the page shows the service as `injoignable` and the noyau as `inconnu`. The page itself always renders, as long as the application runs.

## The demo dataset

The noyau is never empty: at every `docker compose up`, locally and on the VM, the `chargement` container writes the demo dataset into it. Everything in it is synthetic except the names of the five établissements, real public facilities chosen to cover the health pyramid.

**What it holds.** The files live in `donnees/src/donnees/`, written by hand in Lafia's vocabulary, each thing with a fixed id:

| File | What it lists |
|---|---|
| `etablissements.toml` | The five établissements, from the CNHU in Cotonou to the centre de santé of Kpanroun, each with its level |
| `officines.toml` | Two officines with invented names, and the single account of each |
| `agents.toml` | Soignants, caissiers and pharmaciens, each with one account per établissement where they work, plus accounts reserved for the test suite |
| `patients.toml` | About thirty patients from several regions, ages and languages, plus a few reserved for the test suite. No clinical data. |
| `catalogue.toml` | The products and acts an ordonnance can carry, each with its price at every level of établissement |
| `citoyens.toml` | Demo citoyens: the NPI of a dataset patient and the code carnet of their latest reçu |

Accounts, mots de passe and codes carnet are public, since everything is synthetic. Every NPI starts with six zeros and every phone number with `+229 01 00`, series no real person holds. Resource ids say nothing about the person: `patient-007`, `agent-15`.

**What it becomes in the noyau.** `donnees/src/donnees/__init__.py` reads the files into the records of `commun/src/commun/modele.py`; `commun/src/commun/fhir/ressources.py` turns each into a FHIR resource:

| In the dataset | FHIR resource | Shape |
|---|---|---|
| Établissement, officine | `Organization` | Name; `type` from Lafia's `type-de-structure` code system (`chu-national`, `chu-departemental`, `chu-de-zone`, `centre-de-sante`, `officine`); `address` with département (`state`) and commune (`city`). |
| Agent | `Practitioner` | Name; role (`médecin`, `infirmier`, `caissier`, `pharmacien`) as `qualification`. One per person, however many accounts: the établissement comes with the account and travels in the token. Its id is the `sub` of the agent's tokens. |
| Patient | `Patient` | NPI as the only `identifier` (system `https://npi.gouv.bj`); name, gender, birth date; place of birth and nationality through the standard HL7 extensions; address from département (`state`) to quartier (`line`); phone in `telecom`; personne à prévenir in `contact`; spoken languages in `communication`, as BCP 47 codes. |
| Tarif | `ChargeItemDefinition` | One per product or act per établissement. The product in `code`, in Lafia's `catalogue` code system, with its ATC code for a medicine; the établissement in `useContext` (`venue`); the price in FCFA (`XOF`) as the base price component; an `identifier` `<établissement>:<code>`, so that the caisse finds a tarif in one search. Officines have none: their prices live in their own software. |

Lafia's own code and identifier systems are named under `https://lafia.bj/fhir` (`commun/src/commun/fhir/systemes.py`, `docs/adr/0006-systemes-de-codes-et-d-identifiants.md`). They are names, not addresses: nothing answers there.

**How it is loaded.** `chargement` waits until the noyau is healthy, sends the whole dataset as one FHIR transaction of `PUT`s, each resource under its fixed id, logs how many resources it created and how many were already there, and exits. The transaction is all or nothing. The loader never deletes anything: a resource whose content has not changed keeps its version, since HAPI ignores an update that changes nothing; a dataset resource that changed, in the files or by a user's hand, gets the dataset's content back as a new version, and its history keeps the version before; whatever users created stays. A redeploy therefore never wipes the demo or what the jury created. Starting over is one command, which erases the noyau's volume: `docker compose down -v`, then `docker compose up -d --build --wait`.

The same files give identite its accounts, built into its image, so that every token names a `Practitioner` and an `Organization` the noyau holds. Later features add their own resources (cas, mesures, allergies, ordonnances) to the same files and loader.

## Who can reach whom

The network layout enforces the architecture rules. Code does not have to remember them.

```
                  outside (your machine, the internet)
                                │ 80, 443
 ┌──────────────────────────────┼───────────────────────────┐
 │ network passerelle           ▼                           │
 │                                                          │
 │  application-soin         passerelle           identite  │
 │  application-caisse                               │      │
 │  application-pharmacie                            │      │
 │  application-citoyen                              │      │
 │  application-site                                 │      │
 │                                                   │      │
 │  soin    caisse    pharmacie    citoyen           │      │
 │   │        │          │           │               │      │
 └───┼────────┼──────────┼───────────┼───────────────┼──────┘
 ┌───┼────────┼──────────┼───────────┼────┐ ┌────────┼──────┐
 │   └────────┴────┬─────┴───────────┘    │ │        ▼      │
 │                 ▼                      │ │ base-identite │
 │ chargement ──▶ noyau ── base-noyau     │ │               │
 │                                        │ │ network       │
 │ network noyau, internal: no internet   │ │ identite,     │
 └────────────────────────────────────────┘ │ internal      │
                                            └───────────────┘
```

| From | Can reach | Cannot reach |
|---|---|---|
| Outside | `passerelle`, on 80 and 443 | Anything else: no other container publishes a port, and Caddy's internal entry (8080) is not published either. |
| `passerelle` | The containers the `Caddyfile` routes to | `noyau`, `base-noyau` and `base-identite`: Caddy is on neither the `noyau` nor the `identite` network. |
| `application-soin`, `application-caisse`, `application-pharmacie`, `application-citoyen` | Its own service and `identite`, through the gateway | `noyau` and `base-identite`, by name or by address: the application is only on the `passerelle` network. Another actor's service: the gateway answers 404 to `/api/soin/*` on `caisse.<domaine>`, and so on. |
| `application-site` | The gateway; it calls nothing | `noyau` and `base-identite`, by name or by address: it is only on the `passerelle` network. Any service through the gateway: on the domain itself, every `/api/*` path answers 404. |
| `soin`, `caisse`, `pharmacie`, `citoyen` | `noyau`, over FHIR | `base-noyau`'s data: only HAPI holds the database password. `base-identite`, by name or by address: they are not on the `identite` network. |
| `identite` | `base-identite`; and what any container on the `passerelle` network reaches: the gateway, the services, the applications, the internet. It calls none of them. | `noyau`, by name or by address: identite is not on the `noyau` network. |
| `base-identite` | Nothing: the `identite` network is internal, and holds only identite and its database. | |
| `chargement` | `noyau`, over FHIR | The gateway, the services, the applications, the internet: it is only on the `noyau` network. |
| `noyau` | `base-noyau` | The internet: the `noyau` network is internal. |

The test suite checks the first, third, fourth and fifth rows from the machine that runs the stack: only `passerelle` publishes ports; from inside each application container and `identite`, the noyau gives no answer; from inside each application container and each FHIR service, `base-identite` gives no answer, while `identite` reaches it; each whether called by its name or by its IP address. It also checks that `chargement` is attached to the `noyau` network and to no other. Through the gateway, it checks that no subdomain reaches another actor's service.

Two rules are conventions rather than network properties. **Services never call each other**: they share the `passerelle` network with identite, so nothing physically stops one from calling another. **An application calls only the gateway**: it could open a connection to `soin:8000` directly. Both rules are kept in code and review. Going through the gateway keeps a single place, the `Caddyfile`, that decides what each subdomain can reach, for the browser and for the application's server alike.

## Starting up and staying up

`docker compose up -d --build --wait` starts the containers in dependency order:

1. `base-noyau` and `base-identite` are healthy once PostgreSQL accepts connections (`pg_isready`).
2. `noyau` starts next. It is healthy once HAPI's own probe, shipped in the official image, reports Spring and its database up. On the very first start HAPI creates its schema, which takes a few minutes.
3. `chargement` starts once the noyau is healthy, writes the demo dataset, and exits with code 0. A failed load exits with another code, and nothing that waits for it starts.
4. `soin`, `caisse`, `pharmacie` and `citoyen` start once the noyau is healthy and `chargement` has completed: they serve a noyau that holds its établissements and tarifs. Each is healthy when it answers its own OpenAPI contract, and refuses to start without a readable `JETON_CLE_PUBLIQUE`, except on `localhost` (see [Configuration](#configuration)). `identite` starts once `base-identite` accepts connections: it creates its schema, loads the demo accounts and codes carnet, then answers; it is healthy when it answers its OpenAPI contract too. It refuses to start without a readable `JETON_CLE_PRIVEE`, except on `localhost`.
5. Each application, and the site, needs only the gateway to start: it asks its service for its state on each page, not at startup. It is healthy once its server listens.

`--wait` returns when every container is healthy. It would take `chargement`'s exit for a failure, were the services not waiting for it: Compose accepts a container that stops only when another waits for it to complete. `chargement` runs again at each `up`, but not after a reboot, when Docker restarts the containers without Compose; the dataset is already in the noyau's volume then. Each other container has `restart: unless-stopped`, so it comes back after a crash or a reboot. Each also has a memory limit, so the whole stack fits on one virtual machine: HAPI gets 2 GB with a 1 GB Java heap, its PostgreSQL 512 MB, identite's 256 MB, the gateway and `chargement` 128 MB each, each service, each application and the site 256 MB, about 5.6 GB in all.

`docker-compose.yml` writes what services and applications share once. `x-service-fhir` holds what every service that speaks FHIR needs: both networks, a healthy noyau and a completed `chargement` before starting, `NOYAU_URL`, `JETON_CLE_PUBLIQUE` and `LAFIA_DOMAINE`. `x-application` holds what every application needs: the `passerelle` network only, and the gateway before starting. Each service is built by `services/Dockerfile` with its name as `SERVICE`, `commun` included, and `donnees` too for identite; each application by `web/Dockerfile` with its name as `APPLICATION`; `chargement` by `donnees/Dockerfile`, `commun` included.

Docker's health checks and `/sante` answer different questions. Docker checks each container on its own, which tells you which one is broken. `/sante` checks the chain from the outside, which tells you whether a request can get through.

## Configuration

Variables come from a `.env` file at the root, which git ignores. `.env.example` lists them all:

| Variable | Used by | Local default |
|---|---|---|
| `LAFIA_DOMAINE` | Caddy: every application is served on `<application>.<domaine>`. soin, caisse, pharmacie, citoyen: the development key is allowed on `localhost` only | `localhost` |
| `NOYAU_BASE_MOT_DE_PASSE` | The noyau's PostgreSQL and HAPI | `noyau-local` |
| `IDENTITE_BASE_MOT_DE_PASSE` | identite's PostgreSQL and identite | `identite-local` |
| `JETON_CLE_PUBLIQUE` | soin, caisse, pharmacie, citoyen, to verify tokens: the base64 line of an Ed25519 public key PEM | Empty: the development key, on `localhost` only |
| `JETON_CLE_PRIVEE` | identite alone, to sign tokens: the base64 line of an Ed25519 private key PEM. It never leaves the machine that runs the stack | Empty: the development key, on `localhost` only |

Without a `.env`, the local defaults apply. In production every variable is set in `.env`. The token keys are guarded in code, by one rule in `commun` (`lire_cle`): the development pair's private half is public, so a service uses the development public key only when `LAFIA_DOMAINE` is `localhost` and `JETON_CLE_PUBLIQUE` is empty, and identite the development private key only when `LAFIA_DOMAINE` is `localhost` and `JETON_CLE_PRIVEE` is empty. On any other domain each refuses to start without a key, and refuses the development key: a deployed stack never issues nor accepts a token anyone can sign. A database keeps the first password it starts with, so each password must be in `.env` before the first start. Three addresses are set in `docker-compose.yml` instead, because they are internal: `NOYAU_URL`, where a service or `chargement` finds the noyau; `BASE_URL`, where identite finds its database; and `PASSERELLE_URL`, where an application's server finds the gateway's internal entry for its subdomain (`http://soin.<domaine>:8080`).

## Deployment

The public stack runs on one Azure virtual machine (Ubuntu 24.04, 2 vCPU, 8 GB), from the same `docker-compose.yml` as on a laptop. Only its `.env` differs. The steps to set up a server and deploy are in `deploiement.md`; this section explains what they put in place.

```
 browser  ──  soin.lafia.stephanebah.page  ──  DNS: *.lafia.stephanebah.page  →  172.189.57.57
                                                                     │ 443
 VM (Azure)  ┌───────────────────────────────────────────────────────┼──────┐
             │ firewall: 80, 443 for everyone; 22 for the operator   ▼      │
             │ Docker, started at boot  →  the containers, as above         │
             │ ~/lafia: the repository, and .env, which exists nowhere else │
             └──────────────────────────────────────────────────────────────┘
```

- **Names.** One wildcard DNS record, `*.lafia.stephanebah.page`, points every subdomain at the VM's public address, and `.env` sets `LAFIA_DOMAINE=lafia.stephanebah.page`. The applications are then `https://soin.lafia.stephanebah.page`, `https://caisse.…`, `https://pharmacie.…` and `https://citoyen.…`. Adding an actor needs no DNS change.
- **Certificates.** On a real domain, Caddy obtains a certificate for each subdomain from a public authority (Let's Encrypt) the first time it starts, through ports 80 and 443, and renews them on its own. They are kept in the `passerelle-donnees` volume, so a redeploy does not ask again.
- **Firewall.** The VM's Azure network security group admits 80 and 443 from anywhere and SSH from the operator's address only. The gateway's internal entry, 8080, is not published by Docker and not open in Azure either.
- **Preparing the VM.** `deploiement/preparer-vm.sh <domaine>` installs Docker, enables it at boot, clones the repository into `~/lafia` and writes `.env`: the domain, a random password for each database, and a fresh Ed25519 key pair for tokens. `.env` is readable by the VM's user only. Run again, the script keeps every value already in `.env` and adds only the variables it lacks: new secrets would lock HAPI and identite out of their own databases. It runs before the first deploy of a version that needs a new variable, since a database keeps the first password it starts with.
- **Deploying `main`.** `ssh -i <vm-key.pem> azureuser@lafia.stephanebah.page lafia/deploiement/deployer.sh` pulls `main`, refuses to go on while `.env` lacks a variable that `.env.example` lists, builds the images one at a time (two processors do not build four Next.js applications in parallel comfortably), brings the stack up with `--wait`, which loads the demo dataset again, recreates the gateway when the `Caddyfile` it serves differs from the repository's (it is mounted as a single file, which `git pull` replaces), and removes the images it replaced.
- **Reboots.** Docker starts with the VM, and every container has `restart: unless-stopped`: the stack comes back without anyone logging in.

## Try it yourself

```sh
docker compose up -d --build --wait    # start; the first time takes a few minutes
docker compose ps                      # which containers run, which are healthy
curl -k --resolve soin.localhost:443:127.0.0.1 https://soin.localhost/api/soin/sante
curl -k --resolve soin.localhost:443:127.0.0.1 https://soin.localhost/    # the soin page
curl -k --resolve soin.localhost:443:127.0.0.1 https://soin.localhost/api/identite/sante
curl -k --resolve soin.localhost:443:127.0.0.1 https://soin.localhost/api/soin/session    # 401: no token
curl -k --resolve soin.localhost:443:127.0.0.1 https://soin.localhost/api/identite/comptes-de-demonstration
curl -k --resolve soin.localhost:443:127.0.0.1 -i -H "Origin: https://soin.localhost" \
  -d identifiant=medecin.cnhu.1 -d mot_de_passe=lafia-demo \
  https://soin.localhost/api/identite/connexion    # 303 to /, and the two cookies
curl -k --resolve caisse.localhost:443:127.0.0.1 https://caisse.localhost/    # the caisse page
curl -k --resolve caisse.localhost:443:127.0.0.1 https://caisse.localhost/api/soin/sante    # 404: not caisse's service
curl -k --resolve citoyen.localhost:443:127.0.0.1 https://citoyen.localhost/    # the citoyen page, Mon carnet
curl -k --resolve localhost:443:127.0.0.1 https://localhost/    # the product site
curl -k --resolve localhost:443:127.0.0.1 https://localhost/api/identite/sante    # 404: the site reaches no service
docker compose logs -f soin            # follow a container's log
docker compose logs chargement         # how many resources the last load created
docker compose run --rm --no-deps chargement    # load the dataset again: nothing changes
docker compose stop noyau              # watch /sante turn into a 503 …
docker compose start noyau             # … and back
uv run --project tests pytest tests    # the black-box suite
docker compose down                    # stop and keep the data (down -v erases it)
```

In Windows PowerShell 5, type `curl.exe`, because `curl` is an alias for another command there. `-k` skips certificate checks; `--resolve` points the subdomain at this machine.

In a browser, open `https://localhost` for the product site and its door to each application, `https://soin.localhost` for the soin application, `https://soin.localhost/connexion` to sign in with one of the demo accounts it lists, and `https://soin.localhost/api/soin/docs` for the service's documentation. The documentation lists every route, its answers, and a *Try it out* button. The browser warns about the certificate until you trust Caddy's local authority, whose root is at `/data/caddy/pki/authorities/local/root.crt` in the `passerelle` container.

## The test suite

`tests/` holds a black-box suite. It talks to the stack only through the gateway, as a user or an attacker would, and asserts what they can observe: status codes, JSON bodies, and the text of pages.

- Each application is addressed by its subdomain. Locally, the suite connects to `127.0.0.1` and sends the subdomain as the requested host.
- Certificates are verified. Locally, the suite first reads Caddy's root certificate from the `passerelle` container; elsewhere, it uses the public authorities.
- `LAFIA_DOMAINE=<domaine>` points the same suite at another deployment.
- The suite gets valid tokens by signing in through identite with the demo accounts, read from `donnees/`, locally and against production alike: it never holds a deployment's private key. Tokens of a wrong shape (expired, valid for a year, wrong claims, another key, unsigned) can only be forged with the development key, which a stack served on `localhost` accepts; those tests are skipped against another deployment. A form carries the `Origin` a browser would send from the application's page, derived from the referrer policy the gateway sets on it, so a policy that makes browsers send `Origin: null` fails the suite.
- `tests/test_identite.py` signs in every demo account on its application and checks both cookies and the token's lifetime; the same answer for a wrong mot de passe and an unknown identifiant; refusals for a role on another application and a form from another origin; renewal, and its refusal after déconnexion or on another application; the citoyen's sign-in, however the code is typed, and with every demo citoyen the citoyen application lists; codes carnet, issued to soignants only, each replacing the last; `/session` for every kind of holder; the demo accounts each application lists. On the machine that runs the stack, it also starts identite's image on another domain than `localhost`, and checks that it refuses to start without a key of its own or with the development key. Lockouts run on accounts and NPIs reserved for the tests, never listed, so that running the suite in production never locks a jury member out. The per-address limit is not exercised: it would lock the machine running the suite out of every other test. Each run still counts about twenty failures against that machine's address, so a third run within 15 minutes is refused; locally, `docker compose exec base-identite psql -U identite -c "TRUNCATE tentative"` clears the counters.
- `tests/test_acteurs.py` runs the same checks for every actor, from one table: each actor's title and the roles its service serves, the officine among pharmacie's. Session tests take every admitted agent role, every refused role and every invalid token, each by cookie and by `Authorization` header; the cross-actor test asks each subdomain for every other actor's `/sante` and expects 404. Each subdomain also answers 404 to the noyau's paths and to unknown API paths, and every response, page or API, carries the security headers and none that names the software. `tests/test_citoyen.py` holds what only the citoyen has: a session without the NPI, and a page that never contains it, anywhere in its HTML.
- `tests/test_site.py` addresses the product site on the domain itself: its page, a link to each application, the security headers, a 404 for any `/api/*` path, and every demo account it shows being one that identite lists for that application, so the site cannot drift from the dataset.
- Network isolation cannot be seen through the gateway, so `tests/test_isolement.py` checks it with `docker`, on the machine that runs the stack: it reads which ports each container publishes and which networks `chargement` is on, and sends probes from inside the containers: HTTP from each application container, the site's included, and identite to the noyau, TCP from each application and each FHIR service to `base-identite`. Each probe first reaches the gateway, or for `base-identite` is first run from identite, so a probe that cannot run is never mistaken for an unreachable noyau. These checks run only when the stack on this machine is the one the suite targets, that is when its gateway serves `LAFIA_DOMAINE`; otherwise they are skipped, since this machine's containers would say nothing about the stack under test.
- The noyau's content cannot be seen through the gateway either. `tests/test_donnees.py` reads it from inside the `soin` container, with `docker` and under the same condition, and compares it with the dataset files: every établissement and officine as an `Organization` with its type, every agent as a `Practitioner`, every patient found by NPI with each field, every tarif found by its identifier at every établissement and none at an officine, every demo citoyen a patient. It also loads the dataset a second time and checks that no version changed, and that no NPI or phone number in the files could be a real person's.

## Where the code is

| File | What it holds |
|---|---|
| `docker-compose.yml` | Containers, networks, volumes, health checks, memory limits |
| `Caddyfile` | Routing: the `en-tetes` security headers; the `acteur` site block, imported once per actor, publicly and on the internal entry; the product site on the domain itself |
| `commun/src/commun/service.py` | `creer_service()`: a service's FastAPI app, its `/sante` and its OpenAPI contract under `/api/<service>`; `client_fhir`, the dependency that hands a route the noyau's client |
| `commun/src/commun/fhir/client.py` | `ClientFhir`: the only way a service talks to the noyau, reading or sending a transaction |
| `commun/src/commun/fhir/systemes.py` | The code and identifier systems Lafia uses in the noyau, its own and the standard ones |
| `commun/src/commun/fhir/ressources.py` | The translation of Lafia's records into FHIR resources: `Organization`, `Practitioner`, `Patient`, `ChargeItemDefinition` |
| `commun/src/commun/modele.py` | The things Lafia names, as records, without FHIR: établissement, officine, agent, patient, product, tarif |
| `commun/src/commun/jeton.py` | The token contract: the three holders `Agent`, `Officine` and `Citoyen`, `revendications()` and its reverse, the lifetimes, the development-key rule `lire_cle`; `VerificateurDeJetons`: token verification, the `porteur` dependency, and the `agent`, `agent_ou_officine` and `citoyen` guards |
| `services/<service>/src/<service>/service.py` | A service's own routes, `/session` today, handed to `creer_service()` |
| `services/<service>/src/<service>/regles/acces.py` | Who a service serves: the roles soin, caisse and pharmacie admit, the officine for pharmacie; for citoyen, what the service gives back of the citoyen, never the NPI |
| `services/identite/src/identite/service.py` | identite's routes: sign-in, renewal, déconnexion, `/session`, codes carnet, demo accounts; the cookies |
| `services/identite/src/identite/guichet.py` | What those routes do: sign-ins with their guessing limits, sessions, renewals, codes carnet |
| `services/identite/src/identite/regles/` | identite's rules: which roles each application signs in, session lifetimes, guessing limits, the code carnet and NPI formats |
| `services/identite/src/identite/base.py`, `empreintes.py`, `jetons.py` | identite's database and its schema; argon2id and SHA-256 hashes; token signing with the private key |
| `services/identite/src/identite/demonstration.py` | Loading the demo accounts and codes carnet at start; the accounts each sign-in page lists |
| `services/Dockerfile` | One image per service, `commun` included, with its health probe: `docker build --build-arg SERVICE=soin --build-context commun=commun services` |
| `donnees/src/donnees/*.toml` | The demo dataset, in Lafia's vocabulary |
| `donnees/src/donnees/__init__.py`, `chargement.py` | Reading the dataset into records; the loader, `python -m donnees.chargement` |
| `donnees/Dockerfile` | The `chargement` image: `docker build --build-context commun=commun donnees` |
| `web/package.json` | The npm workspace: the applications and the two shared packages |
| `web/commun/src/service.ts` | How an application asks its service and identite, through the gateway: the service's state, the holder of the cookie, the demo accounts |
| `web/commun/src/connexion.tsx` | `PageDeConnexion`: the sign-in form, the message of each refusal, the demo accounts, each with a button that fills the form (`UtiliserCeCompte.tsx`) |
| `web/commun/src/renouvellement.ts` | Renewing an expired token before a page renders, called by each application's `src/proxy.ts` |
| `web/commun/src/etat.tsx` | `EtatDeLActeur`: the page every application shows today, rendered on the server at each request, under the application header that names the actor, the établissement and the agent, and holds the déconnexion form |
| `web/commun/src/site.ts` | The product site's address, derived from the page's host, for the logo of the application header |
| `web/design/` | The design system package, compiled into each application and the site: `tokens/` and `fonts/`, the SVG sources in `assets/`, the components in `src/` (`src/generes/` is generated from `assets/` by `npm run generer`) |
| `web/site/` | The product site: its one page, the demo accounts it shows (`src/comptes.ts`), the journey that follows the numéro d'ordonnance as the page scrolls (`src/app/Parcours.tsx`) |
| `web/<acteur>/src/app/` | An application's pages and layout: its title, `EtatDeLActeur` with its own service, and `/connexion` on soin, caisse and pharmacie |
| `web/Dockerfile` | One image per application: `docker build --build-arg APPLICATION=soin web` |
| `tests/` | The black-box suite, how it reaches the gateway, the actor table, the network isolation checks, and the dataset checks |

## How the picture grows

Every later feature repeats the same pattern:

- **The application of an actor** is a Next.js workspace in `web/<acteur>/`, built by `web/Dockerfile` into a container that merges `x-application`: the `passerelle` network only. It gets `@lafia/commun` and `@lafia/design` compiled in. The gateway carries its subdomain as a network alias so the application's server reaches the internal entry. It calls its own service and `identite` through the gateway, and never FHIR.
- **The service of an actor** is `services/<acteur>/`: its routes, handed to `creer_service()` from `commun`, and its `regles/`, which say whom it serves, enforced with the guards of `VerificateurDeJetons`: `agent` with the roles it admits, or `citoyen`. `services/Dockerfile` builds it with `commun`; if it speaks FHIR, its Compose entry merges `x-service-fhir`, which puts it on both networks and gives it `NOYAU_URL`, `JETON_CLE_PUBLIQUE` and `LAFIA_DOMAINE`.
- **A new actor** (a laboratoire, later) means one service, one application, and one line in the `Caddyfile`, `import acteur <nom>`, which routes `/api/<nom>/*` to its service, `/api/identite/*` to identite, and nothing else under `/api/`. Compose gains its service, its application and the gateway alias of its subdomain; `web/package.json` gains its workspace. identite learns which roles its application signs in (`services/identite/src/identite/regles/applications.py`). The test suite gains one row in the actor table of `tests/test_acteurs.py`, its subdomain in `tests/test_identite.py`, and its application in the isolation probes of `tests/test_isolement.py`. Each of these is a line added to a list: no existing code changes.
- **Deployment** needs nothing new for an actor: the wildcard record already covers its subdomain (the record for the domain itself serves the site), and `deploiement/deployer.sh` builds its images like the others.
- **The demo dataset** grows with the services: the feature that fixes a resource's shape (a cas de visite, an ordonnance) adds its records to `donnees/`, its translation to `commun/src/commun/fhir/ressources.py`, and its resources to the one transaction of `donnees/src/donnees/chargement.py`.
