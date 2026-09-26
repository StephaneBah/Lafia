# PRD F2: Identité et données — comptes, officines, code carnet, jeu de démonstration et tarifs

## Problem Statement

F1 left a stack where every service verifies tokens, but nobody issues them. No agent can sign in, so no application can show who writes in the dossier. The citoyen cannot open a carnet. The test suite forges its own tokens with the stack's private key, a key that would forge any médecin once `identite` issues real tokens. And the noyau is empty: no établissement, no soignant, no patient, no tarif. Every later feature (soin, caisse, pharmacie, citoyen, accès d'urgence) needs someone signed in and something to work on.

## Solution

`identite` becomes real. Agents (médecins, infirmiers, caissiers, pharmaciens) sign in with an identifiant and a mot de passe on the application of their role. An officine signs in under its own name on the pharmacie application. The citoyen signs in with their NPI and the code carnet printed on their latest reçu, and `identite` issues that code when the soin application asks for it at the end of a visite. A session lasts a shift, renews its short-lived token without the agent noticing, ends after inactivity or on déconnexion, and resists guessing. The soin, caisse and pharmacie applications gain a sign-in page that lists the demo accounts.

A synthetic dataset is loaded at every start: five real Beninese établissements, from the CNHU to a rural centre de santé, two officines, their soignants, caissiers and pharmaciens, about thirty patients, and the tarif of every product and act at each établissement. The same files feed `identite`'s accounts and the noyau, so every token names people and places the noyau knows.

Token contract: `docs/adr/0004-contrat-du-jeton-de-session.md`. Code carnet issuance: `docs/adr/0005-code-carnet-emis-par-application-soin.md`. This spec settles issue #10.

## User Stories

**Agents**

1. As a soignant, I want to sign in on the soin application with my identifiant and mot de passe, so that everything I write carries my name and my établissement.
2. As a caissier, I want to sign in on the caisse application, so that the encaissements I record are mine.
3. As a pharmacien, I want to sign in on the pharmacie application, so that the délivrances I record are mine.
4. As an officine, I want to sign in on the pharmacie application under the officine's name, so that my pharmaciens can check ordonnances without each holding a Lafia account.
5. As an agent who mistypes, I want one message for a wrong identifiant or a wrong mot de passe, so that the page never confirms which identifiants exist.
6. As an agent who opens the wrong application, I want to be told that my account does not open this application, so that I go to the right one instead of meeting a silent refusal.
7. As an agent, I want to stay signed in for my whole shift while I keep working, so that I never retype my mot de passe in the middle of a consultation.
8. As an agent, I want my session to end after 30 minutes without activity, so that a shared desk computer does not stay open under my name.
9. As an agent, I want my session to end after 12 hours whatever happens, so that a forgotten session does not last until the next day.
10. As an agent, I want to sign out in one click, so that the next person at the desk cannot act as me.
11. As an agent, I want the application to show my name, my role and my établissement once signed in, so that I know which identity writes in the dossier.
12. As a jury member, I want the sign-in page of each application to list its demo accounts with their mots de passe, so that I can try every role without asking anyone.

**Citoyen**

13. As a citoyen, I want to open my carnet with my NPI and the code carnet printed on my latest reçu, so that someone who only knows my NPI cannot read it.
14. As a citoyen, I want to type the code with or without its dash, in capitals or not, so that a small typing difference does not lock me out.
15. As a citoyen, I want the code of my latest reçu to replace the previous one, so that an old reçu I threw away opens nothing.
16. As a citoyen, I want my session to last at most an hour, so that a phone shared in the family does not keep my carnet open.
17. As a citoyen, I want my NPI never sent back to the application, so that it never appears in the pages.

**Code carnet**

18. As the soin application, at the end of a visite, I want to obtain a fresh code carnet for the patient's NPI with the soignant's session, so that it can be printed on the reçu (called from F3).
19. As a security reviewer, I want only médecins and infirmiers to obtain a code carnet, so that a caissier, a pharmacien or an officine cannot open anyone's carnet.
20. As a security reviewer, I want every code carnet recorded with the agent and the établissement that asked for it, so that misuse can be traced (ADR 0005).
21. As a security reviewer, I want a code carnet shown only once, when it is issued, and stored only as a hash, so that no one reads it back from `identite`.

**Guessing and sessions**

