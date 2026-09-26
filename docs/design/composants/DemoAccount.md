# DemoAccount

Bloc repliable « Essayer avec un compte de démonstration » : un ou plusieurs comptes, chaque valeur avec son bouton copier (sans presse-papiers, la valeur reste sélectionnée).

**À fournir :** `comptes`, une liste de comptes, chacun une liste `[{label, value}]` (« Identifiant » et « Mot de passe » ; « NPI » et « Code carnet » pour le citoyen), `note` pour une consigne, `open`, `summary`.

- Les valeurs viennent du jeu de démonstration du dépôt (`donnees/agents.toml`, `officines.toml`, `citoyens.toml`) : mot de passe public `lafia-demo`. Les pages de connexion les reçoivent d'identite (`GET /api/identite/comptes-de-demonstration`).
- Le citoyen n'a pas de mot de passe : il se connecte par son NPI et le code carnet de son dernier reçu. Le jeu de démonstration donne un code à quelques NPI (`citoyens.toml`) ; chaque nouvelle visite en émet un nouveau, qui remplace le précédent.

- Toujours accompagner un groupe de ces blocs de la note : « Ces comptes de démonstration sont publics : n'y saisissez aucune donnée réelle. »
