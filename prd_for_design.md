# PRD: Lafia design system and interfaces

## Problem Statement

Lafia gives every Beninese citizen one shared health record, reached by their NPI. The people it serves are not a connected, literate population: many do not read, many use an entry-level Android phone shared within the family, some have low vision or are deaf. Health software in this context usually fails them twice: screens built on text they cannot read, and professional tools so slow that queues form at the cashier while someone re-types a prescription.

The design must make the platform usable at first sight by someone who cannot read, and fast for professionals working under pressure.

## Solution

A design system and a set of interfaces where the **illustration carries the meaning**: a citizen understands where they stand in their care (what to pay, what to collect, how to take a treatment) from pictures, with words as support. Professional interfaces share the same system, tuned for speed and density.

## Users

| Persona | Situation | What the design must do |
|---|---|---|
| Awa, 42, market vendor, Dantokpa | Does not read; shares her son's entry-level phone | Show what to pay, collect and take, without text |
| Koffi, 67, diabetic, Parakou | Low vision; outdoors in bright sunlight | Large type, strong contrast, generous targets |
| Rachida, 29, deaf | Communicates in writing and sign language | Carry nothing by sound; every state visible |
| Infirmier, rural health centre | Long queue, one shared computer | Find a patient by NPI and write a visite fast |
| Caissière, CHU emergency | Queue at the counter | Open a prescription by number, tick lines, cash in, no re-typing |
| Pharmacien, private pharmacy | Partial stock | Dispense line by line, see allergies before handing over |

## User Stories

1. As a citizen who cannot read, I want to see at a glance whether my ordonnance is paid, so that I know whether to go to the caisse or the pharmacie.
2. As a citizen who cannot read, I want my treatment shown as pictures of when and how many, so that I take it correctly.
3. As a citizen, I want to see my open cas de visite as a simple story, so that I know where I stand.
4. As a citizen, I want to see who opened my dossier and when, so that I trust the system.
5. As a citizen with low vision, I want to enlarge text to 200% without losing content, so that I can read on my phone.
6. As a deaf citizen, I want every alert shown visually, so that I miss nothing.
7. As an infirmier, I want to find a patient by typing an NPI, so that I reach the dossier in one step.
8. As a médecin, I want allergies and long-term treatments visible before anything else, so that I prescribe safely.
9. As a médecin, I want to read a cas de visite as one timeline across établissements, so that I stop starting from zero.
10. As a médecin, I want to see a mesure as a curve over time, so that I judge the trend.
11. As a caissière, I want to open an ordonnance from its number and tick available lines, so that I cash in without re-typing.
12. As a pharmacien, I want an unmissable allergy alert at dispensing, so that I never hand over a dangerous product.
13. As a soignant in a vital emergency, I want the vital information of an unconscious patient on one screen, so that I act in seconds.

## Design principles

1. **Understand without reading.** The illustration carries the information; text confirms it. Test: shown for five seconds, a non-reader says correctly what the screen asks of them.
2. **One screen, one decision.** Citizen screens ask for one action at a time.
3. **Icon, word, colour: always together.** Colour never carries meaning alone.
4. **Fast for professionals.** Keyboard-reachable, dense where density saves time, no step that re-asks known data.
5. **Local by default.** Beninese faces, names and places; amounts in FCFA; French copy in everyday words.

## Visual direction

Taken from the two reference images supplied with this PRD.

**Illustration style.** Flat, geometric, friendly. Solid fills, near-black outlines of constant weight, rounded corners, overlapping cards, everyday objects drawn as simple shapes (a card, a pill, a clock in a white disc). No gradients inside illustrations, no photographs.

**Palette.** Measured from the references. Contrast ratios computed against WCAG 2.2.

| Role | Hex | Use | Contrast rule |
|---|---|---|---|
| Bleu royal | `#3648C0` | Primary actions, links, key illustration fills | 7.4:1 on white: valid for all text |
| Bleu denim | `#4E72AE` | Header bands, large surfaces | White text on it at 4.8:1: normal text AA only. Never as text on the pale background (4.2:1, fails) |
| Pervenche | `#C0C6FC` | Selected states, soft surfaces, secondary illustration fills | Ink text only (10:1). Royal text on it fails (4.5:1) |
| Fond pâle | `#EAF0FC` | Page background | Ink text 14:1 |
| Ardoise | `#242A36` | Illustration panels, optional professional dark theme | White text 14:1, pervenche 8.7:1 |
| Encre | `#121212` | Illustration outlines, body text | |
| Blanc | `#FFFFFF` | Cards, surfaces | |