22. As a security reviewer, I want five failed attempts on the same NPI or identifiant to lock it for 15 minutes, so that a code carnet or a mot de passe cannot be guessed.
23. As a security reviewer, I want a source address that piles up failures to be refused for a while, so that one machine cannot spray guesses across many NPIs.
24. As a security reviewer, I want a lock to hold even against the right credentials, so that a guesser learns nothing from a locked account.
25. As a security reviewer, I want the token carried only in an `httpOnly`, `Secure`, `SameSite=Strict`, `__Host-` cookie and never in a response body, so that client JavaScript never reads it.
26. As a security reviewer, I want sign-in forms posted from another site refused, so that a hostile page cannot sign a user in under an attacker's account.
27. As a security reviewer, I want tokens to live 15 minutes and be renewed only from a live session that `identite` holds, so that a stolen token is short-lived and déconnexion really ends access.
28. As a security reviewer, I want mots de passe, codes carnet and session identifiers stored only as hashes, so that a copy of `identite`'s database opens nothing.
29. As a security reviewer, I want `identite`'s database on a network only `identite` reaches, so that no application and no other service can read accounts.
30. As a security reviewer, I want the private signing key read by `identite` alone, so that neither the operator's shell nor the test suite ever holds a key that forges a médecin.
31. As a security reviewer, I want `identite`'s logs to carry account identifiers and outcomes, never NPIs, names, mots de passe or codes, so that logs leak nothing (SYSTEM_PROMPT security statement).
32. As a developer, I want `identite` to sign with the development key on `localhost` when no key is set, so that the local stack still starts in one command.
33. As an operator, I want `identite` to refuse to start on a real domain without a private key, or with the development key, so that a deployed stack never issues tokens anyone can forge.

**Services and applications**

34. As a service, I want an agent token's `sub` to be the agent's `Practitioner` id in the noyau, so that I can author writes and audit entries without asking `identite`.
35. As the pharmacie service, I want an officine token to name the officine and nothing else, so that its reach follows from its role alone.
36. As the pharmacie service, I want to admit both pharmaciens and officines, so that the officine uses the same application as the hospital pharmacie.
37. As an application, I want `identite` to tell me the connected holder's name and établissement name, so that I show people and places, not identifiers.
38. As an application, I want an expired token renewed before I render the page, without ever reading the token myself, so that the agent never sees an expiry.

**Dataset**

39. As a jury member, I want the platform to hold five real Beninese établissements, from the national hospital to a rural centre de santé, so that the demo looks like the country's health pyramid.
40. As a jury member, I want about thirty plausible synthetic patients from several regions, ages and languages, so that search and carnet show realistic people.
41. As a soignant, I want each patient to carry nationalité, lieu de naissance, adresse down to the quartier, spoken language, and optionally a phone and a personne à prévenir, so that I can identify, reach and talk to them.
42. As a caissier, I want every product and act priced at my établissement, so that no amount is ever typed (used by F4).
43. As a security reviewer, I want every synthetic NPI to start with six zeros and every synthetic phone number to follow a pattern no operator assigns, so that no fixture can be a real person's.
44. As a developer, I want the dataset loaded at every start without deleting anything, so that a redeploy never wipes the demo nor what the jury wrote.
45. As a developer, I want a full reset to be one documented command, so that I can start over when I choose.
46. As a developer, I want the dataset written in Lafia's vocabulary and translated to FHIR by `commun`, so that the noyau holds exactly what a service would have written.
47. As a developer, I want `identite`'s accounts and the noyau's `Practitioner`s and `Organization`s to come from the same files, so that every token's `sub` and `etablissement` resolve in the noyau.
48. As a later feature (F3 to F5), I want to add my resources (cas, mesures, allergies, ordonnances, encaissements, délivrances) to the same files and loader, so that the dataset grows with the services that own each shape.

**Tests and operations**

49. As a developer, I want the suite to get valid tokens by signing in with demo accounts, locally and in production, so that it exercises the real issuance and never holds the private key.
50. As a developer, I want the tests of malformed tokens to keep running locally with the development key, so that token verification stays covered.
51. As a developer, I want lockout tests to use accounts and NPIs reserved for tests, so that running the suite in production never locks a jury member out of a demo account.
52. As an operator, I want the VM preparation script to add a missing secret to an existing `.env` without touching the others, so that the live VM gets `identite`'s database password without losing HAPI's.
53. As an operator, I want the deployment runbook to stop copying the private key to my shell, so that the key never leaves the VM.

## Implementation Decisions

**`identite` service**

