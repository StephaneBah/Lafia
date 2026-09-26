# CodeField

Le champ code carnet : une case par caractère, en deux groupes séparés d'un tiret comme sur le reçu (`H3T-9QR`), portée par un seul vrai champ (le collage et le remplissage automatique fonctionnent). La saisie passe en majuscules, tiret et espaces ôtés ; identite la normalise de même.

**À fournir :** `name` dans un formulaire (`code` pour `POST /api/identite/citoyen/connexion`), `length` (6 par défaut), `value`/`onChange` ou `defaultValue`, `numeric` pour un code tout chiffres, `label` (« Code carnet » par défaut), `hint` (indique où le code est imprimé sur le reçu), `error`, `required`.

- À la connexion, l'associer à l'illustration du reçu qui s'éclaire là où le code est imprimé.
