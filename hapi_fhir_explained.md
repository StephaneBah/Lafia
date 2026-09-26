# HAPI FHIR, explained

## 1. First, FHIR (the standard)

**FHIR** (pronounced "fire") is the international standard for exchanging health data. It's published by HL7, the body that writes health IT standards. It defines two things:

**Resources.** These are standard building blocks for health information, each with a fixed JSON shape. Some examples:
- `Patient` is a person.
- `Encounter` is a visit.
- `Observation` is a measurement: blood pressure, a lab result.
- `Condition` is a diagnosis.
- `MedicationRequest` is one prescription line.
- `AuditEvent` records who accessed what.

A `Patient` looks roughly like this:
```json
{
  "resourceType": "Patient",
  "id": "123",
  "identifier": [{ "system": "https://npi.gouv.bj", "value": "0123456789" }],
  "birthDate": "1985-04-12"
}
```

**A REST API.** Every FHIR server answers the same kinds of HTTP calls:

| Call | Meaning |
|---|---|
| `GET /Patient/123` | read one resource |
| `POST /Observation` | create one |
| `PUT /Patient/123` | update it (a new version is created) |
| `GET /Patient?identifier=...` | search |
| `GET /Patient/123/_history` | see every past version |
| `GET /metadata` | "what can you do?" (returns a `CapabilityStatement`) |

Because the format and the API are standard, any system that speaks FHIR can talk to any FHIR server.

## 2. What HAPI is

**HAPI FHIR** is the best-known open-source implementation of FHIR, written in Java. The **HAPI FHIR JPA Server** is a complete, ready-to-run FHIR server:

- It receives FHIR HTTP requests.
- It checks that resources are well formed.
- It stores them in a database. Here that's PostgreSQL, reached through JPA/Hibernate, which is why it's called the "JPA" server.
- It builds search indexes, so queries like "all Observations for this patient" work.
- It keeps every version of every resource.

It ships as a Docker image (`hapiproject/hapi`). You don't write any code for it: you point it at a database with a few environment variables and it runs. That is exactly what the `noyau` entry in `docker-compose.yml` does.

## 3. Its role in Lafia: the noyau

HAPI **is** the noyau: the single place where all medical data lives.

```
app soin ──► service soin ──FHIR──► HAPI (noyau) ──► PostgreSQL
app caisse ─► service caisse ─FHIR─┘
```

Each Lafia concept is a FHIR resource stored in HAPI (the mapping table in `SYSTEM_PROMPT.md`):
- A cas de visite is an `EpisodeOfCare`.
- A visite is an `Encounter`.
- A mesure is an `Observation`.
- A ligne d'ordonnance is a `MedicationRequest`.

The services translate "domain language" into FHIR calls. For example:
- **Finding a patient by NPI:** `GET /fhir/Patient?identifier=https://npi.gouv.bj|0123456789`
- **The caisse finding an ordonnance:** `GET /fhir/MedicationRequest?group-identifier=ORD-7K4-M2P`

## 4. Why it helps us

- **No database schema to design.** HAPI already knows how to store and search patients, visits, prescriptions and so on. We saved days of work.
- **Interoperability for free.** A future laboratoire or télémédecine service, or even a third-party hospital system, only has to "speak FHIR" to plug in. That's the core promise of the project.
- **History built in.** An update creates a new version and old ones stay readable. That directly satisfies the "records are append-only" invariant.
- **Standard resources for the tricky parts.** The access log (`AuditEvent`) and the tarifs (`ChargeItemDefinition`) are already defined by the standard.
- **Credibility.** It uses a recognised international standard with its reference implementation, in default configuration. Nothing is homemade or proprietary.

## 5. What HAPI does *not* do (why the services exist)

In default configuration, HAPI has **no authentication and no business rules**. Anyone who can reach it can read and write everything. Two consequences:

- **The noyau is hidden.** It publishes no port, and it sits on an internal `noyau` network that only HAPI, its database and the services share. The browser apps can't reach it at all.
- **Every Lafia rule lives in the services:**
  - who may see what (roles, relation de soin);
  - writing an `AuditEvent` on every access;
  - generating numéros d'ordonnance;
  - looking up tarifs.

  HAPI stays a pure, standard data store. That split is architecture invariant 3.

## 6. Practical things to know

- **It's heavy.** It's a Java app and needs about 1–2 GB of memory. That's why it gets an explicit memory limit (`-Xmx1g` heap, 2 GB container).
- **It's slow to start.** The first boot creates hundreds of tables in PostgreSQL and can take 1–3 minutes. That's why `soin` waits for the noyau to be "healthy" before starting.
- **Its data lives in PostgreSQL.** That's the `noyau-donnees` volume, which is why the data survives a restart.
- **Its image is minimal.** It has no shell and no curl inside, so writing its health check takes a small trick. That's the open question in the current ticket.
- **In this ticket it's the tracer bullet's endpoint.** `soin` calls `GET /fhir/metadata` and HAPI answers with a `CapabilityStatement` saying `"fhirVersion": "4.0.1"` (FHIR R4). If that value comes back through the gateway, the whole chain works: browser → Caddy → soin → HAPI → PostgreSQL.

If you want to explore FHIR hands-on, the public HAPI test server (hapi.fhir.org) lets you try these REST calls in a browser. Use only fake data there, never real patients.