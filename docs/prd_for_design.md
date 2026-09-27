# PRD: Lafia design: product site, design system and applications

> Brief for Claude Design. Attach the two reference images named under *Visual language*. Everything the user sees is in French. This brief is in English and uses the French domain terms exactly as they appear in the interface.

## Problem Statement

Lafia gives every Beninese citizen one shared health record, found by their NPI alone. Many of the people it serves are not connected or literate. Many cannot read, many share an entry-level Android phone with their family, and some have low vision or are deaf. Health software here usually fails them twice. Its screens rely on text they cannot read, and its professional tools are so slow that queues form at the caisse while someone re-types a prescription.

Lafia also needs a front door. Each actor's application lives at its own address (`soin.lafia.stephanebah.page`, `caisse.lafia.stephanebah.page`, …), sealed off from the others by design. Nobody should have to memorise a subdomain. Every visitor, whether citizen, professional, ministry official or jury member, needs to understand in one minute what Lafia changes and why it can be trusted with health data.

The design must work at first sight for someone who cannot read, be fast for professionals under pressure, and make the vision clear to decision-makers.

## Solution

One visual language in which **the illustration carries the meaning** and words confirm it. It must feel alive and smooth: every interaction answers at once, and motion shows what just happened. Lafia has its own signature, never a template look. Three surfaces share it:

1. **The product site** at `lafia.stephanebah.page`. It tells the vision, shows how the system is designed (the change it brings, not the technology), lists the services open today and those coming next, and opens the door to each application.
2. **The citizen application.** Citizens understand from pictures where they stand in their care: what to pay, what to collect, how to take a treatment.
3. **The professional applications** (soin, caisse, pharmacie). They use the same system, tuned for speed and density.

## Map of the product

| Address | Surface | For whom | Status |
|---|---|---|---|
| `lafia.stephanebah.page` | Product site | Everyone: citizens, professionals, institutions, partners | To design |
| `citoyen.lafia.stephanebah.page` | Application citoyen: the carnet | Citizens | v1 |
| `soin.lafia.stephanebah.page` | Application soin | Médecins, infirmiers | v1 |
| `caisse.lafia.stephanebah.page` | Application caisse | Caissiers | v1 |
| `pharmacie.lafia.stephanebah.page` | Application pharmacie | Pharmacies d'établissement, officines | v1 |

Each application is a separate site with its own sign-in. A caisse account never opens a dossier médical. This isolation is a security feature, and the site presents it as one. The product site is the only page that links to every application. Each application's header carries the Lafia mark, which links back to the site.

## Users

| Persona | Situation | What the design must do |
|---|---|---|
| Awa, 42, market vendor, Dantokpa | Does not read; shares her son's entry-level phone | Show what to pay, collect and take, without text |
| Koffi, 67, diabetic, Parakou | Low vision; outdoors in bright sunlight | Large type, strong contrast, generous targets |
| Rachida, 29, deaf | Communicates in writing and sign language | Carry nothing by sound; every state visible |
| Infirmier, rural health centre | Long queue, one shared computer | Find a patient by NPI and write a visite fast |
| Caissière, CHU emergency | Queue at the counter | Open an ordonnance by its numéro, tick lines, cash in, no re-typing |
| Pharmacien, private pharmacy | Partial stock | Dispense line by line, see allergies before handing over |
| Décideuse, ARS or ministry | Judges whether Lafia can serve the whole country | Explain the change, interoperability and data protection without technical terms |
| Jury member, partner developer | Wants to try the platform now | Reach each application and a demo account in one click |

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
11. As a caissière, I want to open an ordonnance from its numéro and tick available lines, so that I cash in without re-typing.
12. As a pharmacien, I want an unmissable allergy alert at dispensing, so that I never hand over a dangerous product.
13. As a soignant in a vital emergency, I want the vital information of an unconscious patient on one screen, so that I act in seconds.
14. As a visitor from an institution, I want to understand in one scroll what Lafia changes for a patient and how it protects health data, so that I can judge whether it can scale nationally.
15. As a professional, I want to reach my application from the Lafia address in one click, so that I do not have to remember its subdomain.
16. As a citizen, I want an "Ouvrir mon carnet" button on the home page, so that I reach my carnet without knowing its address.
17. As a jury member, I want a demo account next to each application, so that I can try it right away.
18. As a decision-maker, I want to see which services come next, so that I see the platform grows without being rebuilt.

