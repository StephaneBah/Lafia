# Alert

Un message qui reste à l'écran : jamais un toast, jamais un son, jamais de clignotement.

**À fournir :** `tone` (`info`, `succes`, `attention`, `danger`, et les deux forts `allergie` et `urgence` en aplat `status-danger-solid`), `title` (le fait, court), `children` (quoi faire), `actions`, `onClose` (absent des tons forts : ils restent jusqu'à résolution).

- L'alerte allergie à la délivrance entre d'un seul mouvement ferme (`motion-standard`), puis ne bouge plus.
- Chaque état porte un pictogramme ou une icône et un mot : entièrement visible pour une personne sourde.