Semantic colours (paid, partial, to collect, allergy, emergency) are to be proposed. Each must reach 4.5:1 against its surface and always ship with its pictogram and label, so red and green are never the only distinction.

**Typography.** Atkinson Hyperlegible Next, designed for low-vision readers, full French diacritics. Citizen body text 18px minimum; professional body text 16px.

**Shape.** Generous radii, soft shadows under white cards on the pale background, as in the second reference. Touch targets 48px minimum.

## Pictogram set

A consistent SVG family in the illustration style, each tested for meaning without its label:

- **Treatment:** matin, midi, soir, nuit; avant / après le repas; number of tablets; number of days
- **Ordonnance states:** à payer, payé, à retirer, retiré en partie, retiré
- **Care:** cas en cours, cas terminé, visite, analyse en attente, résultat disponible
- **Places and people:** caisse, pharmacie, laboratoire, établissement, soignant
- **Safety:** allergie, urgence, qui a consulté mon dossier

## Screens

In delivery order. Each actor has its own application (`web/citoyen`, `web/soin`, `web/caisse`, `web/pharmacie`), all built on the shared design system `web/design`. See `docs/adr/0001-une-application-par-acteur.md`.

**1. Design system** (`web/design`). Tokens (colour, type, spacing, radius, shadow), components with all states: buttons, inputs, NPI field, code field, status badge, ordonnance line, timeline item, alert, card, table.

**2. Application citoyen** (mobile, 360px wide):
- Sign-in: NPI plus code carnet, the receipt drawn so the citizen knows where to find the code
- Carnet home: what is happening now in my care
- My ordonnance: each line with its state pictogram
- My treatment: posology as pictograms
- My cas de visite: the story, step by step
- Who opened my dossier

**3. Printed receipt.** The paper the patient carries: numéro d'ordonnance large and readable aloud (`ORD-7K4-M2P`) with its QR code, posology pictograms per line, and the code carnet that opens the citizen application.

**4. Application soin** (desktop and tablet):
- Search by NPI, leading to "ouvrir un cas" or "continuer un cas" (the relation de soin), never straight to the dossier
- Patient summary with allergies first
- Cas de visite timeline across établissements
- New visite form
- Issue an ordonnance
- Mesure curve

**5. Application caisse:** open by numéro, tick lines priced from the tarif (no amount typed), total, cash in, receipt.

**6. Application pharmacie:** paid lines, partial dispensing, allergy alert.

**7. Accès d'urgence** (in the soin application): stated reason, then the vital information card.

## Constraints

- Citizen: entry-level Android, 360 × 640 viewport, outdoor light, shared device.
- Professionals: shared desktop or tablet, keyboard use, long sessions.
- French everyday vocabulary; the domain terms in `CONTEXT.md` are the ones used in the UI.
- Amounts `12 500 FCFA`; dates `25/09/2026`; NPI shown in digit groups for reading aloud.
- All data shown is synthetic, with Beninese names and places.

## Accessibility acceptance

- WCAG 2.2 AA on every screen; text contrast 4.5:1 minimum, 7:1 targeted on citizen screens.
- Text enlarged to 200% loses no content or function.
- Every state conveyed by pictogram and label, never colour alone; nothing conveyed by sound.
- Every interactive element reachable by keyboard, with a visible focus.
- Every pictogram has a text alternative.
- Targets 48px minimum on citizen screens.

## Out of Scope

Voice, offline states, USSD and SMS channels, a marketing site, citizen dark mode.

## Deliverables

- Tokens as CSS custom properties and as JSON, named by role (`--color-action`, not `--blue-1`)
- Component sheet with every state
- Screens listed above
- Pictograms as individual SVG files, outline weight and grid specified
- A one-page charte graphique: palette with its contrast rules, type scale, illustration dos and don'ts

The tokens, pictograms and components live in the `web/design` workspace package, consumed by every application. The charte graphique and component sheet go to `docs/design/` and become the source for the project's design skill used by coding agents.