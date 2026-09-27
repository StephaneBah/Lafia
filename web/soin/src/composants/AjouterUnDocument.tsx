"use client";

import { Alert, Button, Icon, TextInput } from "@lafia/design";
import { useActionState, useState, useTransition, type FormEvent } from "react";

import { ajouterDocument, type EtatDuDocument } from "../app/actions";
import { TYPES_DE_DOCUMENT } from "../lib/types";

// Ajouter un document apporté par le patient, pendant la visite : les mêmes champs qu'au guichet de
// numérisation. Les photos sont compressées ici, dans le navigateur (ADR 0008) : JPEG, 1600 px au
// plus sur le grand côté, 1 Mo au plus. Un PDF part tel quel.

const COTE_MAX = 1600;
const OCTETS_MAX = 1024 * 1024;

async function compresser(fichier: File): Promise<File> {
  if (!fichier.type.startsWith("image/")) return fichier;
  const image = await createImageBitmap(fichier);
  const echelle = Math.min(1, COTE_MAX / Math.max(image.width, image.height));
  const toile = document.createElement("canvas");
  toile.width = Math.round(image.width * echelle);
  toile.height = Math.round(image.height * echelle);
  const contexte = toile.getContext("2d");
  if (!contexte) return fichier;
  contexte.drawImage(image, 0, 0, toile.width, toile.height);
  image.close();
  let qualite = 0.85;
  let blob: Blob | null = null;
  do {
    blob = await new Promise<Blob | null>((resoudre) => toile.toBlob(resoudre, "image/jpeg", qualite));
    qualite -= 0.15;
  } while (blob && blob.size > OCTETS_MAX && qualite > 0.2);
  if (!blob) return fichier;
  const nom = fichier.name.replace(/\.[^.]+$/, "") || "page";
  return new File([blob], `${nom}.jpg`, { type: "image/jpeg" });
}

export function AjouterUnDocument({ patientId }: { patientId: string }) {
  const [etat, envoyer] = useActionState<EtatDuDocument, FormData>(ajouterDocument, null);
  const [enCours, demarrer] = useTransition();
  const [preparation, setPreparation] = useState(false);
  const [erreurLocale, setErreurLocale] = useState<string | null>(null);

  async function soumettre(evenement: FormEvent<HTMLFormElement>) {
    evenement.preventDefault();
    setErreurLocale(null);
    setPreparation(true);
    try {
      const donnees = new FormData(evenement.currentTarget);
      const fichiers = donnees.getAll("pages").filter((p): p is File => typeof p !== "string" && p.size > 0);
      donnees.delete("pages");
      for (const fichier of fichiers) {
        const page = await compresser(fichier);
        donnees.append("pages", page, page.name);
      }
      demarrer(() => envoyer(donnees));
    } catch {
      setErreurLocale("Une photo n’a pas pu être préparée. Reprenez-la ou choisissez un autre fichier.");
    } finally {
      setPreparation(false);
    }
  }

  const erreur = erreurLocale ?? etat?.erreur;
  return (
    <details className="sn-replie">
      <summary className="lf-btn lf-btn--secondary lf-btn--pro">
        <Icon name="plus" size={20} />
        <span className="lf-btn-label">Ajouter un document apporté par le patient</span>
      </summary>
      <div className="sn-replie-corps">
        <form onSubmit={soumettre} className="lf-formulaire">
          <input type="hidden" name="patient_id" value={patientId} />
          {erreur && <Alert tone="danger" title={erreur} />}
          <div className="lf-field lf-field--pro">
            <label className="lf-field-label" htmlFor="document-type">
              Type de document
            </label>
            <select id="document-type" name="type" className="lf-input sn-select" required defaultValue="">
              <option value="" disabled>
                Choisir un type
              </option>
              {TYPES_DE_DOCUMENT.map(([code, libelle]) => (
                <option key={code} value={code}>
                  {libelle}
                </option>
              ))}
            </select>
          </div>
          <TextInput
            name="annee"
            label="Année du document"
            size="pro"
            placeholder="2019"
            inputMode="numeric"
            pattern="(19|20)[0-9]{2}"
            maxLength={4}
            required
          />
          <TextInput name="etablissement" label="Établissement d’origine (tel qu’écrit)" size="pro" placeholder="CHD Borgou" maxLength={200} />
          <fieldset className="sn-fieldset">
            <legend className="lf-field-label">Lisibilité</legend>
            <div className="sn-radios sn-radios--ligne">
              <label className="sn-radio">
                <input type="radio" name="lisibilite" value="lisible" defaultChecked required />
                Lisible
              </label>
              <label className="sn-radio">
                <input type="radio" name="lisibilite" value="partiel" required />
                Partiellement lisible
              </label>
            </div>
          </fieldset>
          <div className="lf-field lf-field--pro">
            <label className="lf-field-label" htmlFor="document-pages">
              Pages : photos ou PDF, dans l’ordre (vingt au plus)
            </label>
            <input
              id="document-pages"
              name="pages"
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              multiple
              required
              className="lf-input"
            />
          </div>
          <Button type="submit" size="pro" icon="check" disabled={preparation || enCours}>
            {preparation ? "Préparation des pages…" : enCours ? "Enregistrement…" : "Enregistrer le document"}
          </Button>
        </form>
      </div>
    </details>
  );
}
