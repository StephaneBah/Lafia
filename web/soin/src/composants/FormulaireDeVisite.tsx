"use client";

import { Alert, Button, Icon, Picto, StatusBadge, TextInput } from "@lafia/design";
import { useActionState, useRef, useState, type FormEvent } from "react";

import { enregistrerVisite, type EtatDeVisite } from "../app/actions";
import { adresseDuPatient } from "../lib/adresses";
import {
  allergieDuProduit,
  LIBELLES_DES_MOMENTS,
  MOMENTS,
  type Allergie,
  type Catalogue,
  type Moment,
  type Patient,
  type TitreDeCas,
} from "../lib/types";
import { RecuImprimable } from "./Recu";

/** Les mesures numériques du catalogue, dans l'ordre du formulaire ; tension et TDR à part. */
const MESURES_SIMPLES: { code: string; libelle: string; mode: "decimal" | "numeric" }[] = [
  { code: "8310-5", libelle: "Température (°C)", mode: "decimal" },
  { code: "8867-4", libelle: "Pouls (/min)", mode: "numeric" },
  { code: "29463-7", libelle: "Poids (kg)", mode: "decimal" },
  { code: "59408-5", libelle: "SpO2 (%)", mode: "numeric" },
  { code: "2339-0", libelle: "Glycémie (g/L)", mode: "decimal" },
  { code: "718-7", libelle: "Hémoglobine (g/dL)", mode: "decimal" },
];

const ETAPES = ["Motif", "Mesures", "Diagnostic", "Ordonnance", "Récapitulatif"] as const;
const TYPES_DE_VISITE: Record<string, string> = {
  consultation: "Consultation",
  "soins-infirmiers": "Soins infirmiers",
  continuite: "Visite de continuité",
};

/** Ce que le récapitulatif relit du formulaire avant l'envoi. */
type Apercu = {
  type: string;
  motif: string;
  mesures: { libelle: string; valeur: string }[];
  diagnostic: string | null;
  confirme: boolean;
  lignes: { libelle: string; quantite: string; posologie: string | null; allergie: string | null }[];
};

/** L'indicateur d'étapes : numéro, mot et état, jamais la couleur seule. */
function Etapes({ courante }: { courante: number }) {
  return (
    <ol className="sn-etapes" aria-label="Étapes de la visite">
      {ETAPES.map((libelle, i) => {
        const etat = i < courante ? "faite" : i === courante ? "courante" : "a-venir";
        return (
          <li key={libelle} className={`sn-etape sn-etape--${etat}`} aria-current={i === courante ? "step" : undefined}>
            <span className="sn-etape-numero" aria-hidden="true">
              {i < courante ? <Icon name="check" size={16} /> : i + 1}
            </span>
            <span>{libelle}</span>
            {i < courante && <span className="sn-visuellement-cache"> (faite)</span>}
          </li>
        );
      })}
    </ol>
  );
}

