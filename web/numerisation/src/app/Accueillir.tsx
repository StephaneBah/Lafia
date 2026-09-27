"use client";

// Étape 1 : la personne est au bureau, ses papiers en main. Son NPI, la pièce que l'agent a vérifiée,
// et si le dépôt compte pour la Reprise. Le NPI part dans le corps de la requête, jamais dans l'adresse.
import { Alert, Button, Icon, NpiField } from "@lafia/design";
import { startTransition, useActionState, type FormEvent } from "react";

import { PIECES } from "../libelles";
import { ouvrirLeDepot, type Refus } from "./actions";

const MESSAGES: Record<NonNullable<Refus>["erreur"], { titre: string; texte: string; ton: "attention" | "danger" }> = {
  npi: { titre: "Le NPI compte treize chiffres.", texte: "Relisez-le sur la pièce, chiffre par chiffre.", ton: "attention" },
  piece: {
    titre: "Cochez la pièce d'identité présentée.",
    texte: "Le dépôt s'ouvre une fois la pièce vue et comparée au visage de la personne.",
    ton: "attention",
  },
  inconnu: {
    titre: "Aucune personne sous ce NPI.",
    texte: "Relisez le NPI avec la personne, chiffre par chiffre. Rien n'a été ouvert.",
    ton: "attention",
  },
  service: {
    titre: "Le service numérisation ne répond pas.",
    texte: "Aucun dépôt n'a été ouvert. Réessayez dans un instant : ce que vous avez saisi reste là.",
    ton: "danger",
  },
};

export function Accueillir() {
  const [refus, envoyer, enCours] = useActionState(ouvrirLeDepot, null);
  const message = refus ? MESSAGES[refus.erreur] : undefined;

  // Envoyé à la main : le formulaire n'est pas vidé quand le service refuse, l'agent corrige et renvoie.
  function soumettre(evenement: FormEvent<HTMLFormElement>) {
    evenement.preventDefault();
    const donnees = new FormData(evenement.currentTarget);
    startTransition(() => envoyer(donnees));
  }

  return (
    <form className="num-carte num-formulaire" onSubmit={soumettre}>
      <NpiField name="npi" label="NPI de la personne" size="pro" autoFocus required className="num-champ-npi" />

      <fieldset className="num-choix">
        <legend className="num-legende">
          <Icon name="identification-card" size={24} />
          <span>Pièce d'identité vérifiée</span>
        </legend>
        <p className="num-aide">Comparez la photo au visage de la personne avant d'ouvrir le dépôt.</p>
        <div className="num-radios">
          {PIECES.map((piece) => (
            <label key={piece.code} className="num-radio">
              <input type="radio" name="piece" value={piece.code} required />
              <span>{piece.libelle}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <label className="num-case">
        <input type="checkbox" name="reprise" value="oui" defaultChecked />
        <span>Dans le cadre de la Reprise</span>
      </label>

      {message && (
        <Alert tone={message.ton} title={message.titre}>
          {message.texte}
        </Alert>
      )}

      <div className="num-actions">
        <Button type="submit" size="pro" icon="plus" loading={enCours}>
          Ouvrir le dépôt
        </Button>
      </div>
    </form>
  );
}
