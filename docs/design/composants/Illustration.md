# Illustration

Une scène de la charte (`web/design/assets/Illustrations`), insérée en SVG dans la page : aucune requête de plus, et le fil (`.lf-fil`) peut s'animer en CSS. Importée depuis `@lafia/design/illustration`, jamais depuis `@lafia/design` : réservée aux composants serveur, les scènes ne partent pas dans le JavaScript envoyé au navigateur.

**À fournir :** `name` (le nom du fichier sans `.svg`, typé : `site-heros`, `vide-ordonnance`, `acteur-caissiere`…), `decorative` quand le texte voisin dit déjà la même chose, sinon `label` pour remplacer le titre du fichier, qui sert d'alternative textuelle.

- Citoyen : seulement aux moments clés et dans les états vides, avec une phrase courte et, si utile, une seule action. Pro : seulement dans les états vides.
- Après tout changement dans `assets/` : `npm run generer --workspace @lafia/design` régénère `src/generes/`.