## Design principles

1. **Understand without reading.** The illustration carries the information; text confirms it. The test: after five seconds on the screen, a person who cannot read says correctly what it asks of them.
2. **One screen, one decision.** Citizen screens ask for one action at a time.
3. **Icon, word, colour: always together.** Colour never carries meaning alone.
4. **Fast for professionals.** Everything is reachable by keyboard. Screens are dense where density saves time, and no step asks again for data already known.
5. **Local by default.** Beninese faces, names and places; amounts in FCFA; French copy in everyday words.
6. **Trust you can see.** Security is shown, not claimed: who opened the dossier, why an emergency access happened, what each role can see.
7. **One door per actor.** Every surface says which actor it serves, and the site gets anyone to their door in one click.
8. **Smooth, and fast above all.** Every touch gets a response within 100 ms. Motion connects one state to the next so the eye follows what changed, and never makes anyone wait: the user can always act before an animation ends.

## Visual language

The two reference images supplied with this brief set the direction.

### Illustration

**Style.** Flat, geometric and friendly. Solid fills and near-black outlines of constant weight. Rounded corners and overlapping cards. Everyday objects drawn as simple shapes: a card, a pill, a clock in a white disc. No gradients inside illustrations, no photographs, no 3D.

**Where.** The product site uses full scenes. The citizen application uses spot illustrations at key moments and in empty states. The professional applications use them only in empty states: a work screen has nothing decorative.

**People and places.** Beninese people of every age: a vendor, an elderly man with a cane, a young woman in a headscarf, a mother carrying a child on her back, soignants in their work clothes. Skin is drawn in a range of warm browns, colours reserved for illustration and kept out of the UI palette. Wax prints appear sparingly, as flat pattern fills. Places come from daily life: a centre de santé, a CHU, the market, a pharmacy counter, a zem (moto-taxi) bringing a patient, the family phone passed from hand to hand.

**Do:** calm, dignified and hopeful scenes. Show hands doing things, and the objects the patient actually holds: the reçu, the phone, the box of tablets.
**Don't:** poverty imagery; needles, blood or wounds on citizen screens; stock-photo realism; global-health clichés (a world map with pins, a stethoscope on a laptop); the red cross emblem, which is legally protected.

### Icons

Use one open-source family for the interface: **Phosphor Icons** (MIT licence). Use the `bold` weight in the interface and the `duotone` weight next to illustrations, because its two-tone fill matches the flat style. Never mix icon families. An icon always comes with a visible word, except universal controls (close, back, menu), which still carry a text alternative.

### Pictograms

Stock icons cover the actions: search, print, pay, sign out. They cannot tell someone who cannot read "two tablets, morning and evening, after the meal, for five days", or "paid: now go to the pharmacie". A small custom set, drawn in the illustration style, covers only those meanings:

- **Treatment:** matin, midi, soir, nuit; avant / après le repas; number of tablets; number of days
- **Ordonnance states:** à payer, payé, à retirer, retiré en partie, retiré
- **Safety:** allergie, urgence, qui a consulté mon dossier

Care states (cas en cours, cas terminé, analyse en attente, résultat disponible), places and people (caisse, pharmacie, laboratoire, établissement, soignant) should use Phosphor icons and illustration. Draw a custom pictogram only when no stock icon is unambiguous. Test each pictogram for meaning with its label hidden.

### Palette

Measured from the references. Contrast ratios computed against WCAG 2.2.

| Role | Hex | Use | Contrast rule |
|---|---|---|---|
| Bleu royal | `#3648C0` | Primary actions, links, key illustration fills | 7.4:1 on white: valid for all text |
| Bleu denim | `#4E72AE` | Header bands, large surfaces | White text on it at 4.8:1: normal text AA only. Never as text on the pale background (4.2:1, fails) |
| Pervenche | `#C0C6FC` | Selected states, soft surfaces, secondary illustration fills | Ink text only (10:1). Royal text on it fails (4.5:1) |
| Fond pâle | `#EAF0FC` | Page background | Ink text 14:1 |
| Ardoise | `#242A36` | Illustration panels, optional professional dark theme | White text 14:1, pervenche 8.7:1 |
| Encre | `#121212` | Illustration outlines, body text | |
| Blanc | `#FFFFFF` | Cards, surfaces | |