- It keeps its place on the `passerelle` network, never speaks FHIR, and gains its own PostgreSQL 17 (`base-identite`) on a new internal network shared with nothing else. It reads `LAFIA_DOMAINE`, `JETON_CLE_PRIVEE` and its database password from the environment.
- What it stores:
  - **comptes**: identifiant, mot de passe hash, role, `sub` (the agent's `Practitioner` id, or the officine's `Organization` id), établissement id for agents, and the names shown in applications (the holder's, the établissement's or the officine's);
  - **codes carnet**: one per NPI, with its hash, the agent and établissement that asked for it, and when;
  - **sessions**: the hash of a random identifier, the holder, when it started, its last renewal;
  - **failed attempts**: counters per identifiant, per NPI and per source address, over a 15-minute window.
- Hashes: argon2id for mots de passe and codes carnet; SHA-256 for session identifiers, which are random and long.
- The schema is created by `identite` at startup; no migration tool in v1.
- At startup it loads its accounts from the dataset files built into its image: an account is created or updated by identifiant, and accounts absent from the files are left alone. Demo codes carnet are inserted only for NPIs without a code, never over a code issued since.
- The application is read from the request's host: `<application>.<LAFIA_DOMAINE>`, public or internal entry. Roles each application signs in: soin (médecin, infirmier), caisse (caissier), pharmacie (pharmacien, officine), citoyen (citoyen).
- Routes, all under `/api/identite`:

  | Method and path | Who | Behaviour |
  |---|---|---|
  | `POST /connexion` | form: identifiant, mot de passe | Agents and officines. Success: both cookies, 303 to `/`. Failure: 303 to `/connexion?erreur=…` with `identifiants`, `application` or `verrouille`, no cookie. |
  | `POST /citoyen/connexion` | form: NPI, code | On the citoyen application only. Same answers; an unknown NPI and a wrong code give the same `identifiants`. |
  | `POST /session/renouveler` | renewal cookie | 204 with a new token cookie; 401 and both cookies cleared when the session is over. |
  | `POST /deconnexion` | anyone | Ends the session, clears both cookies, 303 to `/connexion`. |
  | `GET /session` | any valid token | The holder: agent `{sub, role, etablissement, nom, nom_etablissement}`; officine `{sub, role, nom}`; citoyen `{sub, role}`, never the NPI. |
  | `POST /codes-carnet` | médecin, infirmier | JSON `{npi}`; 201 `{code}` shown once, replacing the previous code of that NPI. 403 for any other role, 422 for a malformed NPI. |
  | `GET /comptes-de-demonstration` | public | The demo accounts of the roles the requesting application signs in: identifiant, mot de passe, role, établissement or officine name. Accounts reserved for tests are never listed. |
  | `GET /sante` | public | Unchanged. |

- Form posts are accepted only when their `Origin` is the requesting application's own origin; otherwise 403.
- Cookies, both `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/`, without `Domain`: `__Host-session` holds the token, with a `Max-Age` of its 15-minute life; `__Host-renouvellement` holds the session identifier, with a `Max-Age` of the session's remaining life.
- Session limits: agents and officines, 12 hours at most and 30 minutes without renewal; citoyen, one hour at most. A renewal counts as activity.
- Guessing: five failures on one identifiant or NPI lock it for 15 minutes, even against the right credentials; 50 failures from one address within 15 minutes refuse that address until the window passes; a success resets the identifiant's or NPI's counter. The source address is the one the gateway forwards; Caddy does not trust a forwarded address sent by the client.
- Code carnet: 6 characters from the numéro d'ordonnance's alphabet (no `0 O 1 I L`), shown as two groups, `K7M-4PX`. Input is normalised: dashes and spaces removed, capitals.
- NPI: 13 digits. Anything else is refused before any lookup.
- Signing: EdDSA, Ed25519, with `JETON_CLE_PRIVEE`. Without it, on `localhost` only, the development key; on any other domain, `identite` refuses to start without a key or with the development key, by the same rule as the services.
- Logs: account identifiers and outcomes only.

**`commun`**

- Token contract, per ADR 0004: `Role` gains `officine`. A verified token is one of three holders: `Agent` (`sub`, role, `etablissement`), `Officine` (`sub`), `Citoyen` (`sub`, `npi`). An officine token carrying an `etablissement` or an `npi` is refused. A guard admits a set of agent roles together with officines, for pharmacie. Claim names and the lifetime constants are defined once and used by both `identite`, which signs, and the services, which verify. Signing stays in `identite`: services never hold the private key.
- FHIR translation: a module turns the dataset's records into FHIR resources: établissement and officine into `Organization`, agent into `Practitioner`, patient into `Patient`, tarif into `ChargeItemDefinition`. It also defines the code systems and identifier systems Lafia uses. F3 adds the reading direction when soin first reads a patient.
- The FHIR client gains sending a transaction bundle, used by the loader, and later by services.

**FHIR shapes**

- `Organization`: fixed id, name, type (from a Lafia code system: CHU national, CHU départemental, CHU de zone, centre de santé, officine), address (département, commune).
- `Practitioner`: fixed id, name, qualification (médecin, infirmier, caissier, pharmacien). An officine has no `Practitioner`: it acts as its `Organization`.
- `Patient`:
  - fixed id;
  - NPI in `identifier` (system `https://npi.gouv.bj`);
  - name, gender, birth date;
  - place of birth and nationality through the standard HL7 extensions;
  - address: `state` département, `city` commune, `district` arrondissement, `line` quartier;
  - optional phone in `telecom`;
  - optional personne à prévenir in `contact`: name, relationship, phone;
  - spoken languages in `communication` as BCP-47 codes (`fr`, `fon`, `yo`, `bba`, `ddn`, `ajg`…).
- `ChargeItemDefinition`: one per product or act per établissement.
  - The product or act is its `code`, in Lafia's catalogue code system, with the ATC code as a second coding for medicines.
  - The price in FCFA (`XOF`) is a base price component.
  - The établissement is in `useContext` (venue, the `Organization`).
  - An `identifier` combines the établissement and the product code, so the caisse finds a tarif with one search.
  - Officines have no tarif: their prices live in their own software.

**Dataset (`donnees/`)**

- Hand-written files in Lafia's vocabulary, with fixed ids: établissements, officines, the catalogue of products and acts with their tarifs per établissement, agents (identifiant, demo mot de passe, role, établissement, `Practitioner` id, name), patients, and demo citoyens (NPI and code carnet). Mots de passe and codes are public: every datum is synthetic.
- Établissements, real public facilities; everyone and everything else is synthetic:

  | Établissement | Commune | Level |
  |---|---|---|
  | CNHU Hubert Koutoukou Maga (CNHU-HKM) | Cotonou | national |
  | CHU de la Mère et de l'Enfant Lagune (CHU-MEL) | Cotonou | national, mother and child |
  | CHUD Borgou-Alibori | Parakou | départemental |
  | CHU de Zone Abomey-Calavi/Sô-Ava | Abomey-Calavi | zone |
  | Centre de santé de Kpanroun | Abomey-Calavi | centre de santé |

- Two officines with invented names, one in Cotonou and one in Abomey-Calavi, one account each.
- Agents: about twelve soignants across the établissements, including one médecin with two accounts (CHU de Zone Abomey-Calavi and Kpanroun) to show the one-établissement rule; one caissier and one pharmacien per établissement. Plus accounts reserved for the lockout tests, never listed on a sign-in page.
- About thirty patients:
  - names from several regions and languages, men and women, children (CHU-MEL) and older adults;
  - Beninese nationality for most, and a few residents of neighbouring countries who hold an NPI;
  - 13-digit NPIs starting with six zeros, with a few NPIs reserved for the lockout tests;
  - phones and personnes à prévenir for some;
  - no clinical data.
- A catalogue of 20 to 40 products and acts, each priced at every établissement, with prices that differ by level.

**Loader**

- A one-off container (`chargement`), built with `commun` and `donnees/`, on the noyau network only. It runs at every `docker compose up`, once the noyau is healthy, and sends one FHIR transaction of `PUT`s with fixed ids, then exits.
- It never deletes. A resource whose content has not changed gets no new version.
- `docker compose up -d --build --wait` and the deployment script still succeed with it.
- A full reset is `docker compose down -v`, then `up`.

**Applications**

- `web/commun` gains:
  - the sign-in page: identifiant, mot de passe, a message per `erreur`, and the demo accounts from `identite`;
  - déconnexion, as a form post;
  - the display of the connected holder from `identite`'s `/session`;
  - token renewal before rendering. When the token cookie is gone but the renewal cookie is present, the application's server calls `/session/renouveler` through the gateway's internal entry, then redirects to the same address with the cookies `identite` set. The application never reads the token.
- soin, caisse and pharmacie serve `/connexion` with the shared page. Their home shows a link to it without a session, and the holder's name, établissement and déconnexion with one. The citoyen application is unchanged until F6.
- The session types gain the officine.

**Services**

- pharmacie admits pharmaciens and officines. Its `/session` answers an officine with `{sub, role: "officine"}`.
- soin, caisse and citoyen change only through `commun`.

**Operations and docs**

- Compose: `base-identite`, the `identite` network, `identite`'s environment, the `chargement` container, and memory limits for both new containers.
- `.env.example`: `identite`'s database password. `JETON_CLE_PRIVEE` is now read by `identite`.
- The VM preparation script adds a missing variable to an existing `.env`, keeping existing values.
- The deployment runbook no longer copies the private key; the suite signs in instead.
- `docs/architecture.md`: the new containers and network, and who reaches whom.
- The technical document, updated at the end of the work: `identite`'s routes (`/session` replaces `/moi`), the dataset section (five établissements, two officines), and the open points (code carnet validity is settled by ADR 0005).
- `SYSTEM_PROMPT.md`, `CONTEXT.md` and ADRs 0003 to 0005 were updated during grilling.

## Testing Decisions

- A good test treats the stack as a black box and asserts what a user or an attacker observes: status codes, redirect targets, cookie attributes, JSON bodies, page text. It never inspects `identite`'s tables. It uses resource ids and synthetic accounts only; test names carry no NPI and no name.
- **Seam 1, the gateway (main seam).** Through `https://<application>.<domaine>`:
  - agent sign-in for every demo role on its application: 303 to `/`, both cookies with the required attributes, a token that lives 15 minutes;
  - each service's `/session` answering that agent, with a `sub` that is its `Practitioner` id;
  - failures: wrong mot de passe and unknown identifiant give the same answer; a role on the wrong application; a form from another origin;
  - lockout after five failures, holding against the right credentials, on accounts and NPIs reserved for tests;
  - renewal from the renewal cookie, refused after déconnexion;
  - officine sign-in on pharmacie, and pharmacie's `/session` answering it; the officine refused on caisse and soin;
  - citoyen sign-in with a demo NPI and code; `/api/citoyen/session` answering without the NPI; two sign-ins giving two different `sub`s;
  - code carnet issued by a signed-in médecin, then used to sign in; issued again, the old code refused and the new one accepted; refused to a caissier;
  - `identite`'s `/session` for each kind of holder;
  - the demo accounts listed per application, without the accounts reserved for tests;
  - the `/connexion` page, and the home page naming the connected agent and établissement.
- **Seam 2, docker on the machine running the stack.** Reading the noyau from inside a service container, the dataset is checked: the five établissements and two officines, every patient by NPI, a tarif for every product at every établissement, and every account's `sub` and `etablissement` resolving to a `Practitioner` or `Organization`. Running the loader a second time leaves every version unchanged. The isolation probes add that no application and no FHIR service reaches `base-identite`, and that `chargement` is on the noyau network only. These checks are skipped when the stack under test runs elsewhere, as today.
- **Tokens in the suite.** Valid tokens come from signing in with demo accounts read from `donnees/`. Malformed tokens (expired, valid for a year, wrong claims, other key, unsigned) are forged with the development key, locally only, and skipped against another deployment. The actor table gains the officine role for pharmacie.
- Not exercised: the per-address limit, which would lock the machine running the suite out of every other test.
- No unit tests on `commun`: the FHIR translation is exercised by seam 2, the token contract by seam 1.
- Prior art: `tests/test_acteurs.py` (one table per actor), `tests/test_citoyen.py` (the NPI never in the page), `tests/test_isolement.py` (docker probes), and the fixtures in `tests/conftest.py`.

## Out of Scope

- Patients without an NPI, and foreign identity documents.
- Clinical history in the dataset: cas, visites, mesures, allergies, ordonnances, encaissements, délivrances (F3 to F5).
- Account administration: creating accounts, changing or resetting a mot de passe, registries of professionals and établissements.
- An API for officines' own software (designed, not built).
- The citoyen's sign-in screen (F6), printing the reçu and asking for the code at the end of a visite (F3), the officine's check of an ordonnance and its declaration of sold lignes (F5).
- The relation de soin and `AuditEvent`s (F3); accès d'urgence (F7).
- SMS, one-time codes, second factors.
- Rate limiting at the gateway.
- Styling beyond legibility: F0 restyles the sign-in page.

## Further Notes

- Issue #10 is settled here:
  - the cookie flags set by `identite`;
  - issuance matching verification (ADR 0004);
  - the development-key rule for `identite`;
  - `/api/identite/session`;
  - the citoyen `sub` that is not the NPI;
  - the suite signing in instead of holding the key;
  - guessing limits on citoyen sign-in;
  - the Bearer header reconciled in `SYSTEM_PROMPT.md`.
  
  Its two F3 points (the FHIR client's reads, and the test seam for writes) stay with F3.
- The NPI's length (13 digits) comes from non-official sources; ANIP's own pages do not state it. If it proves to be 10, only the dataset and one format check change.
- The five établissements are real public facilities, named to make the demo recognisable; no real person, account or clinical fact is attached to them.
- F0 has not landed: the sign-in page is plain, and gets restyled with the design system.
