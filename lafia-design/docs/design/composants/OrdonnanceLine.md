# OrdonnanceLine

Une ligne d'ordonnance, en trois modes : `citoyen` (lecture, avec pictogrammes de posologie), `caisse` (cocher pour ajouter au total, prix issu du tarif) et `pharmacie` (cocher pour remettre, allergie affichée avant).

**À fournir :** `name`, `detail`, `mode`, `price` (entier FCFA, affiché `12 500 FCFA`), `status`, `posology` `{count, moments:['matin','midi','soir','nuit'], meal:'avant'|'apres', days}` (citoyen), `allergy` (texte : la ligne prend un contour et un badge rouges), `checked` + `onToggle(next)`, `disabled` pour une ligne non cochable.

- Toute la ligne est la cible ; Espace la coche au clavier.
- Caisse : rien n'est saisi. Pharmacie : une ligne avec `allergy` ne se coche jamais sans avoir d'abord montré `Alert tone="allergie"`.
- Au changement, le fond évolue en `motion-standard` ; une ligne remise glisse vers « Remis », une ligne laissée pour plus tard reste en place, marquée `aretirer`.