Semantic colours (paid, partial, to collect, allergy, emergency) are yours to propose. Each must reach 4.5:1 against its surface and always come with its pictogram and label, so that red and green are never the only distinction.

### Typography

- **Atkinson Hyperlegible Next** for all text. It was designed for low-vision readers, tells apart characters that are easily confused (I l 1, O 0) and covers every French diacritic.
- **Atkinson Hyperlegible Mono** for identifiers that people read aloud or type: the NPI in digit groups, the numéro d'ordonnance (`ORD-7K4-M2P`), the code carnet, application addresses.
- Body text: 18px minimum on citizen screens and on the site, 16px on professional screens. Site headings are large, short and bold.
- Fonts are served from Lafia itself, never from a third-party font CDN.

### Shape

Generous radii and soft shadows under white cards on the pale background, as in the second reference. Touch targets of 48px minimum.

### Logo: the wordmark and its dot

The logo is the word **Lafia** alone, with no separate symbol. The name is short, easy to say and easy to read, and it does not need one.

- **Letterforms.** Use Atkinson Hyperlegible Next, extra bold (800), with slightly tightened letter-spacing. Using the interface font keeps the brand coherent with every screen; the tuning makes it a mark and not just typed text.
- **The dot on the "i"** is the one detail that belongs only to Lafia. Draw it as a perfect circle, slightly larger than the font's own dot. It stands for the person, and it is the only part of the logo that moves (see *Motion*).
- **Colour.** The word is bleu royal on light surfaces and white on royal or ardoise. The dot may take a single warm accent, for example an ochre or terracotta that recalls Beninese earth. That accent is used only for brand moments: never for a status, and clearly distinct from the semantic colours, especially the "partial" one.
- **Black only.** The logo must still work in plain black on the printed reçu.
- **Compact form** for the favicon and the app icon: the dot alone, or "L" with its dot, on a rounded bleu royal square. It must stay readable at 16px.
- Propose three variants of the wordmark (weight, spacing, size and colour of the dot) side by side, in context: site header, application header, reçu.
- Avoid crosses and the caduceus.

### Signature: le fil

The dot is the person; **le fil** (the thread) is their record following them. It is one continuous line, drawn in the illustration outline weight, and it is Lafia's recurring visual motif. It ties together:

- in the site's hero, the places around the patient
- the steps of the journey section, along which the numéro d'ordonnance travels
- the items of a cas de visite timeline, in the citizen and soin applications
- the steps of sign-in and of encaissement

Wherever something "follows the patient", it runs along le fil. Use it with restraint so it keeps its meaning: never as decoration, never as a border.

### Motion

Motion is a first-class part of the design system, with its own tokens and a specification for each signature moment.

**Tokens**, named by role and delivered with the other tokens:

| Token | Duration | Use |
|---|---|---|
| `--motion-press` | 100 ms | Pressed state, a tick, a toggle |
| `--motion-quick` | 180 ms | Hover, focus, small state changes |
| `--motion-standard` | 280 ms | Panels, screen transitions, a line changing state |
| `--motion-expressive` | 500–800 ms | Signature moments, the site's storytelling |

Propose the easing curves: a standard one, an exit one, and a gentle spring for the signature moments. No bounce on professional screens.

**Tuning by surface:**

- **Professional applications:** `press` and `quick` only, plus screen transitions. No decorative motion, because a queue never waits for an animation.
- **Citizen application:** calm, `standard` motion that explains cause and effect.
- **Product site:** expressive, driven by scroll.

**Signature moments.** Design and prototype each one:

| Surface | Moment | What moves |
|---|---|---|
| Site | Hero | Le fil draws itself from the woman to the centre de santé, the caisse and the pharmacie; the dot of the "i" in the header settles last |
| Site | Un parcours, zéro ressaisie | As the visitor scrolls, `ORD-7K4-M2P` slides along le fil from step to step, and each step's illustration wakes as the number reaches it |
| Site | Services | Cards lift on hover and focus; the actor's illustration makes one small movement |
| All applications | Changing screen | The element tapped grows into the next screen's header (shared-element transition); going back reverses it |
| All applications | Loading | Placeholders shaped like the content, never a lone spinner; content fades in without shifting the layout |
| Citoyen | Sign-in | The reçu illustration lights up where the code carnet is printed; the code field fills digit by digit |
| Citoyen | Mon cas de visite | Le fil draws from the first visite down to today, step by step |
| Citoyen | Mon traitement | A sun travels from matin to nuit; at each moment, the tablets to take appear |
| Soin | Search by NPI | Digits group themselves as they are typed; the patient card slides in the moment the NPI is complete |
| Soin | Mesure curve | The curve draws itself once from left to right; its points then respond to pointer and keyboard |
| Caisse | Encaissement | Ticking a line makes the total count up to its new amount; on cash-in, a « Payé » stamp lands on the ordonnance and the récépissé slides out as if from a printer |
| Pharmacie | Délivrance | Each line handed over slides into the « Remis » column; a line left for later stays in place, marked à retirer |
| Pharmacie | Allergy alert | Enters with one firm movement, never flashes, and stays on screen |

