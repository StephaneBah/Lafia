"use client";

import { Alert, Button, Icon, TextInput } from "@lafia/design";
import { enKo, PageRefusee, PAGES_MAX, preparerFichier, TYPES_ACCEPTES } from "@lafia/commun/televersement";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { TYPES_DE_DOCUMENT } from "../lib/types";

// Ajouter un document apporté par le patient, pendant la visite : les mêmes champs et la même
// préparation des pages qu'au guichet de numérisation (@lafia/commun/televersement, ADR 0008). Une
// photo, prise à l'appareil ou choisie, devient un JPEG sur fond blanc d'au plus 1600 px et 1 Mo ; un
// PDF part tel quel, s'il pèse au plus 3 Mo. Le navigateur envoie le Document droit au service soin,
// par la passerelle, avec la session du soignant : aucun serveur d'application ne relaie ses pages.

const DELAI_D_ENVOI_MS = 60_000;

type Page = { cle: string; blob: Blob; pdf: boolean; apercu: string | null };

let compteur = 0;
function nouvellePage(blob: Blob): Page {
  const pdf = blob.type === "application/pdf";
  compteur += 1;
  return { cle: `page-${compteur}`, blob, pdf, apercu: pdf ? null : URL.createObjectURL(blob) };
}

function liberer(page: Page) {
  if (page.apercu) URL.revokeObjectURL(page.apercu);
}

function motifDEchec(statut: number): string {
  if (statut === 413) return `Trop lourd : au plus ${PAGES_MAX} pages de 3 Mo chacune. Rien n’a été enregistré.`;
  if (statut === 422) return "Le service a refusé ce document : vérifiez le type, l’année et le format des pages.";
  if (statut === 403) return "Il faut une relation de soin avec ce patient pour ajouter un document.";
  if (statut === 401) return "Votre session a pris fin : reconnectez-vous, puis reprenez ce document.";
  return "Le document n’a pas été enregistré. Vos pages restent là : réessayez.";
}

