Lafia donne à chaque citoyen béninois un dossier de santé unique, retrouvé par son seul NPI. **L'illustration porte le sens, les mots le confirment.** Ce système sert trois surfaces : le site produit (`lafia.stephanebah.page`), l'application citoyen, et les applications professionnelles soin, caisse et pharmacie. Chaque surface dit à quel acteur elle sert.

## Principes

1. **Comprendre sans lire.** Test : après cinq secondes à l'écran, une personne qui ne lit pas dit correctement ce qu'on lui demande.
2. **Un écran, une décision.** Côté citoyen, une seule action `primary` par écran.
3. **Icône, mot, couleur : toujours ensemble.** La couleur ne porte jamais le sens seule (`StatusBadge`).
4. **Rapide pour les pros.** Tout au clavier, dense là où la densité fait gagner du temps, aucune donnée redemandée.
5. **Local par défaut.** Visages, noms et lieux béninois ; montants en FCFA ; français courant.
6. **La confiance se voit.** Qui a ouvert le dossier, pourquoi un accès d'urgence, ce que voit chaque rôle.
7. **Une porte par acteur.** Le site mène chacun à sa porte en un clic ; chaque en-tête d'application nomme l'acteur.
8. **Fluide, et d'abord rapide.** Réponse à chaque appui en moins de 100 ms ; on peut toujours agir avant la fin d'une animation.

## Écriture

- Français courant, phrases courtes, vouvoiement côté citoyen (« Allez à la pharmacie »), infinitif sur les boutons (« Encaisser », « Ouvrir mon carnet »).
- Termes du domaine exactement : NPI, code carnet, cas de visite, visite, ordonnance, numéro d'ordonnance, caisse, pharmacie, délivrance, mesure, établissement, soignant.
- Formats : `12 500 FCFA` (espace fine insécable, `formatFcfa`), `25/09/2026`, NPI de 13 chiffres en groupes `0000 001 317 462` (`formatNpi`), ordonnance `ORD-7K4-M2P`.
- Majuscule en début de libellé seulement. Pas d'emoji. Un nom technique n'apparaît que comme petit badge (« Standard international HL7 FHIR »).
- Toutes les données montrées sont fictives, avec des noms et lieux béninois (Awa Houngbédji, Dantokpa, CHU-MEL Cotonou, Parakou, Kandi). Les maquettes reprennent les agents et établissements du jeu de démonstration (`donnees/`) ; les NPI de démonstration commencent par six zéros.

## Couleur

Palette mesurée sur les références, contrastes WCAG 2.2 :

| Rôle | Token | Usage et règle |
|---|---|---|
| Bleu royal #3648C0 | `bleu-royal` → `color-action`, `color-link` | Actions, liens, aplats clés. 7,4:1 sur blanc : tout texte. |
| Bleu denim #4E72AE | `bleu-denim` → `color-band` | Bandeaux, grandes surfaces. Texte blanc 4,8:1 (AA normal seulement). **Jamais** en texte sur `fond-pale` (4,2:1). |
| Pervenche #C0C6FC | `pervenche` → `color-surface-soft` | Sélection, cartes « Bientôt ». Texte `encre` seulement (11:1) ; royal dessus échoue. |
| Fond pâle #EAF0FC | `fond-pale` → `color-bg` | Fond de page. Encre 14:1. |
| Ardoise #242A36 | `ardoise` | Panneaux d'illustration, pied de page, thème pro sombre. |
| Encre #121212 | `encre` → `color-text` | Texte, contours d'illustration. |
| Terre #C2562B | `terre` | **Uniquement** le point du « i » et les moments de marque. Jamais un statut, jamais du texte. |

Statuts (fg sur bg, tous ≥ 6,7:1, citoyen visé 7:1) : `status-apayer-*` ambre, `status-paye-*` sarcelle (hors axe rouge-vert), `status-aretirer-*` bleu, `status-partiel-*` prune (distinct de `terre`), `status-retire-*` neutre, `status-danger-*` rouge ; `status-danger-solid` + `color-on-danger` pour l'allergie à la délivrance et l'urgence vitale.

- Mettre le texte courant en `color-text` sur `color-bg`, `color-surface` ou `color-surface-soft` ; le secondaire en `color-text-muted` (≥ 6,9:1).
- Contours de champs : `color-border-control` (≥ 3:1) ; séparateurs décoratifs : `color-border`.
- Focus : anneau plein `color-focus` de 3px décalé de 2px sur la surface, visible sur blanc, fond pâle et pervenche.
- Thème `ardoise` : optionnel, **professionnels seulement**. Le citoyen n'a pas de mode sombre.
- Illustration seulement, hors interface : `illu-soleil`, `illu-peau-1` à `illu-peau-3`.

## Typographie

- **Atkinson Hyperlegible Next** (`--font-sans`) pour tout texte : conçue pour la basse vision, distingue I l 1 et O 0, couvre tous les diacritiques français.
- **Atkinson Hyperlegible Mono** (`--font-mono`) pour ce qu'on lit à voix haute ou qu'on tape : NPI, numéro d'ordonnance, code carnet, adresses d'application.
- Fichiers woff2 servis par Lafia (`fonts/`), jamais par un CDN tiers.
- Site : `display-xl` (héros), `display` (sections), `lead`. Titres courts et gras.
- Citoyen : `title`, `heading`, `body-lg`, `body` — **18px minimum**, `label` pour boutons et badges.
- Professionnel : `pro-title`, `pro-body` — **16px minimum**, `pro-label`, `pro-small` (métadonnées pro seulement).
- Identifiants : `id-xl` (reçu, caisse), `id` (NPI, code carnet), `id-sm` (adresses).
- Agrandi à 200 %, aucun contenu ni fonction ne se perd : pas de hauteur fixe sur un bloc de texte.