export function FormulaireDeVisite({
  patientId,
  patient,
  allergies,
  cas,
  catalogue,
  role,
  adresseDuCarnet,
}: {
  patientId: string;
  patient: Patient;
  allergies: Allergie[];
  cas: TitreDeCas;
  catalogue: Catalogue;
  role: "médecin" | "infirmier";
  adresseDuCarnet: string;
}) {
  const [etat, envoyer, enCours] = useActionState<EtatDeVisite, FormData>(enregistrerVisite, null);
  const [etape, setEtape] = useState(0);
  const [lignes, setLignes] = useState<number[]>([]);
  const [produits, setProduits] = useState<Record<number, string>>({});
  const [suivante, setSuivante] = useState(0);
  const [apercu, setApercu] = useState<Apercu | null>(null);
  const formulaire = useRef<HTMLFormElement>(null);
  const sections = useRef<(HTMLElement | null)[]>([]);
  const titre = useRef<HTMLHeadingElement>(null);
  const nom = `${patient.prenoms} ${patient.nom}`;
  const parCode = new Map(catalogue.produits.map((p) => [p.code, p]));
  const medicaments = catalogue.produits.filter((p) => p.code.startsWith("MED-"));
  const autres = catalogue.produits.filter((p) => !p.code.startsWith("MED-"));
  const derniere = ETAPES.length - 1;

  if (etat?.recu) {
    return <RecuImprimable recu={etat.recu} catalogue={catalogue} patientId={patientId} adresseDuCarnet={adresseDuCarnet} />;
  }

  /** Les champs d'une étape sont-ils valides ? Sinon on y revient et le navigateur montre le premier en défaut. */
  function valide(n: number): boolean {
    const section = sections.current[n];
    if (!section) return true;
    const champs = Array.from(section.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>("input, select, textarea"));
    const enDefaut = champs.find((c) => !c.checkValidity());
    if (!enDefaut) return true;
    setEtape(n);
    setTimeout(() => enDefaut.reportValidity(), 0);
    return false;
  }

  function relire(): Apercu {
    const d = new FormData(formulaire.current!);
    const t = (nom: string) => String(d.get(nom) ?? "").trim();
    const mesures = MESURES_SIMPLES.filter((m) => t(`m-${m.code}`)).map((m) => ({ libelle: m.libelle, valeur: t(`m-${m.code}`) }));
    if (t("m-85354-9") && t("m-85354-9-2")) mesures.push({ libelle: "Tension (mm Hg)", valeur: `${t("m-85354-9")}/${t("m-85354-9-2")}` });
    if (t("m-70569-9")) mesures.push({ libelle: "TDR paludisme", valeur: t("m-70569-9") });
    const diagnostic = catalogue.diagnostics.find((x) => x.code === t("diagnostic"))?.libelle ?? null;
    return {
      type: TYPES_DE_VISITE[t("type")] ?? t("type"),
      motif: t("motif"),
      mesures,
      diagnostic,
      confirme: d.get("confirme") === "on",
      lignes: lignes
        .map((i) => {
          const produit = parCode.get(t(`l-${i}-produit`));
          if (!produit) return null;
          const moments = d.getAll(`l-${i}-moments`) as Moment[];
          const medicament = produit.code.startsWith("MED-");
          return {
            libelle: produit.libelle,
            quantite: `${t(`l-${i}-quantite`)}${produit.forme ? ` ${produit.forme}` : ""}`,
            posologie: medicament
              ? `${t(`l-${i}-dose`)} par prise · ${moments.map((m) => LIBELLES_DES_MOMENTS[m].toLowerCase()).join(", ") || "sans moment"} · ${t(`l-${i}-jours`)} jours`
              : null,
            allergie: allergieDuProduit(produit, allergies)?.libelle ?? null,
          };
        })
        .filter((l) => l !== null),
    };
  }

  function aller(n: number) {
    if (n > etape) for (let e = etape; e < n; e++) if (!valide(e)) return;
    if (n === derniere) setApercu(relire());
    setEtape(n);
    setTimeout(() => titre.current?.focus(), 0);
  }

  function soumettre(e: FormEvent<HTMLFormElement>) {
    // Entrée dans un champ avance d'une étape ; l'envoi ne part que du récapitulatif, tout valide.
    if (etape < derniere) {
      e.preventDefault();
      aller(etape + 1);
      return;
    }
    for (let n = 0; n < derniere; n++)
      if (!valide(n)) {
        e.preventDefault();
        return;
      }
  }

  function ajouter() {
    setLignes((l) => [...l, suivante]);
    setSuivante((n) => n + 1);
  }

  const section = (n: number) => ({
    ref: (el: HTMLElement | null) => {
      sections.current[n] = el;
    },
    hidden: etape !== n,
    className: "sn-etape-corps",
  });

  return (
    <form ref={formulaire} action={envoyer} onSubmit={soumettre} noValidate className="sn-panneau lf-card sn-formulaire">
      <input type="hidden" name="patient_id" value={patientId} />
      <input type="hidden" name="cas" value={cas.id} />
      <input type="hidden" name="patient" value={nom} />
      <input type="hidden" name="lignes" value={lignes.join(",")} />
      <h2 className="sn-h2">{`Nouvelle visite · cas « ${cas.motif || "en cours"} »`}</h2>
      {!cas.de_mon_etablissement && (
        <Alert tone="info" title={`Cas ouvert à ${cas.etablissement}`}>
          Cette visite le continue ici : votre établissement entre en relation de soin avec le patient.
        </Alert>
      )}
      <Etapes courante={etape} />
      <h3 ref={titre} tabIndex={-1} className="sn-h3">{`Étape ${etape + 1} sur ${ETAPES.length} : ${ETAPES[etape]}`}</h3>
      {etat?.erreur && <Alert tone="danger" title={etat.erreur} />}

      <section {...section(0)} aria-label="Motif">
        <div className="sn-grille">
          <div className="lf-field lf-field--pro">
            <label className="lf-field-label" htmlFor="type">
              Type de visite
            </label>
            <select id="type" name="type" className="lf-input sn-select" defaultValue={role === "infirmier" ? "soins-infirmiers" : "consultation"}>
              {Object.entries(TYPES_DE_VISITE).map(([code, libelle]) => (
                <option key={code} value={code}>
                  {libelle}
                </option>
              ))}
            </select>
          </div>
          <TextInput name="motif" label="Motif de la visite" size="pro" required maxLength={300} defaultValue={cas.motif} />
        </div>
      </section>

      <section {...section(1)} aria-label="Mesures">
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
        <p className="sn-meta">Toutes les mesures sont facultatives : ne remplissez que celles prises.</p>
      </section>

      <section {...section(2)} aria-label="Diagnostic">
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
      </section>

      <section {...section(3)} aria-label="Ordonnance">
        <div className="sn-colonne">
          {lignes.length === 0 && <div className="sn-vide">Pas d’ordonnance pour cette visite.</div>}
          {lignes.map((i, rang) => {
            const produit = parCode.get(produits[i] ?? "");
            const allergie = allergieDuProduit(produit, allergies);
            const medicament = !produit || produit.code.startsWith("MED-");
            return (
              <fieldset key={i} className={`sn-fieldset sn-ligne${allergie ? " sn-ligne--allergie" : ""}`}>
                <legend className="sn-visuellement-cache">{`Ligne ${rang + 1}`}</legend>
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
                <TextInput
                  name={`l-${i}-quantite`}
                  label={produit?.forme ? `Quantité (${produit.forme})` : "Quantité"}
                  size="pro"
                  inputMode="numeric"
                  pattern="[0-9]+"
                  defaultValue="1"
                  required
                />
                {medicament && (
                  <>
                    <TextInput
                      name={`l-${i}-dose`}
                      label={produit?.forme ? `Dose par prise (${produit.forme})` : "Dose par prise"}
                      size="pro"
                      inputMode="decimal"
                      pattern="[0-9]+([.,][0-9]+)?"
                      defaultValue="1"
                    />
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
                {allergie && produit && (
                  <div className="sn-plein">
                    <Alert tone="danger" title={`Allergie déclarée : ${allergie.libelle}`}>
                      {`${produit.libelle} appartient à la classe ${allergie.code_atc}. Retirez la ligne, ou gardez-la en connaissance de cause : la pharmacie sera alertée de toute façon.`}
                    </Alert>
                    <label className="sn-coche sn-coche--danger">
                      <input type="checkbox" name={`l-${i}-garder`} required />
                      Je garde cette ligne malgré l’allergie
                    </label>
                  </div>
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
          <div>
            <Button size="pro" variant="secondary" icon="plus" onClick={ajouter}>
              Ajouter une ligne
            </Button>
          </div>
        </div>
      </section>

      <section {...section(4)} aria-label="Récapitulatif">
        {apercu && (
          <dl className="sn-recap">
            <div>
              <dt>Visite</dt>
              <dd>{`${apercu.type} · ${apercu.motif}`}</dd>
            </div>
            <div>
              <dt>Mesures</dt>
              <dd>{apercu.mesures.length ? apercu.mesures.map((m) => `${m.libelle} : ${m.valeur}`).join(" · ") : "Aucune"}</dd>
            </div>
            <div>
              <dt>Diagnostic</dt>
              <dd>{apercu.diagnostic ? `${apercu.diagnostic} · ${apercu.confirme ? "confirmé" : "provisoire"}` : "Aucun"}</dd>
            </div>
            <div>
              <dt>Ordonnance</dt>
              <dd>
                {apercu.lignes.length === 0 ? (
                  "Aucune"
                ) : (
                  <ul className="sn-puces">
                    {apercu.lignes.map((l, n) => (
                      <li key={n}>
                        <b>{l.libelle}</b>
                        {` · ${l.quantite}`}
                        {l.posologie && ` · ${l.posologie}`}
                        {l.allergie && <StatusBadge status="allergie" size="pro" label={`Allergie : ${l.allergie}`} />}
                      </li>
                    ))}
                  </ul>
                )}
              </dd>
            </div>
          </dl>
        )}
        <p className="sn-meta">Après l’enregistrement, le reçu s’imprime avec le numéro d’ordonnance et un nouveau code carnet.</p>
      </section>

      <div className="sn-actions sn-actions--etapes">
        {etape > 0 && (
          <Button size="pro" variant="secondary" icon="arrow-left" onClick={() => aller(etape - 1)}>
            Retour
          </Button>
        )}
        {etape < derniere ? (
          <Button size="pro" onClick={() => aller(etape + 1)}>
            {`Suivant : ${ETAPES[etape + 1]}`}
          </Button>
        ) : (
          <Button type="submit" size="pro" icon="check" loading={enCours}>
            {lignes.length ? "Enregistrer la visite et émettre" : "Enregistrer la visite"}
          </Button>
        )}
        <span className="sn-espace" />
        <Button href={adresseDuPatient(patientId)} size="pro" variant="ghost">
          Annuler
        </Button>
      </div>
    </form>
  );
}
