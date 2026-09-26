# TextInput

Un champ texte avec libellé, aide facultative et erreur en mots simples.

**À fournir :** `label` (toujours visible, jamais un simple placeholder), `hint`, `error` (dit quoi faire, pas seulement ce qui ne va pas), `size` (`citizen` 48px / 18px, `pro` 40px / 16px), `icon`, et tout attribut natif (`value`, `onChange`, `inputMode`…).

- L'erreur montre une icône, un texte gras et une bordure rouge : jamais la couleur seule.
- Ne jamais redemander une donnée déjà connue.
