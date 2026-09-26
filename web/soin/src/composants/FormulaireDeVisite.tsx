"use client";

import { Alert, Button, Card, Picto, StatusBadge, TextInput } from "@lafia/design";
import { useActionState, useState } from "react";

import { enregistrerVisite, type EtatDeVisite } from "../app/actions";
import { allergieDuProduit, MOMENTS, type Allergie, type Catalogue, type Patient, type TitreDeCas } from "../lib/types";
import { RecuImprimable } from "./Recu";

const LIBELLES_DES_MOMENTS = { matin: "Matin", midi: "Midi", soir: "Soir", nuit: "Nuit" } as const;

/** Les mesures numériques du catalogue, dans l'ordre du formulaire ; tension et TDR à part. */
const MESURES_SIMPLES: { code: string; libelle: string; mode: "decimal" | "numeric" }[] = [
  { code: "8310-5", libelle: "Température (°C)", mode: "decimal" },
  { code: "8867-4", libelle: "Pouls (/min)", mode: "numeric" },
  { code: "29463-7", libelle: "Poids (kg)", mode: "decimal" },
  { code: "59408-5", libelle: "SpO2 (%)", mode: "numeric" },
  { code: "2339-0", libelle: "Glycémie (g/L)", mode: "decimal" },
  { code: "718-7", libelle: "Hémoglobine (g/dL)", mode: "decimal" },
];

