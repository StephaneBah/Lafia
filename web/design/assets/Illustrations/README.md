# Illustrations

Jeu de départ du site produit et de l'application citoyen, dans le style de la charte : aplats, contours `encre` de 3px (`stroke-illustration`), coins arrondis, carnations `illu-peau-*`, wax en motif plat. Aucun dégradé, aucune photo, aucune croix.

| Fichier | Section du site | Format |
|---|---|---|
| `site-heros.svg` | Héros — Awa, son reçu et son téléphone ; le fil relie centre de santé, caisse, pharmacie | 960×440 |
| `probleme-carnet.svg`, `probleme-registres.svg`, `probleme-exemplaire.svg`, `probleme-interpretations.svg` | Aujourd'hui (4 cartes) | 480×360 |
| `pilier-memoire.svg`, `pilier-interoperable.svg`, `pilier-securite.svg`, `pilier-sans-lire.svg` | Comment nous l'avons pensé (4 piliers) | 480×360 |
| `parcours-1-centre.svg` … `parcours-5-telephone.svg` | Un parcours, zéro ressaisie (5 étapes) | 480×360 |
| `acteur-citoyen.svg`, `acteur-soignant.svg`, `acteur-caissiere.svg`, `acteur-pharmacien.svg` | Cartes de service (`ServiceCard illustration`) | 240×240, disque pervenche |
| `demain-telemedecine.svg`, `demain-insights.svg`, `demain-assistant.svg`, `demain-laboratoire.svg` | Demain (`SoonCard`) | 480×360 |
| `citoyen-connexion.svg` | Application citoyen · connexion : le code carnet du reçu ouvre le carnet | 320×240 |
| `citoyen-bienvenue.svg` | Application citoyen · première ouverture du carnet | 320×240 |
| `citoyen-paye-pharmacie.svg` | Application citoyen · ordonnance payée, aller à la pharmacie | 320×240 |
| `citoyen-traitement-fini.svg` | Application citoyen · traitement terminé | 320×240 |
| `citoyen-cas-termine.svg` | Application citoyen · cas de visite terminé (le fil se referme sur une coche) | 320×240 |
| `citoyen-urgence-tracee.svg` | Application citoyen · explication d'un accès d'urgence tracé | 320×240 |
| `vide-ordonnance.svg` | État vide · aucune ordonnance en cours | 320×240 |
| `vide-traitement.svg` | État vide · rien à prendre aujourd'hui | 320×240 |
| `vide-cas.svg` | État vide · aucun cas en cours | 320×240 |
| `vide-consultations.svg` | État vide · personne d'autre n'a ouvert le dossier | 320×240 |
| `vide-session.svg` | État vide · session fermée (téléphone partagé) | 320×240 |

- Chaque fichier porte son alternative textuelle en `<title>` ; sur le site, l'insérer en SVG inline et reprendre ce texte en `aria-label`, ou `aria-hidden="true"` si le texte voisin dit déjà la même chose.
- Le fil est un `<path class="lf-fil" pathLength="1">` (héros, interopérable, télémédecine, laboratoire) : l'animer par `stroke-dasharray: 1; stroke-dashoffset: 1 → 0`, en `motion-expressive`.
- Awa (foulard `bleu-royal`, haut `illu-soleil`, pagne wax royal) est le personnage fil rouge : garder sa tenue identique d'une scène à l'autre.
- Les soignants portent une tenue sarcelle claire et un stéthoscope ; jamais de coiffe à croix.
- Côté citoyen, une illustration n'apparaît qu'aux moments clés et dans les états vides, toujours avec une phrase courte et, si utile, une seule action. Côté pro, seulement dans les états vides.
