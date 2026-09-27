# 0008. Scanned Documents live in the noyau, as FHIR Binary

- Status: accepted
- Date: 2026-09-27

## Context

The Reprise (F5) turns citizens' paper medical history into Documents: several pages each, images or PDF. Invariant 1 puts all medical data in the noyau; invariant 9 forbids depending on a provider-managed service on the critical path. Three places could hold the files: the noyau itself, an S3-compatible object store beside it, or a cloud blob service.

## Decision

- Each page is a FHIR `Binary` in the noyau (HAPI stores it in its PostgreSQL). The `DocumentReference` lists its pages as `content[].attachment` with `url` = `Binary/<id>`, `contentType`, `size` and `title`.
- Pages are compressed by the application before sending: JPEG at most 1600 px on the long side, aiming at 1 MB, hard limit 3 MB per page and 20 pages per Document; PDF accepted up to 3 MB. The service refuses anything larger.
- Documents are served to applications only through their service, which reads the `Binary` and streams it, after the same role and relation checks and audit as any read.

## Consequences

- One backup covers everything; the invariants hold; nothing new to run.
- The noyau's database grows with the Reprise: about 1 MB per page. At national scale this outgrows one PostgreSQL, so the path forward is written now: move `Binary` content to a MinIO container (S3 API, portable) and keep only the `DocumentReference` in the noyau, its `attachment.url` pointing to the object. The `DocumentReference` shape does not change, so readers are untouched.
- Rejected for v1: MinIO now (one more container and its backups before any volume justifies it); Azure Blob (breaks invariant 9).
