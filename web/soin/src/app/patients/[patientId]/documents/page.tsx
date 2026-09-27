import { Alert, Card } from "@lafia/design";
import { redirect } from "next/navigation";
import { connection } from "next/server";

import { AjouterUnDocument } from "../../../../composants/AjouterUnDocument";
import { soignantConnecte } from "../../../../composants/Cadre";
import { IconeDuType, ListeDesDocuments, NonVerifie, Visionneuse } from "../../../../composants/Documents";
import { EspacePatient, PatientIntrouvable } from "../../../../composants/EspacePatient";
import { AjouterAntecedent, DeclarerAllergie } from "../../../../composants/FormulairesDuDossier";
import { adresseDuPatient } from "../../../../lib/adresses";
import { soin } from "../../../../lib/soin";

type Parametres = { params: Promise<{ patientId: string }>; searchParams: Promise<Record<string, string | undefined>> };

const MESSAGES: Record<string, { ton: "succes" | "danger"; titre: string }> = {
  "ok=document": { ton: "succes", titre: "Document ajouté au dossier, marqué numérisé, non vérifié." },
  "ok=antecedent": { ton: "succes", titre: "Antécédent reporté depuis ce document." },
  "ok=allergie": { ton: "succes", titre: "Allergie reportée depuis ce document : la pharmacie arrêtera toute ligne de cette classe." },
  "erreur=antecedent": { ton: "danger", titre: "L’antécédent n’a pas été reporté. Donnez au moins son libellé." },
  "erreur=lien": { ton: "danger", titre: "Un antécédent familial demande le lien de parenté." },
  "erreur=allergie": { ton: "danger", titre: "L’allergie n’a pas été reportée. Choisissez une classe du catalogue." },
};

/**
 * L'onglet Documents : les papiers du patient, numérisés et non vérifiés, avec leurs pages ; ajouter
 * un document qu'il a apporté ; reporter depuis un document un antécédent ou une allergie.
 */
export default async function DocumentsDuPatient({ params, searchParams }: Parametres) {
  await connection();
  const session = await soignantConnecte();
  const [{ patientId }, recherche] = await Promise.all([params, searchParams]);
  const bandeau = await soin.bandeau(patientId);
  if (bandeau.statut !== 200 || !bandeau.corps) return <PatientIntrouvable session={session} statut={bandeau.statut} />;
  if (!bandeau.corps.relation_de_soin) redirect(adresseDuPatient(patientId));

  const [documents, catalogue] = await Promise.all([soin.documents(patientId), soin.catalogue()]);
  if (documents.statut === 403) redirect(adresseDuPatient(patientId));
  const liste = documents.corps ?? [];
  const choisi = liste.find((d) => d.id === recherche.document);
  const messages = Object.entries(recherche)
    .map(([cle, valeur]) => MESSAGES[`${cle}=${valeur}`])
    .filter(Boolean);

  return (
    <EspacePatient session={session} bandeau={bandeau.corps} onglet="documents">
      {messages.map((m) => (
        <Alert key={m.titre} tone={m.ton} title={m.titre} />
      ))}
      <div className="sn-synthese">
        <div className="sn-colonne">
          <Card className="sn-panneau">
            <h2 className="sn-h2">Documents du patient</h2>
            <p className="sn-meta">
              Des papiers numérisés : personne ne les a vérifiés. Lisez-les avant d’en reporter une entrée.
            </p>
            {!documents.corps ? (
              <Alert tone="danger" title="Le service soin ne répond pas. Réessayez dans un instant." />
            ) : (
              <ListeDesDocuments patientId={patientId} documents={liste} choisi={choisi?.id} />
            )}
            <AjouterUnDocument patientId={patientId} />
          </Card>
        </div>

        <div className="sn-colonne">
          {choisi ? (
            <Card className="sn-panneau">
              <h2 className="sn-h2 sn-titre-document">
                <IconeDuType type={choisi.type} />
                {`${choisi.libelle_du_type}${choisi.annee ? ` · ${choisi.annee}` : ""}`}
              </h2>
              <p className="sn-meta">
                {[choisi.etablissement, choisi.lisibilite === "partiel" ? "Partiellement lisible" : "Lisible"]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              <NonVerifie />
              <Visionneuse document={choisi} page={Number(recherche.page ?? "1") || 1} />
              <section className="sn-sous-partie">
                <h3 className="sn-h3">Reporter depuis ce document</h3>
                <p className="sn-meta">L’entrée reportée portera la mention « Reporté depuis un document », liée à ce document.</p>
                <div className="sn-actions">
                  <AjouterAntecedent patientId={patientId} documentId={choisi.id} />
                  <DeclarerAllergie patientId={patientId} catalogue={catalogue.corps} documentId={choisi.id} />
                </div>
              </section>
            </Card>
          ) : (
            liste.length > 0 && <div className="sn-vide">Choisissez un document pour en voir les pages.</div>
          )}
        </div>
      </div>
    </EspacePatient>
  );
}
