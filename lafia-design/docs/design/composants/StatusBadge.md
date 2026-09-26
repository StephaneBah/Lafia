# StatusBadge

Un statut = pictogramme (ou icône) + mot + couleur, toujours les trois ensemble.

**À fournir :** `status` : états d'ordonnance `apayer`, `paye`, `aretirer`, `partiel`, `retire` ; sécurité `allergie`, `urgence` ; états de soin `encours`, `termine`, `attente`, `resultat` (icônes Phosphor). `size` : `citizen` (défaut), `large`, `pro`. `label` facultatif pour remplacer le mot.

- Couleurs : `status-*-fg` sur `status-*-bg`, toutes ≥ 6,7:1. `paye` est sarcelle, hors de l'axe rouge-vert : il ne dépend jamais de la teinte face à `allergie`.
- Ne pas inventer de couleur de statut : ajouter d'abord l'état ici.
