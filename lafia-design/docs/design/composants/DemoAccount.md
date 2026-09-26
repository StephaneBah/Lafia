# DemoAccount

Bloc repliable « Essayer avec un compte de démonstration » : identifiant et mot de passe, chacun avec son bouton copier.

**À fournir :** `identifier`, `password` (ou `false` s'il n'y en a pas), `identifierLabel` / `passwordLabel` pour d'autres libellés (« NPI », « Code carnet »), `note` pour une consigne, `open`, `summary`.

- Les valeurs viennent du jeu de démonstration du dépôt (`donnees/agents.toml`, `officines.toml`, `patients.toml`) : mot de passe public `lafia-demo`.
- Le citoyen n'a pas de mot de passe : son code carnet est émis par l'application soin à la fin d'une visite et imprimé sur le reçu. Le bloc citoyen donne donc un NPI et une `note` qui explique comment obtenir le code.

- Toujours accompagner un groupe de ces blocs de la note : « Ces comptes de démonstration sont publics : n'y saisissez aucune donnée réelle. »