export function AjouterUnDocument({ patientId }: { patientId: string }) {
  const routeur = useRouter();
  const [pages, setPages] = useState<Page[]>([]);
  const [remplacee, setRemplacee] = useState<number | null>(null);
  const [preparation, setPreparation] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const photo = useRef<HTMLInputElement>(null);
  const toutes = useRef<Page[]>([]);
  toutes.current = pages;
  const anneeCourante = new Date().getFullYear();

  useEffect(() => () => toutes.current.forEach(liberer), []);

  async function ajouter(liste: FileList | null) {
    const fichiers = Array.from(liste ?? []);
    if (!fichiers.length) return;
    setErreur(null);
    setPreparation(true);
    try {
      const preparees: Page[] = [];
      for (const fichier of fichiers) preparees.push(nouvellePage(await preparerFichier(fichier)));
      setPages((avant) => {
        if (remplacee !== null && preparees.length === 1) {
          liberer(avant[remplacee]);
          return avant.map((p, i) => (i === remplacee ? preparees[0] : p));
        }
        const suite = [...avant, ...preparees];
        suite.slice(PAGES_MAX).forEach(liberer);
        if (suite.length > PAGES_MAX) setErreur(`Un document compte ${PAGES_MAX} pages au plus : les suivantes n’ont pas été ajoutées.`);
        return suite.slice(0, PAGES_MAX);
      });
    } catch (refus) {
      setErreur(refus instanceof PageRefusee ? refus.message : "Une page n’a pas pu être préparée. Reprenez-la ou choisissez un autre fichier.");
    } finally {
      setRemplacee(null);
      setPreparation(false);
    }
  }

  function reprendre(indice: number) {
    setRemplacee(indice);
    photo.current?.click();
  }

  function retirer(indice: number) {
    setPages((avant) => {
      liberer(avant[indice]);
      return avant.filter((_, i) => i !== indice);
    });
  }

  async function poster(corps: FormData): Promise<Response | null> {
    try {
      return await fetch(`/api/soin/patients/${encodeURIComponent(patientId)}/documents`, {
        method: "POST",
        body: corps,
        credentials: "same-origin",
        signal: AbortSignal.timeout(DELAI_D_ENVOI_MS),
      });
    } catch {
      return null;
    }
  }

  async function enregistrer(evenement: FormEvent<HTMLFormElement>) {
    evenement.preventDefault();
    const donnees = new FormData(evenement.currentTarget);
    const annee = String(donnees.get("annee") ?? "").trim();
    setErreur(null);
    if (!donnees.get("type")) return setErreur("Choisissez le type du document.");
    if (!/^\d{4}$/.test(annee) || Number(annee) < 1900 || Number(annee) > anneeCourante) {
      return setErreur(`L’année s’écrit en quatre chiffres, de 1900 à ${anneeCourante}.`);
    }
    if (!pages.length) return setErreur("Ajoutez au moins une page : photographiez-la ou choisissez un fichier.");

    const corps = new FormData();
    corps.append("type", String(donnees.get("type")));
    corps.append("annee", annee);
    const etablissement = String(donnees.get("etablissement") ?? "").trim();
    if (etablissement) corps.append("etablissement", etablissement.slice(0, 200));
    corps.append("lisibilite", String(donnees.get("lisibilite") ?? "lisible"));
    pages.forEach((page, i) => corps.append("pages", page.blob, `page-${i + 1}.${page.pdf ? "pdf" : "jpg"}`));

    setEnvoi(true);
    let reponse = await poster(corps);
    if (reponse?.status === 401) {
      // Le jeton a expiré pendant la saisie : relire la page le renouvelle (proxy.ts), puis on renvoie.
      await fetch(window.location.href, { credentials: "same-origin", cache: "no-store" }).catch(() => undefined);
      reponse = await poster(corps);
    }
    if (reponse?.status === 201) {
      const { document_id } = (await reponse.json()) as { document_id: string };
      routeur.push(`/patients/${encodeURIComponent(patientId)}/documents?document=${encodeURIComponent(document_id)}&ok=document`);
      routeur.refresh();
      return;
    }
    setEnvoi(false);
    setErreur(motifDEchec(reponse?.status ?? 0));
  }

  return (
    <details className="sn-replie">
      <summary className="lf-btn lf-btn--secondary lf-btn--pro">
        <Icon name="plus" size={20} />
        <span className="lf-btn-label">Ajouter un document apporté par le patient</span>
      </summary>
      <div className="sn-replie-corps">
        <form onSubmit={enregistrer} className="lf-formulaire" noValidate>
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
            pattern="[0-9]{4}"
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

          <fieldset className="sn-fieldset">
            <legend className="lf-field-label">{`Pages, dans l’ordre (${PAGES_MAX} au plus) : ${pages.length}`}</legend>
            {pages.length > 0 && (
              <ol className="sn-pages">
                {pages.map((page, i) => (
                  <li key={page.cle} className="sn-page-apercu">
                    {page.apercu ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={page.apercu} alt={`Page ${i + 1}`} width={96} />
                    ) : (
                      <span>
                        <Icon name="copy" size={32} /> PDF
                      </span>
                    )}
                    <small>{`Page ${i + 1} · ${enKo(page.blob.size)}`}</small>
                    {!page.pdf && (
                      <Button size="pro" variant="ghost" icon="video-camera" onClick={() => reprendre(i)} aria-label={`Reprendre la page ${i + 1}`}>
                        Reprendre
                      </Button>
                    )}
                    <Button size="pro" variant="ghost" icon="x" onClick={() => retirer(i)} aria-label={`Retirer la page ${i + 1}`}>
                      Retirer
                    </Button>
                  </li>
                ))}
              </ol>
            )}
            <div className="sn-radios sn-radios--ligne">
              {/* La caméra de l'appareil, quand il en a une ; sinon, le choix d'une image. */}
              <label className="lf-btn lf-btn--secondary lf-btn--pro">
                <Icon name="video-camera" size={20} />
                <span className="lf-btn-label">Photographier une page</span>
                <input
                  ref={photo}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  hidden
                  disabled={preparation || envoi || (pages.length >= PAGES_MAX && remplacee === null)}
                  onChange={(e) => {
                    void ajouter(e.currentTarget.files);
                    e.currentTarget.value = "";
                  }}
                />
              </label>
              <label className="lf-btn lf-btn--secondary lf-btn--pro">
                <Icon name="plus" size={20} />
                <span className="lf-btn-label">Choisir des fichiers</span>
                <input
                  type="file"
                  accept={TYPES_ACCEPTES.join(",")}
                  multiple
                  hidden
                  disabled={preparation || envoi || pages.length >= PAGES_MAX}
                  onChange={(e) => {
                    setRemplacee(null);
                    void ajouter(e.currentTarget.files);
                    e.currentTarget.value = "";
                  }}
                />
              </label>
            </div>
          </fieldset>
          <Button type="submit" size="pro" icon="check" disabled={preparation || envoi}>
            {preparation ? "Préparation des pages…" : envoi ? "Enregistrement…" : "Enregistrer le document"}
          </Button>
        </form>
      </div>
    </details>
  );
}