**Rules:**

- Animate only transform and opacity, so motion stays at 60 fps on an entry-level Android phone.
- No layout shift.
- Motion never carries information on its own: the final state says everything by itself.
- Under `prefers-reduced-motion`, every moment becomes a short crossfade and nothing is lost.

**What makes it original:** the dot, le fil, the illustration style and the motion moments above. Avoid the template look: no gradient blobs, no glassmorphism, no generic SaaS hero with a laptop mockup.

## Surfaces

Listed in delivery order. Each actor has its own application (`web/citoyen`, `web/soin`, `web/caisse`, `web/pharmacie`), all built on the shared design system `web/design`. See `docs/adr/0001-une-application-par-acteur.md`.

### 1. Design system (`web/design`)

- **Tokens:** colour, type, spacing, radius, shadow.
- **Components, with all their states:** buttons, inputs, NPI field, code field, status badge, ordonnance line, timeline item, alert, card, table.
- **Components added for the site and the application headers:**
  - site header and footer
  - application header, with the Lafia mark and the actor's name
  - service card
  - demo account block, with a copy button
  - "Bientôt" card for future services

### 2. Product site (`lafia.stephanebah.page`)

One long page. It is mobile-first (360px) and at its best on a laptop (1280 to 1440px), where the jury and institutions will read it. It has more text than the applications but stays illustration-first: each section opens with a picture and makes its point in one sentence before any detail. The tone is plain, confident everyday French, with no jargon. A technical name appears at most as a small badge.

The French copy below is a proposal to refine, not final text.

**1. Header.** Lafia mark; anchors *Vision*, *Comment ça marche*, *Services*, *Demain*; primary button « Ouvrir mon carnet ». Sticky on desktop.

**2. Hero.**

- Title: « Votre dossier de santé vous suit, partout au Bénin. »
- Subtitle: « Avec votre seul NPI, chaque soignant retrouve votre histoire médicale, d'un centre de santé à l'autre, de la caisse à la pharmacie. »
- Buttons: « Ouvrir mon carnet » (to the citizen application), « Je suis un professionnel » (scrolls to *Services*).
- A quiet banner: « Démonstration : toutes les données sont fictives. »
- Illustration: a woman at the centre, holding her reçu and a phone. Around her stand the centre de santé, the caisse and the pharmacie, joined by le fil: her record follows her. Le fil draws itself on arrival (see *Motion*).

**3. Aujourd'hui (the problem).**

- Title: « Aujourd'hui, la mémoire médicale est éparpillée. »
- Three illustrated cards: « Le carnet papier se perd. » · « Chaque établissement tient son propre registre. » · « Le résultat d'analyse n'existe qu'en un exemplaire. »
- Closing line: « Le patient est le seul lien entre ses soignants. »

**4. La vision.**

- Title: « Une personne, un dossier, dans tout le pays. »
- Three points:
  - « Le NPI suffit » : pas de nouveau numéro, pas de carte à créer.
  - « Chaque problème de santé, du début à la fin » : le cas de visite relie les visites, les analyses et les ordonnances, même d'un établissement à l'autre.
  - « Le citoyen voit son carnet » : ce qu'il doit payer, retirer et prendre, et qui a ouvert son dossier.

**5. Comment nous l'avons pensé.** This section shows what makes Lafia different: four pillars, each with an illustration and no architecture diagram.

