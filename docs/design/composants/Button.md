# Button

Le bouton unique : un verbe en français courant, avec une icône Phosphor facultative devant.

**À fournir :** `children` (le libellé), `variant` (`primary` un seul par écran, `secondary`, `ghost` pour une action discrète, `danger` pour l'urgence vitale uniquement), `size` (`citizen` : cible 48px, texte 18px ; `pro` : 40px, 16px), `icon`/`iconRight`, `href` pour un lien, `loading`, `disabled`, `block` pleine largeur côté citoyen.

- Répondre à chaque appui en moins de 100 ms : l'état pressé (`motion-press`) est la réponse.
- Un seul bouton primaire par écran citoyen : un écran, une décision.
- Ne pas désactiver un bouton pour expliquer une règle : dire à côté ce qui manque.
- `loading` garde le libellé et la largeur : rien ne bouge.
