# 0002. Dossier access follows a relation de soin

- Status: accepted
- Date: 2026-09-25

## Context

Accès d'urgence is defined as bypassing normal access, but normal access was never defined. Left open, any authenticated soignant in the country could open any dossier by typing an NPI, and accès d'urgence would mean nothing. Patient-granted access (a code, a card) excludes unconscious patients and people who cannot read.

## Decision

- A soignant opens a dossier only through a **relation de soin**: their établissement holds an open cas de visite for the patient, or they open or continue one now with the patient present.
- The caisse and the pharmacie reach an ordonnance, never a dossier, through the numéro d'ordonnance the patient presents.
- Any other access is an **accès d'urgence**: a stated reason, a restricted vital view, an `AuditEvent` flagged as emergency and visible to the citoyen.
- The rule lives in the `soin` service's `regles/`, evaluated from the token's établissement and the patient's open `EpisodeOfCare`s.

## Consequences

- Accès d'urgence has a real meaning and is rare, so each one is worth reading in the access log.
- Opening a cas is the gesture that creates the relation: the soignant search by NPI leads to "ouvrir un cas" or "continuer un cas", not to the full dossier directly.
- Rejected: open access with audit only (accès d'urgence becomes decorative); patient-granted access (excludes the unconscious and the non-reading).
