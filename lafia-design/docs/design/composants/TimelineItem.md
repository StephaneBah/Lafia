# TimelineItem

Une étape d'un cas de visite, enfilée sur le fil : la ligne continue qui figure le dossier qui suit le patient.

**À fournir :** `title`, `date` (`25/09/2026`), `place` (établissement), `icon` (Phosphor), `children` (détail), `state` (`done`, `current`, `upcoming` en pointillés), `first`/`last` pour couper le fil aux extrémités, `animate` + `index` pour que le fil se dessine de la première visite jusqu'à aujourd'hui, étape après étape. Envelopper les éléments dans `<ol class="lf-timeline">`.

- Le fil est `color-fil` à `stroke-illustration` : jamais une décoration ni une bordure ailleurs.
- Soin utilise le même élément, plus dense, à travers les établissements.
