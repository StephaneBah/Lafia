# Mouvement : moments signature

Chaque moment : déclencheur, ce qui bouge, durée et courbe, version réduite. Tous n'animent que `transform` et `opacity`, et l'état final dit tout seul ce qui s'est passé.

## Toutes les applications

| Moment | Déclencheur | Ce qui bouge | Durée · courbe | Mouvement réduit |
|---|---|---|---|---|
| Changer d'écran | Appui sur un élément qui ouvre un écran | L'élément touché grandit jusqu'à devenir l'en-tête de l'écran suivant (transition d'élément partagé, View Transitions API) ; retour : l'inverse | `motion-standard` · `ease-standard` (sortie `ease-exit`) | Fondu 120 ms |
| Chargement | Donnée attendue | Placeholders à la forme du contenu (`lf-skel`), puis fondu du contenu sans décalage | apparition `motion-quick` | Placeholders fixes, fondu |

## Site

| Moment | Déclencheur | Ce qui bouge | Durée · courbe | Mouvement réduit |
|---|---|---|---|---|
| Héros | Arrivée sur la page | Le fil se dessine (`stroke-dashoffset`) de la femme au centre de santé, à la caisse puis à la pharmacie ; le point du « i » de l'en-tête se pose en dernier (`Logo animate`) | 3 × `motion-expressive` enchaînés · `ease-standard` ; point `ease-spring` | Scène finale en fondu |
| Un parcours, zéro ressaisie | Défilement (`animation-timeline: view()`, repli IntersectionObserver) | `ORD-7K4-M2P` glisse le long du fil d'étape en étape ; l'illustration de chaque étape s'éveille (échelle 0,96 → 1, opacité) quand le numéro l'atteint | lié au défilement ; éveil `motion-expressive` · `ease-spring` | Numéro affiché à chaque étape, sans trajet |
| Services | Survol ou focus d'une carte | Carte −4px + `shadow-lift` ; l'illustration de l'acteur fait un seul petit mouvement (rotation −6°) | `motion-quick` · `ease-standard` ; illustration `motion-standard` · `ease-spring` | Ombre seule |

## Citoyen

| Moment | Déclencheur | Ce qui bouge | Durée · courbe | Mouvement réduit |
|---|---|---|---|---|
| Connexion | Focus sur le code carnet | L'illustration du reçu s'éclaire là où le code est imprimé ; le champ se remplit chiffre par chiffre (`CodeField`) | `motion-standard` · `ease-standard` | Zone surlignée fixe |
| Mon cas de visite | Ouverture de l'écran | Le fil se dessine de la première visite jusqu'à aujourd'hui, étape par étape (`TimelineItem animate index`) | `motion-standard` par étape, décalage 220 ms | Fondu de la liste |
| Mon traitement | Ouverture de l'écran | Un soleil voyage de matin à nuit ; à chaque moment apparaissent les comprimés à prendre | 4 × `motion-standard` · `ease-standard` | Les quatre moments affichés d'emblée |

## Soin

| Moment | Déclencheur | Ce qui bouge | Durée · courbe | Mouvement réduit |
|---|---|---|---|---|
| Recherche par NPI | Frappe | Les chiffres se groupent 4-3-3-3 ; au 13e chiffre (`onComplete`), la carte patient glisse (translateY 8px → 0) | `motion-quick` · `ease-standard` | Apparition directe |
| Courbe de mesure | Première apparition | La courbe se dessine une fois de gauche à droite ; ses points répondent ensuite au pointeur et au clavier | `motion-expressive` (exception pro : une seule fois, jamais bloquante) · `ease-standard` | Courbe complète d'emblée |
| Accès d'urgence | Motif déclaré | Bandeau `Alert tone="urgence"` entre d'un mouvement ferme | `motion-standard` · `ease-standard` | Fondu |

## Caisse

| Moment | Déclencheur | Ce qui bouge | Durée · courbe | Mouvement réduit |
|---|---|---|---|---|
| Encaissement | Coche d'une ligne | Le total compte jusqu'au nouveau montant (chiffres tabulaires : aucune largeur ne bouge) | `motion-standard` · `ease-standard` | Montant final direct |
| Encaissé | Validation | Un tampon « Payé » se pose sur l'ordonnance (échelle 1,2 → 1) ; le récépissé glisse comme d'une imprimante | `motion-standard` · `ease-standard`, sans rebond | Tampon et récépissé en fondu |

## Pharmacie

| Moment | Déclencheur | Ce qui bouge | Durée · courbe | Mouvement réduit |
|---|---|---|---|---|
| Délivrance | Ligne remise | La ligne glisse vers la colonne « Remis » ; une ligne laissée pour plus tard reste en place, marquée `aretirer` | `motion-standard` · `ease-standard` | Changement de colonne direct |
| Alerte allergie | Ligne à risque sélectionnée | `Alert tone="allergie"` entre d'un seul mouvement ferme, ne clignote jamais, reste à l'écran | `motion-standard` · `ease-standard` | Fondu |
