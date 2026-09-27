"use client";

// Étape 3 : un papier devient un Document. Son type, son année, l'établissement d'où il vient, sa
// lisibilité, puis ses pages, photographiées une à une ou choisies en fichiers, compressées ici avant
// l'envoi. L'envoi va droit au service numerisation, par la passerelle du même domaine : le cookie de
// session l'accompagne, et le NPI n'y figure pas, le dépôt sait de qui il s'agit.
import { Alert, Button, Icon, TextInput } from "@lafia/design";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";

import { compresser, enKo, PageRefusee, PAGES_MAX, preparerFichier, TYPES_ACCEPTES } from "../../../../compression";
import { adresseDuDepot, LISIBILITES, TYPES_DE_DOCUMENT } from "../../../../libelles";

type Page = { cle: string; blob: Blob; pdf: boolean; apercu: string | null };
type Champ = "type" | "annee" | "lisibilite" | "pages";
type Camera = "fermee" | "ouverture" | "ouverte";

const DELAI_D_ENVOI_MS = 60_000;

let compteur = 0;
function nouvellePage(blob: Blob): Page {
  const pdf = blob.type === "application/pdf";
  compteur += 1;
  return { cle: `page-${compteur}`, blob, pdf, apercu: pdf ? null : URL.createObjectURL(blob) };
}

function liberer(page: Page) {
  if (page.apercu) URL.revokeObjectURL(page.apercu);
}

/** Pourquoi la caméra ne s'ouvre pas, et quoi faire à la place. */
function refusDeLaCamera(erreur: unknown): string {
  const nom = erreur instanceof DOMException ? erreur.name : "";
  if (nom === "NotAllowedError") return "La caméra est refusée : autorisez-la dans le navigateur, ou choisissez des fichiers.";
  if (nom === "NotFoundError" || nom === "OverconstrainedError") return "Aucune caméra sur cet appareil : choisissez des fichiers.";
  if (nom === "NotReadableError") return "La caméra est occupée par une autre application : fermez-la, ou choisissez des fichiers.";
  return "La caméra ne s'ouvre pas : choisissez des fichiers.";
}

