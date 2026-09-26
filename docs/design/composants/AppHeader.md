# AppHeader

L'en-tête de chaque application : la marque Lafia blanche (lien vers le site), le nom de l'acteur avec son icône, puis le lieu, l'utilisateur et la déconnexion.

**À fournir :** `actor` (`citoyen`, `soin`, `caisse`, `pharmacie`), `siteHref` (`adresse(domaine)`), `place` (établissement), `user`, `signOut` : `true` pose un formulaire qui envoie `POST /api/identite/deconnexion`, par la passerelle de l'application (identite efface les cookies et renvoie à `/connexion`) ; une chaîne donne une autre adresse d'envoi.

- La puce d'acteur dit à qui est cette porte : un compte caisse n'ouvre jamais un dossier médical.
