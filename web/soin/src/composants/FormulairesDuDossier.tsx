import { Button, Icon, Picto, TextInput } from "@lafia/design";
import type { ReactNode } from "react";

import {
  ajouterAntecedent,
  ajouterTraitement,
  declarerAllergie,
  enregistrerGroupeSanguin,
} from "../app/actions";
import { GROUPES_SANGUINS, LIBELLES_DES_MOMENTS, LIENS_DE_PARENTE, MOMENTS, type Catalogue } from "../lib/types";

// Les petits formulaires de la synthèse, chacun replié derrière son bouton : on ouvre, on remplit,
// on enregistre, et le bandeau se met à jour. Sans script : <details> s'ouvre au clavier comme à la souris.

function Replie({ titre, icone, children }: { titre: string; icone: "plus" | "pill"; children: ReactNode }) {
  return (
    <details className="sn-replie">
      <summary className="lf-btn lf-btn--secondary lf-btn--pro">
        <Icon name={icone} size={20} />
        <span className="lf-btn-label">{titre}</span>
      </summary>
      <div className="sn-replie-corps">{children}</div>
    </details>
  );
}

const Patient = ({ id, documentId }: { id: string; documentId?: string }) => (
  <>
    <input type="hidden" name="patient_id" value={id} />
    {documentId && <input type="hidden" name="document_id" value={documentId} />}
  </>
);

function Choix({ id, nom, libelle, children, requis }: { id: string; nom: string; libelle: string; children: ReactNode; requis?: boolean }) {
  return (
    <div className="lf-field lf-field--pro">
      <label className="lf-field-label" htmlFor={id}>
        {libelle}
      </label>
      <select id={id} name={nom} className="lf-input sn-select" required={requis} defaultValue="">
        {children}
      </select>
    </div>
  );
}

/** Avec `documentId`, l'antécédent est reporté depuis ce Document : il en porte l'origine. */
export function AjouterAntecedent({ patientId, documentId }: { patientId: string; documentId?: string }) {
  return (
    <Replie titre={documentId ? "Reporter un antécédent" : "Ajouter un antécédent"} icone="plus">
      <form action={ajouterAntecedent} className="lf-formulaire">
        <Patient id={patientId} documentId={documentId} />
        <fieldset className="sn-fieldset">
          <legend className="lf-field-label">Type</legend>
          <div className="sn-radios sn-radios--ligne">
            {[
              ["medical", "Médical"],
              ["chirurgical", "Chirurgical"],
              ["familial", "Familial"],
            ].map(([valeur, libelle], i) => (
              <label key={valeur} className="sn-radio">
                <input type="radio" name="type" value={valeur} defaultChecked={i === 0} required />
                {libelle}
              </label>
            ))}
          </div>
        </fieldset>
        <TextInput name="libelle" label="Antécédent" size="pro" placeholder="Hypertension artérielle" required maxLength={200} />
        <TextInput name="depuis" label="Depuis (année ou période)" size="pro" placeholder="2019" maxLength={40} />
        <Choix id="lien" nom="lien" libelle="Lien de parenté (antécédent familial)">
          <option value="">Sans objet</option>
          {LIENS_DE_PARENTE.map(([code, libelle]) => (
            <option key={code} value={code}>
              {libelle}
            </option>
          ))}
        </Choix>
        <label className="sn-coche">
          <input type="checkbox" name="resolu" />
          Résolu, n’est plus actif
        </label>
        <Button type="submit" size="pro" icon="check">
          Enregistrer l’antécédent
        </Button>
      </form>
    </Replie>
  );
}

export function AjouterTraitement({ patientId, catalogue }: { patientId: string; catalogue: Catalogue | null }) {
  const medicaments = (catalogue?.produits ?? []).filter((p) => p.code.startsWith("MED-"));
  return (
    <Replie titre="Ajouter un traitement" icone="pill">
      <form action={ajouterTraitement} className="lf-formulaire">
        <Patient id={patientId} />
        <Choix id="traitement-produit" nom="produit" libelle="Médicament du catalogue">
          <option value="">Hors catalogue : je l’écris</option>
          {medicaments.map((p) => (
            <option key={p.code} value={p.code}>
              {p.libelle}
            </option>
          ))}
        </Choix>
        <TextInput name="libelle" label="Ou médicament hors catalogue" size="pro" placeholder="Amlodipine 5 mg" maxLength={200} />
        <TextInput name="posologie" label="Posologie" size="pro" placeholder="1 comprimé le matin" required maxLength={200} />
        <div className="sn-moments" role="group" aria-label="Moments de prise">
          {MOMENTS.map((m) => (
            <label key={m} className="sn-moment">
              <input type="checkbox" name="moments" value={m} />
              <Picto name={m} size={24} decorative />
              {LIBELLES_DES_MOMENTS[m]}
            </label>
          ))}
        </div>
        <Button type="submit" size="pro" icon="check">
          Enregistrer le traitement
        </Button>
      </form>
    </Replie>
  );
}

export function EnregistrerGroupeSanguin({ patientId, actuel }: { patientId: string; actuel: string | null }) {
  return (
    <Replie titre={actuel ? "Corriger le groupe sanguin" : "Enregistrer le groupe sanguin"} icone="plus">
      <form action={enregistrerGroupeSanguin} className="lf-formulaire">
        <Patient id={patientId} />
        <fieldset className="sn-fieldset">
          <legend className="lf-field-label">Groupe sanguin</legend>
          <div className="sn-radios sn-radios--groupes">
            {GROUPES_SANGUINS.map((g) => (
              <label key={g} className="sn-radio">
                <input type="radio" name="groupe" value={g} required defaultChecked={g === actuel} />
                {g}
              </label>
            ))}
          </div>
        </fieldset>
        <Button type="submit" size="pro" icon="check">
          Enregistrer le groupe
        </Button>
      </form>
    </Replie>
  );
}

/** Avec `documentId`, l'allergie est reportée depuis ce Document : elle en porte l'origine. */
export function DeclarerAllergie({
  patientId,
  catalogue,
  documentId,
}: {
  patientId: string;
  catalogue: Catalogue | null;
  documentId?: string;
}) {
  const allergies = catalogue?.allergies ?? [];
  return (
    <Replie titre={documentId ? "Reporter une allergie" : "Déclarer une allergie"} icone="plus">
      <form action={declarerAllergie} className="lf-formulaire">
        <Patient id={patientId} documentId={documentId} />
        <Choix id="allergie" nom="allergie" libelle="Classe de médicaments" requis>
          <option value="" disabled>
            {allergies.length ? "Choisir une classe" : "Catalogue indisponible"}
          </option>
          {allergies.map((a) => (
            <option key={a.code_atc} value={`${a.code_atc}|${a.libelle}`}>
              {`${a.libelle} (${a.code_atc})`}
            </option>
          ))}
        </Choix>
        <Button type="submit" size="pro" variant="danger" icon="warning-octagon" disabled={allergies.length === 0}>
          Déclarer l’allergie
        </Button>
      </form>
    </Replie>
  );
}
