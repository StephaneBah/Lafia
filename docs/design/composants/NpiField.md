# NpiField

Le champ NPI : les 13 chiffres se groupent en 4-3-3-3 pendant la frappe (`0000 001 317 462`), en Mono, avec un compteur et une coche quand les 13 chiffres sont là. Les NPI du jeu de démonstration commencent par six zéros : aucun NPI réel ne commence ainsi.

**À fournir :** `name` dans un formulaire : le formulaire reçoit sous ce nom les 13 chiffres seuls, jamais groupés, comme identite et les services les attendent (avant le chargement du JavaScript, le champ visible porte lui-même le nom) ; `value`/`onChange` (reçoit les chiffres seuls) ou `defaultValue`, `onComplete(npi)` appelé une fois au 13e chiffre (l'application soin fait alors glisser la carte patient), `label` (« NPI » par défaut), `hint`, `error`, `size`, `autoFocus` sur l'écran de recherche, `required`.

- Donner le focus à l'arrivée dans soin : l'infirmier tape tout de suite.
- Pas d'étape « Rechercher » quand le NPI est complet : agir sur `onComplete`.