export function Numeriser({ depot, anneeCourante }: { depot: string; anneeCourante: number }) {
  const routeur = useRouter();
  const [pages, setPages] = useState<Page[]>([]);
  const [erreurs, setErreurs] = useState<Partial<Record<Champ, string>>>({});
  const [refusDePages, setRefusDePages] = useState<string | null>(null);
  const [preparation, setPreparation] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const [echec, setEchec] = useState<{ titre: string; texte: ReactNode; ton: "attention" | "danger" } | null>(null);

  const [camera, setCamera] = useState<Camera>("fermee");
  const [remplacee, setRemplacee] = useState<number | null>(null);
  const video = useRef<HTMLVideoElement>(null);
  const flux = useRef<MediaStream | null>(null);
  const fichiers = useRef<HTMLInputElement>(null);
  const pagesCourantes = useRef<Page[]>([]);
  pagesCourantes.current = pages;

  // En quittant l'écran : la caméra s'éteint, les aperçus sont rendus au navigateur.
  useEffect(
    () => () => {
      flux.current?.getTracks().forEach((piste) => piste.stop());
      pagesCourantes.current.forEach(liberer);
    },
    [],
  );

  useEffect(() => {
    if (camera !== "ouverte" || !video.current || !flux.current) return;
    video.current.srcObject = flux.current;
    video.current.play().catch(() => undefined);
  }, [camera]);

  /** Ajoute des pages en fin de document, ou remplace la page `indice` par la première. */
  function ajouter(nouvelles: Blob[], indice: number | null) {
    const actuelles = pagesCourantes.current;
    if (indice !== null && actuelles[indice]) {
      const suite = [...actuelles];
      liberer(suite[indice]);
      suite[indice] = nouvellePage(nouvelles[0]);
      pagesCourantes.current = suite;
      setPages(suite);
    } else {
      const place = Math.max(0, PAGES_MAX - actuelles.length);
      if (nouvelles.length > place) {
        setRefusDePages(`Un document compte ${PAGES_MAX} pages au plus : les pages en trop n'ont pas été ajoutées.`);
      }
      const suite = [...actuelles, ...nouvelles.slice(0, place).map(nouvellePage)];
      pagesCourantes.current = suite;
      setPages(suite);
    }
    setErreurs((e) => ({ ...e, pages: undefined }));
  }

  function retirer(indice: number) {
    const actuelles = pagesCourantes.current;
    if (actuelles[indice]) liberer(actuelles[indice]);
    const suite = actuelles.filter((_, i) => i !== indice);
    pagesCourantes.current = suite;
    setPages(suite);
  }

  async function ouvrirLaCamera(indice: number | null) {
    setRefusDePages(null);
    setRemplacee(indice);
    if (flux.current) {
      setCamera("ouverte");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setRefusDePages("Ce navigateur ne donne pas accès à la caméra : choisissez des fichiers.");
      return;
    }
    setCamera("ouverture");
    try {
      flux.current = await navigator.mediaDevices.getUserMedia({
        // La caméra arrière, celle qui regarde le papier.
        video: { facingMode: { ideal: "environment" }, width: { ideal: 2560 }, height: { ideal: 1920 } },
        audio: false,
      });
      setCamera("ouverte");
    } catch (erreur) {
      setCamera("fermee");
      setRefusDePages(refusDeLaCamera(erreur));
    }
  }

  function fermerLaCamera() {
    flux.current?.getTracks().forEach((piste) => piste.stop());
    flux.current = null;
    setCamera("fermee");
    setRemplacee(null);
  }

  async function photographier() {
    const image = video.current;
    if (!image || !image.videoWidth) return;
    setPreparation(true);
    try {
      ajouter([await compresser(image, image.videoWidth, image.videoHeight)], remplacee);
      if (remplacee !== null) fermerLaCamera();
    } catch (erreur) {
      setRefusDePages(erreur instanceof PageRefusee ? erreur.message : "La photo n'a pas pu être prise : réessayez.");
    } finally {
      setPreparation(false);
    }
  }

  async function choisirDesFichiers(liste: FileList | null) {
    if (!liste?.length) return;
    setRefusDePages(null);
    setPreparation(true);
    const pretes: Blob[] = [];
    const refus: string[] = [];
    for (const fichier of Array.from(liste)) {
      try {
        pretes.push(await preparerFichier(fichier));
      } catch (erreur) {
        refus.push(erreur instanceof PageRefusee ? erreur.message : `« ${fichier.name} » ne s'ouvre pas.`);
      }
    }
    if (pretes.length) ajouter(pretes, null);
    if (refus.length) setRefusDePages(refus.join(" "));
    setPreparation(false);
    if (fichiers.current) fichiers.current.value = "";
  }

  function valider(donnees: FormData): Partial<Record<Champ, string>> {
    const trouvees: Partial<Record<Champ, string>> = {};
    const annee = String(donnees.get("annee") ?? "").trim();
    if (!donnees.get("type")) trouvees.type = "Choisissez le type du document.";
    if (!/^\d{4}$/.test(annee) || Number(annee) < 1900 || Number(annee) > anneeCourante) {
      trouvees.annee = `L'année s'écrit en quatre chiffres, de 1900 à ${anneeCourante}.`;
    }
    if (!donnees.get("lisibilite")) trouvees.lisibilite = "Dites si le document se lit en entier.";
    if (!pages.length) trouvees.pages = "Ajoutez au moins une page : photographiez-la ou choisissez un fichier.";
    return trouvees;
  }

  async function poster(corps: FormData): Promise<Response | null> {
    try {
      return await fetch(`${adresseDuDepot(depot)}/documents`, {
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
    const formulaire = evenement.currentTarget;
    const donnees = new FormData(formulaire);
    const trouvees = valider(donnees);
    setErreurs(trouvees);
    setEchec(null);
    const premiere = (["type", "annee", "lisibilite", "pages"] as Champ[]).find((champ) => trouvees[champ]);
    if (premiere) {
      formulaire.querySelector<HTMLElement>(`[data-champ="${premiere}"]`)?.focus();
      return;
    }

    const corps = new FormData();
    corps.append("type", String(donnees.get("type")));
    corps.append("annee", String(donnees.get("annee")).trim());
    const etablissement = String(donnees.get("etablissement") ?? "").trim();
    if (etablissement) corps.append("etablissement", etablissement);
    corps.append("lisibilite", String(donnees.get("lisibilite")));
    pages.forEach((page, i) => corps.append("pages", page.blob, `page-${i + 1}.${page.pdf ? "pdf" : "jpg"}`));

    setEnvoi(true);
    let reponse = await poster(corps);
    if (reponse?.status === 401) {
      // Le jeton a expiré pendant la saisie : relire la page le renouvelle (proxy.ts), puis on renvoie.
      await fetch(window.location.href, { credentials: "same-origin", cache: "no-store" }).catch(() => undefined);
      reponse = await poster(corps);
    }
    if (reponse?.status === 201) {
      routeur.push(`/depots/${encodeURIComponent(depot)}`);
      return;
    }
    setEnvoi(false);
    setEchec(motifDEchec(reponse?.status ?? 0));
  }


  return (
    <form className="num-carte num-formulaire" onSubmit={enregistrer} noValidate>
      <fieldset className="num-choix" aria-describedby={erreurs.type ? "erreur-type" : undefined}>
        <legend className="num-legende">Type de document</legend>
        <div className="num-tuiles">
          {TYPES_DE_DOCUMENT.map((type, i) => (
            <label key={type.code} className="num-tuile">
              <input
                type="radio"
                name="type"
                value={type.code}
                data-champ={i === 0 ? "type" : undefined}
                onChange={() => setErreurs((e) => ({ ...e, type: undefined }))}
              />
              <Icon name={type.icone} size={32} />
              <span>{type.libelle}</span>
            </label>
          ))}
        </div>
        {erreurs.type && <Erreur id="erreur-type">{erreurs.type}</Erreur>}
      </fieldset>

      <div className="num-ligne">
        <TextInput
          label="Année du document"
          hint="Celle écrite sur le papier."
          name="annee"
          size="pro"
          icon="calendar-blank"
          inputMode="numeric"
          maxLength={4}
          autoComplete="off"
          placeholder={String(anneeCourante)}
          className="num-champ-annee"
          error={erreurs.annee}
          data-champ="annee"
          onChange={() => erreurs.annee && setErreurs((e) => ({ ...e, annee: undefined }))}
        />
        <TextInput
          label="Établissement d'origine (facultatif)"
          hint="Tel qu'il est écrit sur le document."
          name="etablissement"
          size="pro"
          icon="hospital"
          autoComplete="off"
          className="num-champ-etablissement"
        />
      </div>

      <fieldset className="num-choix" aria-describedby={erreurs.lisibilite ? "erreur-lisibilite" : undefined}>
        <legend className="num-legende">Lisibilité</legend>
        <div className="num-radios">
          {LISIBILITES.map((lisibilite, i) => (
            <label key={lisibilite.code} className="num-radio">
              <input
                type="radio"
                name="lisibilite"
                value={lisibilite.code}
                data-champ={i === 0 ? "lisibilite" : undefined}
                onChange={() => setErreurs((e) => ({ ...e, lisibilite: undefined }))}
              />
              <Icon name={lisibilite.icone} size={20} />
              <span>{lisibilite.libelle}</span>
            </label>
          ))}
        </div>
        {erreurs.lisibilite && <Erreur id="erreur-lisibilite">{erreurs.lisibilite}</Erreur>}
      </fieldset>

      <fieldset className="num-choix">
        <legend className="num-legende">{`Pages (${pages.length}/${PAGES_MAX})`}</legend>
        <p className="num-aide">Une photo par page, à plat, bien éclairée. Ou des fichiers : photos JPEG ou PNG, PDF de 3 Mo au plus.</p>

        {camera !== "fermee" ? (
          <div className="num-camera">
            <video ref={video} className="num-camera-video" playsInline muted aria-label="Ce que voit la caméra" />
            <div className="num-actions">
              <Button size="pro" icon="video-camera" onClick={photographier} loading={preparation || camera === "ouverture"} disabled={pages.length >= PAGES_MAX && remplacee === null}>
                {remplacee !== null ? `Reprendre la page ${remplacee + 1}` : `Photographier la page ${pages.length + 1}`}
              </Button>
              <Button size="pro" variant="secondary" icon="x" onClick={fermerLaCamera}>
                Fermer la caméra
              </Button>
            </div>
          </div>
        ) : (
          <div className="num-actions">
            <Button size="pro" icon="video-camera" onClick={() => ouvrirLaCamera(null)} data-champ="pages" disabled={pages.length >= PAGES_MAX}>
              Photographier les pages
            </Button>
            <Button size="pro" variant="secondary" icon="plus" onClick={() => fichiers.current?.click()} loading={preparation} disabled={pages.length >= PAGES_MAX}>
              Choisir des fichiers
            </Button>
            <input
              ref={fichiers}
              type="file"
              accept={TYPES_ACCEPTES.join(",")}
              multiple
              hidden
              onChange={(e) => choisirDesFichiers(e.target.files)}
            />
          </div>
        )}

        {refusDePages && <Alert tone="attention" title={refusDePages} />}
        {erreurs.pages && <Erreur id="erreur-pages">{erreurs.pages}</Erreur>}

        {pages.length > 0 && (
          <ol className="num-pages">
            {pages.map((page, i) => (
              <li key={page.cle} className="num-page">
                {page.apercu ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img className="num-vignette" src={page.apercu} alt={`Page ${i + 1}`} />
                ) : (
                  <span className="num-vignette num-vignette--pdf">
                    <Icon name="copy" size={28} />
                    <span>PDF</span>
                  </span>
                )}
                <span className="num-page-legende">
                  <b>{`Page ${i + 1}`}</b>
                  <span className="num-meta">{enKo(page.blob.size)}</span>
                </span>
                <span className="num-page-actions">
                  <Button size="pro" variant="ghost" icon="video-camera" onClick={() => ouvrirLaCamera(i)} aria-label={`Reprendre la page ${i + 1}`}>
                    Reprendre
                  </Button>
                  <Button size="pro" variant="ghost" icon="x" onClick={() => retirer(i)} aria-label={`Retirer la page ${i + 1}`}>
                    Retirer
                  </Button>
                </span>
              </li>
            ))}
          </ol>
        )}
      </fieldset>

      {echec && (
        <Alert tone={echec.ton} title={echec.titre}>
          {echec.texte}
        </Alert>
      )}

      <div className="num-actions num-actions--fin">
        <Button type="submit" size="pro" icon="check" loading={envoi} disabled={preparation}>
          Enregistrer le document
        </Button>
        <Button href={`/depots/${encodeURIComponent(depot)}`} size="pro" variant="ghost" icon="arrow-left">
          Retour au dépôt
        </Button>
      </div>
    </form>
  );
}

function Erreur({ id, children }: { id: string; children: ReactNode }) {
  return (
    <p className="num-erreur" id={id} role="alert">
      <Icon name="warning-octagon" size={20} />
      <span>{children}</span>
    </p>
  );
}

/** Ce que l'agent lit quand le service n'enregistre pas le Document ; ses pages restent à l'écran. */
function motifDEchec(statut: number): { titre: string; texte: ReactNode; ton: "attention" | "danger" } {
  if (statut === 413) {
    return {
      ton: "attention",
      titre: "Document trop lourd : rien n'a été enregistré.",
      texte: `Un document compte ${PAGES_MAX} pages au plus, de 3 Mo chacune. Retirez des pages, ou reprenez-les en photo.`,
    };
  }
  if (statut === 422) {
    return {
      ton: "attention",
      titre: "Le service refuse ce document : rien n'a été enregistré.",
      texte: "Vérifiez le type, l'année et le format des pages : photos JPEG ou PNG, ou PDF.",
    };
  }
  if (statut === 401) {
    return {
      ton: "attention",
      titre: "Votre session a pris fin : rien n'a été enregistré.",
      texte: (
        <>
          <a href="/connexion">Reconnectez-vous</a>, puis reprenez ce document depuis le dépôt.
        </>
      ),
    };
  }
  if ([403, 404, 409, 410].includes(statut)) {
    return {
      ton: "attention",
      titre: "Ce dépôt est clos : il ne se complète plus.",
      texte: (
        <>
          Pour d'autres papiers, <a href="/">ouvrez un nouveau dépôt</a>.
        </>
      ),
    };
  }
  return {
    ton: "danger",
    titre: "Le service numérisation ne répond pas : rien n'a été enregistré.",
    texte: "Vos pages restent là. Réessayez dans un instant.",
  };
}
