import { Alert, Button, Card, Icon, StatusBadge, TextInput, formatDate } from "@lafia/design";
import { connection } from "next/server";

import { soignantConnecte } from "../../../composants/Cadre";
import { CourbeDeTemperature } from "../../../composants/CourbeDeTemperature";
import { OrigineDeLEntree } from "../../../composants/Documents";
import { EspacePatient, PatientIntrouvable, adresseDuPatient } from "../../../composants/EspacePatient";
import { valeurDeMesure } from "../../../composants/FilDuCas";
import {
  AjouterAntecedent,
  AjouterTraitement,
  DeclarerAllergie,
  EnregistrerGroupeSanguin,
} from "../../../composants/FormulairesDuDossier";
import { soin } from "../../../lib/soin";
import { libelleDuLien, type Bandeau, type Catalogue, type Dossier, type PointDeMesure } from "../../../lib/types";
import { accesDUrgence, arreterTraitement, ouvrirCas } from "../../actions";

type Parametres = { params: Promise<{ patientId: string }>; searchParams: Promise<Record<string, string | undefined>> };

const MOTIFS_D_URGENCE = ["Patient inconscient", "Détresse vitale", "Hémorragie grave", "Autre motif (à préciser)"];

const MESSAGES: Record<string, { ton: "succes" | "danger"; titre: string }> = {
  "ok=allergie": { ton: "succes", titre: "Allergie déclarée : la pharmacie arrêtera toute ligne de cette classe." },
  "ok=antecedent": { ton: "succes", titre: "Antécédent enregistré." },
  "ok=traitement": { ton: "succes", titre: "Traitement au long cours enregistré." },
  "ok=arret": { ton: "succes", titre: "Traitement arrêté." },
  "ok=groupe": { ton: "succes", titre: "Groupe sanguin enregistré." },
  "erreur=motif": { ton: "danger", titre: "Donnez un motif pour ouvrir le cas." },
  "erreur=cas": { ton: "danger", titre: "Le cas n’a pas été ouvert. Réessayez." },
  "erreur=raison": { ton: "danger", titre: "Choisissez un motif d’urgence et précisez-le : dix caractères au moins." },
  "erreur=urgence": { ton: "danger", titre: "Le service soin n’a pas ouvert l’accès d’urgence. Réessayez." },
  "erreur=allergie": { ton: "danger", titre: "L’allergie n’a pas été déclarée. Choisissez une classe du catalogue." },
  "erreur=antecedent": { ton: "danger", titre: "L’antécédent n’a pas été enregistré. Donnez au moins son libellé." },
  "erreur=lien": { ton: "danger", titre: "Un antécédent familial demande le lien de parenté." },
  "erreur=traitement": { ton: "danger", titre: "Le traitement n’a pas été enregistré. Donnez le médicament et la posologie." },
  "erreur=groupe": { ton: "danger", titre: "Le groupe sanguin n’a pas été enregistré." },
};

function Messages({ recherche }: { recherche: Record<string, string | undefined> }) {
  const cles = Object.entries(recherche).map(([cle, valeur]) => `${cle}=${valeur}`);
  return (
    <>
      {recherche.urgence && (
        <Alert tone="urgence" title="Accès d’urgence ouvert">
          L’accès est tracé avec sa raison, et le patient le verra dans son carnet.
        </Alert>
      )}
      {cles
        .filter((c) => MESSAGES[c])
        .map((c) => (
          <Alert key={c} tone={MESSAGES[c].ton} title={MESSAGES[c].titre} />
        ))}
    </>
  );
}