- « Une mémoire commune, une porte par métier. » Toutes les données médicales vivent en un seul endroit. Soignant, caissière, pharmacien, citoyen : chacun entre par sa propre porte et ne voit que ce dont son métier a besoin. La caissière voit une ordonnance et ses montants, jamais le diagnostic. *Illustration: one central house with four doors, an actor at each.*
- « Interopérable dès le premier jour. » Lafia parle la langue internationale des données de santé. Un laboratoire, une officine ou un service de télémédecine s'y branche sans rien reconstruire et sans copier les données. Lafia n'est lié à aucun fournisseur : il peut être hébergé sur l'infrastructure numérique de l'État. Le dossier appartient au patient, pas à un logiciel. *Small badge: « Standard international HL7 FHIR ». Illustration: new pieces clicking onto the same thread.*
- « La sécurité se voit. » Un soignant n'ouvre un dossier que s'il soigne ce patient. L'urgence vitale reste possible, avec un motif déclaré. Chaque ouverture du dossier est tracée, et le citoyen voit lui-même qui l'a ouvert, et quand. *Illustration: the citizen looking at the list of who opened their dossier.*
- « Compris sans savoir lire. » Le carnet se lit en images : ce qui est payé, ce qui reste à retirer, quand prendre chaque médicament. *Illustration: the posology pictograms.*

**6. Un parcours, zéro ressaisie.** A five-step story told along le fil. On desktop it runs as a horizontal strip, on mobile as a vertical timeline. As the visitor scrolls, the numéro `ORD-7K4-M2P` travels from step to step; that is the visual hook and the site's strongest motion moment.

1. Au centre de santé, le soignant retrouve Awa par son NPI, ouvre un cas, écrit la visite et émet l'ordonnance.
2. Awa reçoit son reçu : le numéro d'ordonnance, son QR code et son code carnet.
3. À la caisse, la caissière saisit le numéro. Les lignes arrivent avec leur tarif ; rien n'est retapé.
4. À la pharmacie, le pharmacien voit les lignes payées et les allergies avant de remettre.
5. Sur le téléphone de son fils, Awa voit ce qu'elle a payé, ce qu'elle a retiré et comment prendre son traitement.

**7. Les services ouverts aujourd'hui.** The door to each application.

- Intro: « Chaque métier a son application, à sa propre adresse. Un compte n'ouvre que la sienne : c'est voulu. »
- Each card shows:
  - an illustration of its actor, the service name and who it is for
  - one line on what it does
  - its address in Mono, readable and easy to type
  - an « Ouvrir » button; the whole card is clickable
- The four cards:

  | Service | For whom | What it does | Address |
  |---|---|---|---|
  | Carnet citoyen | Pour les citoyens | Voir ce qui est payé, ce qui reste à retirer, et comment prendre son traitement. | `citoyen.lafia.stephanebah.page` |
  | Soin | Pour les médecins et infirmiers | Retrouver un patient par son NPI, suivre le cas de visite, écrire la visite, émettre l'ordonnance. | `soin.lafia.stephanebah.page` |
  | Caisse | Pour les caissiers | Ouvrir une ordonnance par son numéro, encaisser sans rien retaper. | `caisse.lafia.stephanebah.page` |
  | Pharmacie | Pour les pharmacies et les officines | Remettre les lignes payées, voir les allergies avant de remettre. | `pharmacie.lafia.stephanebah.page` |

- Under each card, a collapsible « Essayer avec un compte de démonstration »: the identifier and password with copy buttons. Design it with placeholders; the real values come from the dataset.
- Note: « Ces comptes de démonstration sont publics : n'y saisissez aucune donnée réelle. »

**8. Demain.** Near the bottom, with a lighter treatment than the live services: a pervenche surface, a « Bientôt » badge, and no button.

- **Télémédecine**: « Consulter à distance. » Une visite par vidéo ou par téléphone, rangée dans le même cas de visite : le spécialiste de Cotonou suit le patient de Kandi sans qu'il fasse le voyage.
- **Lafia Insights**: « Décider sur des données fiables. » Des tableaux de suivi pour les institutions de décision, le ministère et l'ARS : épidémies, couverture des soins, parcours des patients. Ils sont calculés sur des données anonymisées, jamais sur le dossier des patients.
- **Assistant IA de compte rendu**: « Moins de saisie, plus de soin. » Le soignant dicte ou note librement ; l'assistant prépare le compte rendu de la visite et propose la mise à jour du dossier (mesures, diagnostic, ordonnance). Rien n'est enregistré sans la validation du soignant.
- **Laboratoire**: « Les résultats arrivent seuls. » Le laboratoire dépose ses résultats directement dans le cas de visite, sans papier.
- Closing line: « Chaque nouveau service se branche sur le même dossier, sans rien reconstruire. »