## Espace, forme, profondeur

- Espacement 4px de base : `space-1` à `space-9`. Gouttière mobile `space-4` (360px), padding de carte `space-5`, sections du site `space-8` mobile / `space-9` desktop, contenu max `content-max`.
- Rayons généreux : `radius-sm` (pro, badges), `radius-md` (boutons, champs), `radius-lg` (cartes), `radius-xl` (grandes cartes du site), `radius-pill`.
- Cartes blanches sur fond pâle avec `shadow-card` ; `shadow-lift` au survol ; pas de verre dépoli, pas de dégradé décoratif.
- Cibles : `target-min` 48px côté citoyen et site ; `target-pro` 40px côté pro.

## Iconographie

- **Phosphor Icons** (MIT), une seule famille : `bold` dans l'interface, `duotone` à côté des illustrations. Composant `Icon`.
- Une icône a toujours un mot visible, sauf fermer, retour, menu, qui portent un `label`.
- **Pictogrammes Lafia** (`Picto`, `assets/Pictogrammes`) seulement pour ce qu'aucune icône ne dit sans ambiguïté : posologie (matin, midi, soir, nuit, avant/après le repas, comprimés, jours), états d'ordonnance, allergie, urgence, qui a consulté mon dossier. Grille 48, contour `encre` 3px. Tester chaque nouveau pictogramme libellé masqué.
- États de soin, lieux et personnes : Phosphor et illustration.
- Jamais : croix rouge (emblème protégé), caducée, `first-aid-kit`, emoji.

## Illustration

- Style plat, géométrique, amical : aplats, contours quasi noirs d'épaisseur constante (`stroke-illustration`), coins arrondis, cartes qui se chevauchent. Objets simples : une carte, une gélule, une horloge dans un disque blanc.
- Où : scènes complètes sur le site ; illustrations ponctuelles aux moments clés et états vides côté citoyen ; états vides seulement côté pro.
- Qui : des Béninois de tout âge — vendeuse, homme âgé à canne, jeune femme voilée, mère portant son enfant au dos, soignants en tenue. Carnations en `illu-peau-*`. Wax en aplat, avec parcimonie. Lieux : centre de santé, CHU, marché, comptoir de pharmacie, zem, téléphone familial passé de main en main.
- À faire : scènes calmes, dignes, confiantes ; des mains qui agissent ; les objets que le patient tient (le reçu, le téléphone, la boîte de comprimés).
- Jeu de départ : groupe `Illustrations` (héros, problèmes, piliers, parcours, acteurs, services à venir). Awa garde la même tenue dans toutes les scènes.
- À éviter : imagerie de pauvreté ; aiguilles, sang, plaies côté citoyen ; réalisme photo ; clichés de santé mondiale (carte à épingles, stéthoscope sur laptop) ; dégradés, 3D, photos.

## Logo, point et fil

- Le logo est le mot **Lafia** seul (`Logo`, `assets/Logo`) : Atkinson Hyperlegible Next 800, approche resserrée, point du « i » redessiné en cercle parfait, plus grand, en `terre`.
- `royal` sur clair, `blanc` sur royal, denim ou ardoise, `noir` sur le reçu. Forme compacte : `lafia-icone.svg`.
- **Le point, c'est la personne.** C'est la seule partie du logo qui bouge : il se pose en dernier.
- **Le fil, c'est son dossier qui la suit.** Une ligne continue `color-fil` à `stroke-illustration` qui relie : les lieux du héros, les étapes de « Un parcours, zéro ressaisie », les éléments d'un cas de visite (`TimelineItem`), les étapes de connexion et d'encaissement.
- Avec retenue : jamais décoratif, jamais une bordure. Si rien ne « suit le patient », pas de fil.

## Mouvement

Durées (`duration`) : `motion-press` 100 ms (appui, coche), `motion-quick` 180 ms (survol, focus), `motion-standard` 280 ms (panneaux, transitions d'écran), `motion-expressive` 500–800 ms (640 ms par défaut, moments signature). Courbes (`easing`) : `ease-standard` pour entrer, `ease-exit` pour sortir, `ease-spring` ressort doux (citoyen et site seulement).

- Pro : `press` et `quick`, plus les transitions d'écran. Aucun ressort, aucun décor : une file d'attente n'attend pas une animation.
- Citoyen : `standard`, calme, qui explique la cause et l'effet.
- Site : `expressive`, piloté par le défilement.
- N'animer que `transform` et `opacity` ; aucun décalage de mise en page ; le mouvement ne porte jamais seul l'information.
- Sous `prefers-reduced-motion`, chaque moment devient un court fondu ; rien ne clignote plus de trois fois par seconde. Les variables CSS `--motion-*` sont déjà réduites dans `bundle.css`.

Spécification de chaque moment signature : section *Mouvement : moments signature*.

## Accessibilité (critères d'acceptation)

- WCAG 2.2 AA partout ; texte ≥ 4,5:1, 7:1 visé côté citoyen.
- Tout état par pictogramme ou icône **et** mot ; rien par le son.
- Tout élément interactif au clavier avec focus visible ; chargement par placeholders à la forme du contenu (`Card loading`, `Table loading`).
- Pictogrammes et illustrations porteurs de sens avec alternative textuelle ; décoratifs masqués.