/** Sans relation de soin : un seul choix clair, ouvrir un cas, en continuer un, ou l'accès d'urgence. */
function Choix({ bandeau }: { bandeau: Bandeau }) {
  const id = bandeau.patient.id;
  const enCours = bandeau.cas.filter((c) => c.statut === "en-cours");
  return (
    <>
      <p className="sn-intro">
        <Icon name="lock-simple" size={20} />
        Le dossier s’ouvre par une relation de soin, le patient présent : ouvrez un cas ou continuez-en un.
      </p>
      <div className="sn-choix">
        <Card className="sn-panneau">
          <h2 className="sn-h2">Ouvrir un cas</h2>
          <form action={ouvrirCas} className="lf-formulaire">
            <input type="hidden" name="patient_id" value={id} />
            <TextInput name="motif" label="Motif du cas" size="pro" placeholder="Fièvre et toux" required maxLength={200} autoFocus />
            <Button type="submit" size="pro" icon="plus">
              Ouvrir le cas
            </Button>
          </form>
        </Card>

        <Card className="sn-panneau">
          <h2 className="sn-h2">Continuer un cas</h2>
          {enCours.length === 0 ? (
            <div className="sn-vide">Aucun cas en cours pour ce patient.</div>
          ) : (
            <ul className="sn-liste">
              {enCours.map((c) => (
                <li key={c.id} className="sn-cas">
                  <div>
                    <div className="sn-cas-titre">{c.motif || "Cas d’un autre établissement"}</div>
                    <div className="sn-meta">{[c.debut && `Depuis le ${formatDate(c.debut)}`, c.etablissement].filter(Boolean).join(" · ")}</div>
                  </div>
                  <StatusBadge status="encours" size="pro" />
                  <Button href={adresseDuPatient(id, `/visite?cas=${encodeURIComponent(c.id)}`)} size="pro" variant="secondary" icon="heartbeat">
                    Continuer ce cas
                  </Button>
                </li>
              ))}
            </ul>
          )}
          <p className="sn-meta">L’historique du cas s’affiche dès que votre visite l’a continué.</p>
        </Card>

        <Card className="sn-panneau sn-panneau--urgence">
          <h2 className="sn-h2 sn-h2--urgence">
            <Icon name="warning-octagon" size={20} />
            Accès d’urgence
          </h2>
          <p className="sn-meta">En urgence vitale seulement. La raison est tracée et le patient la verra dans son carnet.</p>
          <form action={accesDUrgence} className="lf-formulaire">
            <input type="hidden" name="patient_id" value={id} />
            <fieldset className="sn-fieldset">
              <legend className="lf-field-label">Motif</legend>
              <div className="sn-radios">
                {MOTIFS_D_URGENCE.map((motif) => (
                  <label key={motif} className="sn-radio">
                    <input type="radio" name="motif" value={motif} required />
                    {motif}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="lf-field lf-field--pro">
              <label className="lf-field-label" htmlFor="precision">
                Précision
              </label>
              <textarea id="precision" name="precision" className="sn-textarea" maxLength={400} placeholder="Amené par le SAMU, pas de proche présent." />
            </div>
            <Button type="submit" size="pro" variant="danger" icon="warning-octagon" block>
              Déclarer et ouvrir le dossier
            </Button>
          </form>
        </Card>
      </div>
    </>
  );
}

/** Les séries de mesures : celles du service, ou à défaut relevées sur les visites du dossier. */
function series(dossier: Dossier | null): Record<string, PointDeMesure[]> {
  if (dossier?.mesures_series) return dossier.mesures_series;
  const parCode: Record<string, PointDeMesure[]> = {};
  for (const c of dossier?.cas ?? [])
    for (const v of c.visites)
      for (const m of v.mesures) {
        const date = m.date ?? v.date;
        if (date) (parCode[m.code] ??= []).push({ date, valeur: m.valeur });
      }
  for (const liste of Object.values(parCode)) liste.sort((a, b) => a.date.localeCompare(b.date));
  return parCode;
}

function DernieresMesures({ series, catalogue }: { series: Record<string, PointDeMesure[]>; catalogue: Catalogue | null }) {
  const mesures = (catalogue?.mesures ?? []).filter((m) => series[m.code]?.length);
  if (mesures.length === 0) return <div className="sn-vide">Aucune mesure encore.</div>;
  return (
    <dl className="sn-mesures">
      {mesures.map((m) => {
        const serie = series[m.code];
        const derniere = serie[serie.length - 1];
        return (
          <div key={m.code}>
            <dt>{m.libelle}</dt>
            <dd>{valeurDeMesure(derniere.valeur, m.unite)}</dd>
            <dd className="sn-meta">{formatDate(derniere.date)}</dd>
          </div>
        );
      })}
    </dl>
  );
}

function Synthese({ bandeau, dossier, catalogue }: { bandeau: Bandeau; dossier: Dossier | null; catalogue: Catalogue | null }) {
  const id = bandeau.patient.id;
  const enCours = bandeau.cas.filter((c) => c.statut === "en-cours");
  const toutes = series(dossier);
  const antecedents = bandeau.antecedents ?? [];
  const groupes = [
    { titre: "Médicaux", liste: antecedents.filter((a) => a.type === "medical") },
    { titre: "Chirurgicaux", liste: antecedents.filter((a) => a.type === "chirurgical") },
  ];
  const familiaux = bandeau.familiaux ?? [];
  const traitements = bandeau.traitements ?? [];

  return (
    <div className="sn-synthese">
      <div className="sn-colonne">
        <Card className="sn-panneau">
          <h2 className="sn-h2">Cas en cours</h2>
          {enCours.length === 0 ? (
            <div className="sn-vide">
              Aucun cas en cours.{" "}
              <a href={adresseDuPatient(id, "/visite")} className="sn-lien">
                Ouvrir un cas
              </a>
            </div>
          ) : (
            <ul className="sn-liste">
              {enCours.map((c) => (
                <li key={c.id} className="sn-cas">
                  <div>
                    <div className="sn-cas-titre">{c.motif}</div>
                    <div className="sn-meta">{[c.debut && `Depuis le ${formatDate(c.debut)}`, c.etablissement].filter(Boolean).join(" · ")}</div>
                  </div>
                  <StatusBadge status="encours" size="pro" />
                  <Button href={adresseDuPatient(id, `/cas?cas=${encodeURIComponent(c.id)}`)} size="pro" icon="heartbeat">
                    Continuer
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="sn-panneau">
          <h2 className="sn-h2">Dernières mesures</h2>
          <DernieresMesures series={toutes} catalogue={catalogue} />
        </Card>

        <Card className="sn-panneau">
          <h2 className="sn-h2">Température</h2>
          <CourbeDeTemperature serie={toutes["8310-5"] ?? []} />
        </Card>
      </div>

      <div className="sn-colonne">
        <Card className="sn-panneau">
          <h2 className="sn-h2">Antécédents</h2>
          {groupes.map((g) => (
            <section key={g.titre} className="sn-sous-partie">
              <h3 className="sn-h3">{g.titre}</h3>
              {g.liste.length === 0 ? (
                <p className="sn-meta">Aucun déclaré.</p>
              ) : (
                <ul className="sn-puces">
                  {g.liste.map((a) => (
                    <li key={a.id}>
                      <b>{a.libelle}</b>
                      {a.depuis && <span className="sn-meta">{` · depuis ${a.depuis}`}</span>}
                      {!a.actif && <span className="sn-etiquette">Résolu</span>}
                      <OrigineDeLEntree origine={a.origine} />
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
          <section className="sn-sous-partie">
            <h3 className="sn-h3">Familiaux</h3>
            {familiaux.length === 0 ? (
              <p className="sn-meta">Aucun déclaré.</p>
            ) : (
              <ul className="sn-puces">
                {familiaux.map((f) => (
                  <li key={f.id}>
                    <b>{f.libelle}</b>
                    <span className="sn-meta">{` · ${libelleDuLien(f.lien)}`}</span>
                    <OrigineDeLEntree origine={f.origine} />
                  </li>
                ))}
              </ul>
            )}
          </section>
          <AjouterAntecedent patientId={id} />
        </Card>

        <Card className="sn-panneau">
          <h2 className="sn-h2">Traitements au long cours</h2>
          {traitements.length === 0 ? (
            <p className="sn-meta">Aucun traitement au long cours.</p>
          ) : (
            <ul className="sn-liste">
              {traitements.map((t) => (
                <li key={t.id} className="sn-traitement">
                  <Icon name="pill" size={20} />
                  <div>
                    <b>{t.libelle}</b>
                    <div className="sn-meta">{[t.posologie, t.depuis && `depuis ${formatDate(t.depuis)}`].filter(Boolean).join(" · ")}</div>
                    <OrigineDeLEntree origine={t.origine} />
                  </div>
                  <form action={arreterTraitement}>
                    <input type="hidden" name="patient_id" value={id} />
                    <input type="hidden" name="traitement" value={t.id} />
                    <Button type="submit" size="pro" variant="ghost" icon="x">
                      Arrêter
                    </Button>
                  </form>
                </li>
              ))}
            </ul>
          )}
          <AjouterTraitement patientId={id} catalogue={catalogue} />
        </Card>

        <Card className="sn-panneau">
          <h2 className="sn-h2">Groupe sanguin et allergies</h2>
          {bandeau.allergies.length > 0 && (
            <ul className="sn-puces">
              {bandeau.allergies.map((a) => (
                <li key={a.id}>
                  <b>{a.code_atc ? `${a.libelle} (${a.code_atc})` : a.libelle}</b>
                  <OrigineDeLEntree origine={a.origine} />
                </li>
              ))}
            </ul>
          )}
          <div className="sn-actions">
            <EnregistrerGroupeSanguin patientId={id} actuel={bandeau.groupe_sanguin} />
            <DeclarerAllergie patientId={id} catalogue={catalogue} />
          </div>
        </Card>
      </div>
    </div>
  );
}

/** L'entrée de l'espace patient : la synthèse avec une relation de soin, sinon le choix qui l'ouvre. */
export default async function EspaceDuPatient({ params, searchParams }: Parametres) {
  await connection();
  const session = await soignantConnecte();
  const [{ patientId }, recherche] = await Promise.all([params, searchParams]);
  const bandeau = await soin.bandeau(patientId);
  if (bandeau.statut !== 200 || !bandeau.corps) return <PatientIntrouvable session={session} statut={bandeau.statut} />;

  if (!bandeau.corps.relation_de_soin) {
    return (
      <EspacePatient session={session} bandeau={bandeau.corps}>
        <Messages recherche={recherche} />
        <Choix bandeau={bandeau.corps} />
      </EspacePatient>
    );
  }

  const [dossier, catalogue] = await Promise.all([soin.dossier(patientId), soin.catalogue()]);
  return (
    <EspacePatient session={session} bandeau={bandeau.corps} onglet="synthese">
      <Messages recherche={recherche} />
      <Synthese bandeau={bandeau.corps} dossier={dossier.corps} catalogue={catalogue.corps} />
    </EspacePatient>
  );
}