export function FormulaireDeVisite({
  npi,
  patient,
  allergies,
  cas,
  catalogue,
  role,
  adresseDuCarnet,
}: {
  npi: string;
  patient: Patient;
  allergies: Allergie[];
  cas: TitreDeCas;
  catalogue: Catalogue;
  role: "médecin" | "infirmier";
  adresseDuCarnet: string;
}) {
  const [etat, envoyer, enCours] = useActionState<EtatDeVisite, FormData>(enregistrerVisite, null);
  const [lignes, setLignes] = useState<number[]>([]);
  const [produits, setProduits] = useState<Record<number, string>>({});
  const [suivante, setSuivante] = useState(0);
  const nom = `${patient.prenoms} ${patient.nom}`;
  const parCode = new Map(catalogue.produits.map((p) => [p.code, p]));
  const medicaments = catalogue.produits.filter((p) => p.code.startsWith("MED-"));
  const autres = catalogue.produits.filter((p) => !p.code.startsWith("MED-"));

  if (etat?.recu) {
    return <RecuImprimable recu={etat.recu} catalogue={catalogue} npi={npi} adresseDuCarnet={adresseDuCarnet} />;
  }

  const alertes = lignes
    .map((i) => ({ i, produit: parCode.get(produits[i] ?? ""), allergie: allergieDuProduit(parCode.get(produits[i] ?? ""), allergies) }))
    .filter((l) => l.allergie);

  function ajouter() {
    setLignes((l) => [...l, suivante]);
    setSuivante((n) => n + 1);
  }

  return (
    <form action={envoyer} className="sn-panneau lf-card sn-formulaire">
      <input type="hidden" name="npi" value={npi} />
      <input type="hidden" name="cas" value={cas.id} />
      <input type="hidden" name="patient" value={nom} />
      <input type="hidden" name="lignes" value={lignes.join(",")} />
      <h1 className="sn-h3">{`Nouvelle visite · ${nom} · cas « ${cas.motif} »`}</h1>
      {!cas.de_mon_etablissement && (
        <Alert tone="info" title={`Cas ouvert à ${cas.etablissement}`}>
          Cette visite le continue ici : votre établissement entre en relation de soin avec le patient.
        </Alert>
      )}
      {allergies.length > 0 && (
        <div className="sn-allergie" role="note">
          <b>
            <Picto name="allergie" size={24} decorative />
            {`Allergie : ${allergies.map((a) => a.libelle).join(", ")}`}
          </b>
        </div>
      )}
      {etat?.erreur && <Alert tone="danger" title={etat.erreur} />}

      <div className="sn-grille">
        <div className="lf-field lf-field--pro">
          <label className="lf-field-label" htmlFor="type">
            Type de visite
          </label>
          <select id="type" name="type" className="lf-input sn-select" defaultValue={role === "infirmier" ? "soins-infirmiers" : "consultation"}>
            <option value="consultation">Consultation</option>
            <option value="soins-infirmiers">Soins infirmiers</option>
            <option value="continuite">Visite de continuité</option>
          </select>
        </div>
        <TextInput name="motif" label="Motif de la visite" size="pro" required maxLength={300} defaultValue={cas.motif} />
      </div>

      <h2 className="sn-h3">Mesures</h2>
      <div className="sn-grille sn-grille--mesures">
        {MESURES_SIMPLES.map((m) => (
          <TextInput key={m.code} name={`m-${m.code}`} label={m.libelle} size="pro" inputMode={m.mode} pattern="[0-9]+([.,][0-9]+)?" />
        ))}
        <fieldset className="sn-fieldset sn-tension">
          <legend className="lf-field-label">Tension (mm Hg)</legend>
          <div className="sn-tension-champs">
            <TextInput name="m-85354-9" label="Systolique" size="pro" inputMode="numeric" pattern="[0-9]+" />
            <TextInput name="m-85354-9-2" label="Diastolique" size="pro" inputMode="numeric" pattern="[0-9]+" />
          </div>
        </fieldset>
        <div className="lf-field lf-field--pro">
          <label className="lf-field-label" htmlFor="tdr">
            TDR paludisme
          </label>
          <select id="tdr" name="m-70569-9" className="lf-input sn-select" defaultValue="">
            <option value="">Non fait</option>
            <option value="positif">Positif</option>
            <option value="négatif">Négatif</option>
          </select>
        </div>
      </div>

      <h2 className="sn-h3">Diagnostic</h2>
      <div className="sn-grille">
        <div className="lf-field lf-field--pro">
          <label className="lf-field-label" htmlFor="diagnostic">
            Diagnostic
          </label>
          <select id="diagnostic" name="diagnostic" className="lf-input sn-select" defaultValue="">
            <option value="">Aucun pour l’instant</option>
            {catalogue.diagnostics.map((d) => (
              <option key={d.code} value={d.code}>
                {d.libelle}
              </option>
            ))}
          </select>
        </div>
        {role === "médecin" ? (
          <label className="sn-coche">
            <input type="checkbox" name="confirme" />
            Diagnostic confirmé
          </label>
        ) : (
          <p className="sn-meta sn-coche">Le diagnostic d’un infirmier reste provisoire : un médecin le confirme.</p>
        )}
        <div className="lf-field lf-field--pro sn-plein">
          <label className="lf-field-label" htmlFor="note">
            Note
          </label>
          <textarea id="note" name="note" className="sn-textarea" maxLength={1000} />
        </div>
      </div>

      <h2 className="sn-h3">Ordonnance</h2>
      {lignes.length === 0 && <div className="sn-vide">Pas d’ordonnance pour cette visite.</div>}
      {lignes.map((i) => {
        const produit = parCode.get(produits[i] ?? "");
        const allergie = allergieDuProduit(produit, allergies);
        const medicament = !produit || produit.code.startsWith("MED-");
        return (
          <fieldset key={i} className="sn-fieldset sn-ligne">
            <legend className="sn-visuellement-cache">{`Ligne ${i + 1}`}</legend>
            <div className="lf-field lf-field--pro sn-ligne-produit">
              <label className="lf-field-label" htmlFor={`l-${i}-produit`}>
                Produit ou acte
              </label>
              <select
                id={`l-${i}-produit`}
                name={`l-${i}-produit`}
                className="lf-input sn-select"
                required
                value={produits[i] ?? ""}
                onChange={(e) => setProduits((p) => ({ ...p, [i]: e.target.value }))}
              >
                <option value="" disabled>
                  Choisir dans les tarifs de l’établissement
                </option>
                <optgroup label="Médicaments">
                  {medicaments.map((p) => (
                    <option key={p.code} value={p.code}>
                      {p.libelle}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Actes et examens">
                  {autres.map((p) => (
                    <option key={p.code} value={p.code}>
                      {p.libelle}
                    </option>
                  ))}
                </optgroup>
              </select>
            </div>
            <TextInput name={`l-${i}-quantite`} label="Quantité" size="pro" inputMode="numeric" pattern="[0-9]+" defaultValue="1" required />
            {medicament && (
              <>
                <TextInput name={`l-${i}-dose`} label="Dose par prise" size="pro" inputMode="decimal" pattern="[0-9]+([.,][0-9]+)?" defaultValue="1" />
                <TextInput name={`l-${i}-jours`} label="Jours" size="pro" inputMode="numeric" pattern="[0-9]+" defaultValue="3" />
                <div className="sn-moments" role="group" aria-label="Moments de prise">
                  {MOMENTS.map((m) => (
                    <label key={m} className="sn-moment">
                      <input type="checkbox" name={`l-${i}-moments`} value={m} defaultChecked={m === "matin" || m === "soir"} />
                      <Picto name={m} size={24} decorative />
                      {LIBELLES_DES_MOMENTS[m]}
                    </label>
                  ))}
                </div>
              </>
            )}
            <div className="sn-ligne-fin">
              {allergie && <StatusBadge status="allergie" size="pro" />}
              <Button size="pro" variant="ghost" icon="x" onClick={() => setLignes((l) => l.filter((x) => x !== i))}>
                Retirer
              </Button>
            </div>
          </fieldset>
        );
      })}
      {alertes.map(({ i, produit, allergie }) => (
        <Alert key={i} tone="danger" title={`${produit?.libelle ?? ""} : allergie déclarée (${allergie?.libelle})`}>
          Retirez la ligne ou gardez-la en connaissance de cause. La pharmacie sera alertée de toute façon.
        </Alert>
      ))}
      <div>
        <Button size="pro" variant="secondary" icon="plus" onClick={ajouter}>
          Ajouter une ligne
        </Button>
      </div>

      <div className="sn-actions">
        <Button type="submit" size="pro" icon="check" loading={enCours}>
          {lignes.length ? "Enregistrer la visite et émettre" : "Enregistrer la visite"}
        </Button>
        <Button href={`/patients/${npi}`} size="pro" variant="ghost">
          Annuler
        </Button>
      </div>
    </form>
  );
}