**9. Footer.**

- The Lafia mark.
- « Prototype de démonstration : toutes les données sont fictives. »
- Links to the four applications and to the source code on GitHub (`github.com/StephaneBah/Lafia`).

### 3. Application citoyen (mobile, 360px wide)

- Sign-in: NPI plus code carnet. The reçu is drawn so that the citizen knows where to find the code.
- Carnet home: what is happening now in my care
- My ordonnance: each line with its state pictogram
- My treatment: posology as pictograms
- My cas de visite: the story, step by step
- Who opened my dossier

### 4. Printed reçu

The paper the patient carries away from each visite. It shows:

- the numéro d'ordonnance, large and readable aloud (`ORD-7K4-M2P`), with its QR code
- the posology pictograms for each line
- the code carnet that opens the citizen application

It must stay readable when printed in black only.

### 5. Application soin (desktop and tablet)

- Search by NPI, leading to "ouvrir un cas" or "continuer un cas" (the relation de soin), never straight to the dossier
- Patient summary with allergies first
- Cas de visite timeline across établissements
- New visite form
- Issue an ordonnance
- Mesure curve

### 6. Application caisse

Open an ordonnance by its numéro, tick the lines priced from the tarif (no amount typed), see the total, cash in, print the récépissé.

### 7. Application pharmacie

Paid lines, partial délivrance, allergy alert.

### 8. Accès d'urgence (in the soin application)

The soignant states a reason, then sees the vital information card.

## Constraints

- **Citizen:** entry-level Android, 360 × 640 viewport, outdoor light, shared device.
- **Professionals:** shared desktop or tablet, keyboard use, long sessions.
- **Product site:**
  - usable on a slow 3G connection
  - illustrations as inline SVG; self-hosted fonts
  - no video, no third-party script, no tracker, no cookie
  - rich motion, built light: CSS and SVG animation, scroll-driven where the browser supports it, no animation library, no Lottie
- **Every surface:** a response to each touch within 100 ms, screens that never jump while loading, and transitions that stay smooth on an entry-level Android phone.
- French everyday vocabulary; the UI uses the domain terms of `CONTEXT.md`.
- Amounts `12 500 FCFA`; dates `25/09/2026`; NPI shown in digit groups for reading aloud.
- All data shown is synthetic, with Beninese names and places.

## Accessibility acceptance

These rules apply to every surface, the product site included.

- WCAG 2.2 AA on every screen; text contrast 4.5:1 minimum, 7:1 targeted on citizen screens.
- Text enlarged to 200% loses no content or function.
- Every state conveyed by pictogram or icon and label, never by colour alone; nothing conveyed by sound.
- Every interactive element reachable by keyboard, with a visible focus.
- Every pictogram and every illustration that carries meaning has a text alternative; decorative ones are hidden from screen readers.
- Targets 48px minimum on citizen screens and on the site.
- Under `prefers-reduced-motion`, motion becomes a crossfade; nothing flashes more than three times per second; no animation delays input.

## Out of Scope

- Voice, offline states, USSD and SMS channels, citizen dark mode.
- The future services (télémédecine, Lafia Insights, assistant IA, laboratoire) are presented on the site, not designed as screens.

## Deliverables

- Logo: the Lafia wordmark in three variants shown in context, the chosen one in colour and in black only, and its compact form for the favicon and app icon
- Tokens as CSS custom properties and as JSON, named by role (`--color-action`, not `--blue-1`), motion tokens included
- Motion specification: each signature moment with its trigger, duration, easing and reduced-motion version, and each one prototyped as an interactive HTML file
- Component sheet with every state
- Illustration set as individual SVG files:
  - site: hero, the three problems, the four pillars, the five journey steps, the four actors, the four future services
  - citizen application: key moments and empty states
- Pictograms as individual SVG files, outline weight and grid specified
- Product site mockups at 360px and 1440px, and the page as a working HTML file
- The application screens listed above
- A one-page charte graphique covering:
  - the palette and its contrast rules
  - the type scale
  - icon rules: Phosphor weights, and when to draw a custom pictogram
  - illustration dos and don'ts
  - the logo, the dot and le fil: how to use them and how not to
  - the motion tokens and rules

The tokens, pictograms and components live in the `web/design` workspace package, which every application consumes. The charte graphique and the component sheet go to `docs/design/`, where they become the source of the design skill that coding agents use.
