# 0010. A Transcription is restricted Markdown in volets, pointing back to its pages

- Status: accepted
- Date: 2026-09-27

## Context

A Transcription (F6) is the reviewed reading of a numérised Document, most often a whole Carnet papier: dozens of pages, several établissements, doctors' handwriting. Reviewers compare it with the scan page by page and correct it by hand; soignants and the citizen read it later, alongside the pages. It must be structured enough to regroup by établissement and date, readable by a person, editable in a browser, safe to render (the machine and the reviewers write it), and stable for years: every Transcription ever saved stays in the noyau.

## Decision

- **Format:** Markdown restricted to headings, paragraphs, bold, italic, lists, tables and images, with a small header and one level-2 heading per volet:

  ```markdown
  ---
  etablissements: CS Kpanroun; CHD Ouémé
  periode: 2015-2021
  ---

  ## consultation · 2019-03-14 · CS Kpanroun · p. 3-4
  Motif : fièvre depuis trois jours. T° 39,2.
  Conclusion : paludisme ; traitement par artéméther-luméfantrine.

  ## analyse · 2019-03-15 · CHD Ouémé · p. 5
  | Examen | Résultat | Unité |
  |---|---|---|
  | Hémoglobine | 10,2 | g/dL |

  ![Feuille de résultats](page:5)

  ## illisible · ? · ? · p. 6
  Écriture illisible ; le patient a été vu en 2019 d'après la page précédente.
  ```

  A volet heading is `## <type> · <date or ?> · <établissement or ?> · p. <pages>`. Types: consultation, analyse, ordonnance, vaccination, hospitalisation, imagerie, certificat, note, illisible, autre. Dates are `AAAA`, `AAAA-MM` or `AAAA-MM-JJ`; volets go in date order where dates are known, undated ones where they sit in the carnet.
- **Photos are references, not copies.** An image is `![légende](page:N)` for a whole page, or `![légende](page:N#x,y,l,h)` for a region in per-mille of the page, cropped at display time. The Transcription stores no image of its own; it points to the pages of its Document.
- **Storage:** a `DocumentReference` of type Transcription, `text/markdown` content in a `Binary`, `relatesTo` `transforms` the scanned Document; each save is a new DocumentReference that `replaces` the previous one (ADR 0007), `docStatus` preliminary until the Contrôle, final after. Its `meta.tag` carries origine `extraction` for the machine's draft, then the reviewers' work is recorded as `Provenance` (Relecture, Contrôle) naming each reviewer.
- **One parser and one renderer**, shared (`commun` for the services, `web/commun` for the applications). The renderer is written for this subset only: it escapes all text, emits no raw HTML, and resolves images only through the `page:` scheme to the service's page route. Anything outside the subset is shown as plain text.

## Consequences

- The "par établissement" view and date ordering are computed from volet headings across every relue Transcription; a later Dépôt simply adds Documents whose volets join the views.
- A reviewer can reorder, split and merge volets as text; the left panel follows the `p.` references.
- The format is readable without Lafia; a future model or tool can produce it; changing it later means migrating stored Transcriptions, hence this ADR.
- Rejected: FHIR `Composition` per volet (heavy to edit by hand, and a carnet's content is history, not a clinical document Lafia authored); HTML (unsafe to render and to edit); storing crops as new Binaries (duplicates the scan and drifts from it).
