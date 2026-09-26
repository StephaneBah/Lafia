# Lafia — export design

Copiez ce dossier à la racine du dépôt `Lafia` : les chemins correspondent à sa structure.

- `web/design/tokens/` : `tokens.json` (source, format du design system), `tokens.css` (variables CSS prêtes à importer), `tokens.flat.json` (valeurs à plat par rôle).
- `web/design/fonts/` : Atkinson Hyperlegible Next et Mono en woff2, servies par Lafia.
- `web/design/assets/` : Logo, Pictogrammes, Icones (Phosphor, MIT), Illustrations (SVG, chacun avec son README).
- `web/design/components/` : `bundle.js` (composants React, `window.Lafia`), `bundle.css`, `index.d.ts`. Référence visuelle et de comportement : à porter en composants TypeScript dans `web/design/src`.
- `docs/design/charte-graphique.md`, `mouvement.md`, `composants/*.md` : la source du skill de design pour les agents.
- `docs/design/maquettes/` : le site produit et les écrans, en HTML autonome (les écrans chargent React 18 depuis cdnjs).
