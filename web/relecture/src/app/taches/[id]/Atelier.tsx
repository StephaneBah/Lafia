"use client";

// La Relecture : les pages à gauche, la Transcription à droite, volet par volet. Le relecteur corrige,
// remet en ordre, coupe, fusionne, ajoute des photos de page ; chaque changement s'enregistre seul,
// quelques instants après. Puis la double confirmation : chaque volet coché contre ses pages, et le tout
// confirmé avec le résumé des changements. Un autre agent de relecture le contrôlera.
import { LIBELLES_DES_VOLETS, lireTranscription } from "@lafia/commun/transcription";
import { Alert, Button, Icon } from "@lafia/design";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

import {
  avecMeta,
  changements,
  couper,
  deplacer,
  depuisLeBrut,
  depuisMarkdown,
  empreinte,
  erreursDuVolet,
  fusionner,
  imageDePage,
  inserer,
  resumeSuggere,
  texteDuVolet,
  versMarkdown,
  voletVide,
  type Brouillon,
  type VoletEdite,
} from "../../../edition";
import { pluriel, RAISONS_D_INUTILISABLE } from "../../../libelles";
import type { DocumentARelire, Modele, NoteDeControle } from "../../../types";
import {
  confirmerLaTranscription,
  declarerLeDocumentInutilisable,
  enregistrerLeBrouillon,
  type IssueDeConfirmation,
} from "../../actions";
import { CarteDeVolet, type GestesDuVolet } from "./CarteDeVolet";
import { Dialogue } from "./Dialogue";
import { Feuilles, type Citation, type Zone } from "./Feuilles";
import { Contexte } from "./Contexte";
import { adresseDeLaSuite, avecSession, motDuRefus } from "./session";

type EtatDeSauvegarde = "enregistre" | "modifie" | "en-cours" | "erreur" | "session" | "trop-long" | "conflit";
type Sauvegarde = { etat: EtatDeSauvegarde; a?: Date };

const ATTENTE_MS = 1500;
const NOUVEL_ESSAI_MS = 10000;

function heure(date: Date): string {
  return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

function EtatDeLaSauvegarde({ sauvegarde, onReessayer }: { sauvegarde: Sauvegarde; onReessayer: () => void }) {
  const { etat, a } = sauvegarde;
  const contenu: Record<EtatDeSauvegarde, { icone: "check" | "clock" | "warning" | "warning-octagon"; texte: string }> = {
    enregistre: { icone: "check", texte: a ? `Enregistré à ${heure(a)}` : "Brouillon à jour" },
    modifie: { icone: "clock", texte: "Modifications en attente…" },
    "en-cours": { icone: "clock", texte: "Enregistrement…" },
    erreur: { icone: "warning", texte: "Pas encore enregistré : le service ne répond pas. Nouvel essai sous peu." },
    session: { icone: "warning", texte: "Pas enregistré : votre session a pris fin. Reconnectez-vous dans un autre onglet." },
    "trop-long": { icone: "warning-octagon", texte: "Pas enregistré : la Transcription dépasse 200 Ko. Retirez du texte." },
    conflit: { icone: "warning-octagon", texte: "Pas enregistré : la tâche a changé ailleurs." },
  };
  const { icone, texte } = contenu[etat];
  return (
    <p className={`rel-sauvegarde rel-sauvegarde--${etat}`} role="status">
      <Icon name={icone} size={18} />
      <span>{texte}</span>
      {(etat === "erreur" || etat === "session") && (
        <button type="button" className="rel-lien-bouton" onClick={onReessayer}>
          Réessayer maintenant
        </button>
      )}
    </p>
  );
}

function ListeDesChangements({ depart, volets }: { depart: string[]; volets: VoletEdite[] }) {
  const c = changements(depart, volets);
  const lignes: [number, string, string][] = [
    [c.modifies, "volet corrigé", "volets corrigés"],
    [c.ajoutes, "volet ajouté", "volets ajoutés"],
    [c.supprimes, "volet supprimé", "volets supprimés"],
    [c.deplaces, "volet remis en ordre", "volets remis en ordre"],
    [c.photos, "photo de page ajoutée", "photos de page ajoutées"],
  ];
  const faits = lignes.filter(([n]) => n > 0);
  if (!faits.length) return <p className="rel-meta">Aucun changement depuis l'ouverture : vous confirmez la lecture telle quelle.</p>;
  return (
    <ul className="rel-changements">
      {faits.map(([n, un, plusieurs]) => (
        <li key={un}>
          <span className="rel-chiffres">{n}</span> {n > 1 ? plusieurs : un}
        </li>
      ))}
    </ul>
  );
}

export function Atelier({
  tache,
  document: doc,
  description,
  markdown: markdownInitial,
  version: versionInitiale,
  modele,
  texte,
  notes,
  renvoyee,
}: {
  tache: string;
  document: DocumentARelire;
  description: string;
  markdown: string;
  version: string;
  modele: Modele | null;
  texte: string | null;
  notes: NoteDeControle[];
  renvoyee: boolean;
}) {
  const router = useRouter();
  const pages = Math.max(1, doc.pages);
  const idResume = useId();
  const cleDesCoches = `relecture:${tache}:coches`;

  const [ouverture] = useState(() => {
    const brouillon = depuisMarkdown(markdownInitial, pages);
    return { brouillon, depart: brouillon.volets.map(texteDuVolet), markdown: versMarkdown(brouillon) };
  });
  const [brouillon, setBrouillon] = useState<Brouillon>(ouverture.brouillon);
  const [mode, setMode] = useState<"volets" | "brut">("volets");
  const [brut, setBrut] = useState("");
  const [enEdition, setEnEdition] = useState<string | null>(null);
  const [annulable, setAnnulable] = useState<{ message: string; avant: VoletEdite[] } | null>(null);
  const [pageEnVue, setPageEnVue] = useState(1);
  const [cible, setCible] = useState<{ page: number; n: number } | null>(null);
  const [zone, setZone] = useState<{ cle: string; page: number; legende: string } | null>(null);
  const [dialogue, setDialogue] = useState<null | "confirmation" | "inutilisable">(null);
  const [menu, setMenu] = useState(false);
  const [sauvegarde, setSauvegarde] = useState<Sauvegarde>({ etat: "enregistre" });
  const [annonce, setAnnonce] = useState("");
  const [resume, setResume] = useState("");
  const [raison, setRaison] = useState<"non-medical" | "doublon" | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const [refus, setRefus] = useState<(IssueDeConfirmation & { ok: false }) | { ok: false; statut: number; message: string } | null>(null);

  const curseurs = useRef<Record<string, number>>({});
  const version = useRef(versionInitiale);
  const enregistre = useRef(ouverture.markdown);
  const conflit = useRef(false);
  const file = useRef<Promise<boolean>>(Promise.resolve(true));
  const cochesRestaurees = useRef(false);
  const aFocaliser = useRef<string[] | null>(null);

  /** Après le prochain rendu, le focus va au premier de ces éléments qui existe et n'est pas désactivé. */
  function focaliser(...ids: string[]) {
    aFocaliser.current = ids;
  }
  useEffect(() => {
    if (!aFocaliser.current) return;
    const cible = aFocaliser.current
      .map((id) => document.getElementById(id))
      .find((el): el is HTMLElement => Boolean(el) && !(el as HTMLButtonElement).disabled);
    aFocaliser.current = null;
    cible?.focus();
  });

  const markdown = useMemo(() => (mode === "brut" ? brut : versMarkdown(brouillon)), [mode, brut, brouillon]);
  const courant = useRef(markdown);
  courant.current = markdown;

  const volets = brouillon.volets;
  const lue = useMemo(() => lireTranscription(markdown, pages), [markdown, pages]);
  const erreurs = useMemo(
    () => [...lue.erreurs, ...(lue.volets.length ? [] : ["aucun volet : une Transcription en compte au moins un"])],
    [lue],
  );
  const erreursParVolet = useMemo(() => volets.map((v) => erreursDuVolet(v, pages)), [volets, pages]);
  const citations = useMemo(() => {
    const parPage: Record<number, Citation[]> = {};
    volets.forEach((v, i) => {
      for (const p of v.pages) (parPage[p] ??= []).push({ cle: v.cle, libelle: `${i + 1} · ${LIBELLES_DES_VOLETS[v.type]}` });
    });
    return parPage;
  }, [volets]);

  // ---- L'enregistrement, seul, quelques instants après chaque changement ----

  const enregistrerMaintenant = useCallback((): Promise<boolean> => {
    file.current = file.current
      .then(async () => {
        const md = courant.current;
        if (md === enregistre.current) return true;
        if (conflit.current) return false;
        setSauvegarde((s) => ({ ...s, etat: "en-cours" }));
        const issue = await avecSession(() => enregistrerLeBrouillon(tache, md, version.current));
        if (issue.ok) {
          version.current = issue.version;
          enregistre.current = md;
          setSauvegarde({ etat: courant.current === md ? "enregistre" : "modifie", a: new Date() });
          return true;
        }
        if (issue.statut === 409) conflit.current = true;
        const etat: EtatDeSauvegarde =
          issue.statut === 409 ? "conflit" : issue.statut === 422 ? "trop-long" : issue.statut === 401 ? "session" : "erreur";
        setSauvegarde((s) => ({ ...s, etat }));
        return false;
      })
      .catch(() => {
        setSauvegarde((s) => ({ ...s, etat: "erreur" }));
        return false;
      });
    return file.current;
  }, [tache]);

  useEffect(() => {
    if (conflit.current || markdown === enregistre.current) return;
    setSauvegarde((s) => (s.etat === "en-cours" ? s : { ...s, etat: s.etat === "trop-long" || s.etat === "session" ? s.etat : "modifie" }));
    const minuterie = setTimeout(() => void enregistrerMaintenant(), ATTENTE_MS);
    return () => clearTimeout(minuterie);
  }, [markdown, enregistrerMaintenant]);

  useEffect(() => {
    if (sauvegarde.etat !== "erreur") return;
    const minuterie = setTimeout(() => void enregistrerMaintenant(), NOUVEL_ESSAI_MS);
    return () => clearTimeout(minuterie);
  }, [sauvegarde.etat, enregistrerMaintenant]);

  // Quitter la page avant l'enregistrement : le navigateur prévient.
  useEffect(() => {
    function avantDePartir(e: BeforeUnloadEvent) {
      if (courant.current !== enregistre.current) e.preventDefault();
    }
    window.addEventListener("beforeunload", avantDePartir);
    return () => window.removeEventListener("beforeunload", avantDePartir);
  }, []);

  // Les coches ne partent qu'à la confirmation : elles survivent au rechargement, dans cet onglet,
  // tant que le volet n'a pas changé. Seules des empreintes sont gardées, jamais le texte.
  useEffect(() => {
    try {
      const gardees = new Set(JSON.parse(sessionStorage.getItem(cleDesCoches) ?? "[]") as string[]);
      if (gardees.size) {
        setBrouillon((b) => ({ ...b, volets: b.volets.map((v) => (gardees.has(empreinte(v)) ? { ...v, verifie: true } : v)) }));
      }
    } catch {
      // Stockage indisponible : les coches repartent de zéro.
    }
    cochesRestaurees.current = true;
  }, [cleDesCoches]);

  useEffect(() => {
    if (!cochesRestaurees.current) return;
    try {
      sessionStorage.setItem(cleDesCoches, JSON.stringify(volets.filter((v) => v.verifie).map(empreinte)));
    } catch {
      // Rien à faire : la coche reste à l'écran.
    }
  }, [volets, cleDesCoches]);

  // ---- Les gestes sur les volets ----

  function modifier(f: (volets: VoletEdite[]) => VoletEdite[], annulation?: string) {
    setAnnulable(annulation ? { message: annulation, avant: volets } : null);
    setBrouillon((b) => ({ ...b, volets: f(b.volets) }));
    if (annulation) focaliser("annuler-geste");
  }

  function changerVolet(cle: string, f: (v: VoletEdite) => VoletEdite) {
    modifier((vs) => vs.map((v) => (v.cle === cle ? f(v) : v)));
  }

  function annuler() {
    if (!annulable) return;
    setBrouillon((b) => ({ ...b, volets: annulable.avant }));
    setAnnonce(`Annulé : ${annulable.message.toLowerCase()}`);
    setAnnulable(null);
  }

  function voirPage(page: number) {
    setCible((c) => ({ page, n: (c?.n ?? 0) + 1 }));
    setAnnonce(`Page ${page} affichée à gauche.`);
  }

  const voirVolet = useCallback((cle: string) => {
    const carte = document.getElementById(`volet-${cle}`);
    carte?.scrollIntoView({ block: "start", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    carte?.focus({ preventScroll: true });
  }, []);

  function ajouterVolet(apres?: number) {
    const neuf = voletVide([pageEnVue]);
    modifier((vs) => (apres === undefined ? [...vs, neuf] : [...vs.slice(0, apres + 1), neuf, ...vs.slice(apres + 1)]));
    setEnEdition(neuf.cle);
    setAnnonce(`Volet ajouté, sur la page ${pageEnVue}.`);
    // Le formulaire du volet neuf prend le focus lui-même, et le navigateur le fait voir.
  }

  function insererPhoto(cle: string, page: number, legende: string, z?: Zone) {
    changerVolet(cle, (v) => {
      const position = Math.min(curseurs.current[cle] ?? v.corps.length, v.corps.length);
      const image = imageDePage(page, legende, z);
      curseurs.current[cle] = position + image.length + 2;
      return { ...v, corps: inserer(v.corps, position, image) };
    });
    setAnnonce(z ? `Zone de la page ${page} insérée dans le volet.` : `Page ${page} insérée dans le volet.`);
  }

  function gestesDe(v: VoletEdite, i: number): GestesDuVolet {
    const nom = `Volet ${i + 1}`;
    return {
      onMeta: (meta) => changerVolet(v.cle, (x) => avecMeta(x, meta)),
      onCorps: (corps) => changerVolet(v.cle, (x) => ({ ...x, corps })),
      onCurseur: (position) => {
        curseurs.current[v.cle] = position;
      },
      onEditer: (ouvert) => {
        setEnEdition(ouvert ? v.cle : null);
        if (!ouvert) focaliser(`editer-${v.cle}`);
      },
      onMonter: () => {
        modifier((vs) => deplacer(vs, i, i - 1));
        setAnnonce(`${nom} monté : il est maintenant le volet ${i}.`);
        focaliser(`monter-${v.cle}`, `descendre-${v.cle}`);
      },
      onDescendre: () => {
        modifier((vs) => deplacer(vs, i, i + 1));
        setAnnonce(`${nom} descendu : il est maintenant le volet ${i + 2}.`);
        focaliser(`descendre-${v.cle}`, `monter-${v.cle}`);
      },
      onCouper: (position) => {
        modifier((vs) => couper(vs, i, position), `${nom} coupé en deux`);
        setAnnonce(`${nom} coupé : la suite est le volet ${i + 2}, à revérifier.`);
      },
      onFusionner: () => {
        if (enEdition && volets[i + 1]?.cle === enEdition) setEnEdition(v.cle);
        modifier((vs) => fusionner(vs, i), `${nom} fusionné avec le suivant`);
      },
      onSupprimer: () => {
        if (enEdition === v.cle) setEnEdition(null);
        modifier((vs) => vs.filter((x) => x.cle !== v.cle), `${nom} supprimé`);
      },
      onVerifier: (verifie) => {
        // Cocher ne change pas le texte : pas d'annulation perdue, pas d'enregistrement.
        setBrouillon((b) => ({ ...b, volets: b.volets.map((x) => (x.cle === v.cle ? { ...x, verifie } : x)) }));
      },
      onVoirPage: voirPage,
      onPhotoEntiere: (page, legende) => insererPhoto(v.cle, page, legende),
      onPhotoZone: (page, legende) => {
        setZone({ cle: v.cle, page, legende });
        setAnnonce(`Tracez la zone sur la page ${page}, à gauche.`);
      },
    };
  }

  function changerDeMode(suivant: "volets" | "brut") {
    if (suivant === mode) return;
    if (suivant === "brut") {
      setBrut(versMarkdown(brouillon));
      setEnEdition(null);
      setZone(null);
    } else {
      setBrouillon(depuisLeBrut(brut, pages, volets));
    }
    setAnnulable(null);
    setMode(suivant);
  }

  // ---- La double confirmation ----

  const verifies = volets.filter((v) => v.verifie).length;
  const total = volets.length;
  const raisonDAttendre =
    mode === "brut"
      ? "Revenez à la vue par volets pour cocher chaque volet, puis confirmer."
      : sauvegarde.etat === "conflit"
        ? "La tâche a changé ailleurs : rechargez-la avant de confirmer."
        : total === 0
          ? "Une Transcription compte au moins un volet : ajoutez-en un."
          : erreurs.length
            ? `${pluriel(erreurs.length, "erreur de format", "erreurs de format")} à reprendre (voir en haut de la Transcription).`
            : verifies < total
              ? `Encore ${pluriel(total - verifies, "volet")} à vérifier contre les pages.`
              : null;

  function prochainAVerifier() {
    const v = volets.find((x) => !x.verifie);
    if (v) voirVolet(v.cle);
  }

  function ouvrirLaConfirmation() {
    setResume(resumeSuggere(changements(ouverture.depart, volets)));
    setRefus(null);
    setDialogue("confirmation");
  }

  async function confirmerMaintenant() {
    if (!resume.trim()) {
      setRefus({ ok: false, statut: 422, message: "Écrivez en une phrase ce que vous avez changé." });
      return;
    }
    setEnvoi(true);
    setRefus(null);
    const enregistreOk = await enregistrerMaintenant();
    if (!enregistreOk) {
      setEnvoi(false);
      setRefus({ ok: false, statut: 0, message: "Le brouillon n'a pas pu être enregistré : rien n'est confirmé. Réessayez dans un instant." });
      return;
    }
    const indices = volets.flatMap((v, i) => (v.verifie ? [i] : []));
    let issue: IssueDeConfirmation;
    try {
      issue = await avecSession(() => confirmerLaTranscription(tache, indices, resume));
    } catch {
      issue = { ok: false, statut: 0 };
    }
    if (issue.ok) {
      try {
        sessionStorage.removeItem(cleDesCoches);
      } catch {
        // Sans importance.
      }
      router.push(adresseDeLaSuite(issue.suivante, "confirmee"));
      return;
    }
    setEnvoi(false);
    setRefus(issue);
  }

  async function clore() {
    if (!raison) return;
    setEnvoi(true);
    setRefus(null);
    let issue;
    try {
      issue = await avecSession(() => declarerLeDocumentInutilisable(tache, raison));
    } catch {
      issue = { ok: false as const, statut: 0 };
    }
    if (issue.ok) {
      enregistre.current = courant.current;
      router.push(adresseDeLaSuite(issue.suivante, "close"));
      return;
    }
    setEnvoi(false);
    setRefus({ ok: false, statut: issue.statut, message: motDuRefus(issue.statut) });
  }

  // ---- L'écran ----

  const zoneDemandee = useMemo(() => (zone ? { page: zone.page } : null), [zone]);
  const pourcent = total ? Math.round((verifies / total) * 100) : 0;

  return (
    <div className="rel-atelier">
      <Feuilles
        tache={tache}
        pages={pages}
        formats={doc.formats}
        description={description}
        cible={cible}
        citations={citations}
        onPageEnVue={setPageEnVue}
        onVoirVolet={voirVolet}
        demandeDeZone={zoneDemandee}
        onZone={(page, z) => {
          if (!zone) return;
          insererPhoto(zone.cle, page, zone.legende, z);
          const cle = zone.cle;
          setZone(null);
          focaliser(`volet-${cle}`);
        }}
        onAnnulerZone={() => {
          const cle = zone?.cle;
          setZone(null);
          if (cle) focaliser(`volet-${cle}`);
        }}
      />

      <section className="rel-panneau" aria-labelledby="titre-transcription">
        <Contexte modele={modele} notes={notes} renvoyee={renvoyee} texte={texte} consigne="relecture" />

        {sauvegarde.etat === "conflit" && (
          <Alert
            tone="danger"
            title="Cette tâche a été enregistrée ailleurs depuis que vous l'avez ouverte."
            actions={
              <>
                <Button size="pro" icon="arrow-left" onClick={() => window.location.reload()}>
                  Recharger la version enregistrée
                </Button>
                <Button size="pro" variant="secondary" icon="copy" onClick={() => void navigator.clipboard?.writeText(courant.current)}>
                  Copier mon texte
                </Button>
              </>
            }
          >
            Un autre onglet, ou un autre poste, a enregistré ce brouillon ; ou la tâche n'est plus à relire. Vos derniers
            changements ne sont pas enregistrés : copiez votre texte avant de recharger si vous voulez le reprendre.
          </Alert>
        )}

        <div className="rel-panneau-tete">
          <h2 className="lf-app-sous-titre-fort" id="titre-transcription">
            Transcription
          </h2>
          <EtatDeLaSauvegarde sauvegarde={sauvegarde} onReessayer={() => void enregistrerMaintenant()} />
          <div className="rel-panneau-outils">
            <div className="rel-bascule" role="group" aria-label="Vue de la Transcription">
              <button type="button" aria-pressed={mode === "volets"} onClick={() => changerDeMode("volets")}>
                Par volets
              </button>
              <button type="button" aria-pressed={mode === "brut"} onClick={() => changerDeMode("brut")}>
                Markdown brut
              </button>
            </div>
            <div className="rel-menu">
              <button
                type="button"
                className="lf-btn lf-btn--ghost lf-btn--pro"
                aria-expanded={menu}
                aria-controls="menu-tache"
                onClick={() => setMenu((m) => !m)}
                onKeyDown={(e) => e.key === "Escape" && setMenu(false)}
              >
                <Icon name="list" size={20} />
                <span className="lf-btn-label">Autres actions</span>
              </button>
              {menu && (
                <ul className="rel-menu-liste" id="menu-tache" onKeyDown={(e) => e.key === "Escape" && setMenu(false)}>
                  <li>
                    <button
                      type="button"
                      autoFocus
                      onClick={() => {
                        setMenu(false);
                        setRaison(null);
                        setRefus(null);
                        setDialogue("inutilisable");
                      }}
                    >
                      <Icon name="warning" size={18} />
                      <span>Document inutilisable…</span>
                    </button>
                  </li>
                </ul>
              )}
            </div>
          </div>
        </div>

        {erreurs.length > 0 && (
          <div className="rel-erreurs" role="region" aria-label="Erreurs de format">
            <p className="rel-erreurs-titre">
              <Icon name="warning-octagon" size={20} />
              <span>{`${pluriel(erreurs.length, "point", "points")} hors du format de l'ADR 0010 : à reprendre avant de confirmer.`}</span>
            </p>
            <ul>
              {erreurs.map((e, i) => (
                <li key={`${i}-${e}`}>{e}</li>
              ))}
            </ul>
          </div>
        )}

        {annulable && (
          <div className="rel-annulation" role="status">
            <Icon name="info" size={20} />
            <span>{`${annulable.message}.`}</span>
            <button id="annuler-geste" type="button" className="lf-btn lf-btn--secondary lf-btn--pro" onClick={annuler}>
              <span className="lf-btn-label">Annuler</span>
            </button>
            <button type="button" className="rel-dialogue-fermer" aria-label="Fermer ce message" onClick={() => setAnnulable(null)}>
              <Icon name="x" size={18} />
            </button>
          </div>
        )}

        {mode === "brut" ? (
          <div className="rel-brut">
            <label className="rel-champ-libelle" htmlFor="markdown-brut">
              Le Markdown de la Transcription (ADR 0010)
            </label>
            <p className="rel-meta" id="markdown-brut-aide">
              Un volet commence par « ## type · date ou ? · établissement ou ? · p. pages ». Les erreurs s'affichent au-dessus
              pendant que vous écrivez. Revenez « Par volets » pour cocher et confirmer.
            </p>
            <textarea
              id="markdown-brut"
              className="lf-input rel-corps rel-corps--brut"
              value={brut}
              spellCheck={false}
              aria-describedby="markdown-brut-aide"
              onChange={(e) => setBrut(e.target.value)}
            />
          </div>
        ) : (
          <>
            {total === 0 ? (
              <p className="rel-vide-volets">Aucun volet. Ajoutez-en un pour chaque visite, résultat, ordonnance ou page de vaccination.</p>
            ) : (
              <ol className="rel-volets" aria-label="Les volets de la Transcription">
                {volets.map((v, i) => (
                  <CarteDeVolet
                    key={v.cle}
                    tache={tache}
                    volet={v}
                    rang={i}
                    total={total}
                    pages={pages}
                    enEdition={enEdition === v.cle}
                    pageEnVue={pageEnVue}
                    erreurs={erreursParVolet[i]}
                    gestes={gestesDe(v, i)}
                  />
                ))}
              </ol>
            )}
            <div className="rel-actions">
              <Button size="pro" variant="secondary" icon="plus" onClick={() => ajouterVolet()}>
                Ajouter un volet
              </Button>
              <span className="rel-meta">{`Il citera la page en vue (page ${pageEnVue}) ; vous pourrez la changer.`}</span>
            </div>
          </>
        )}

        <div className="rel-confirmer">
          <div className="rel-confirmer-compte">
            <p className="rel-confirmer-chiffres">
              <span className="rel-chiffres">{`${verifies} / ${total}`}</span>
              <span>{` ${total > 1 ? "volets vérifiés" : "volet vérifié"}`}</span>
            </p>
            <div
              className="rel-barre"
              role="progressbar"
              aria-label="Volets vérifiés contre les pages"
              aria-valuemin={0}
              aria-valuemax={total}
              aria-valuenow={verifies}
              aria-valuetext={`${verifies} sur ${total}`}
            >
              <span className="rel-barre-plein" style={{ width: `${pourcent}%` }} />
            </div>
            {raisonDAttendre && (
              <p className="rel-meta" id="raison-d-attendre">
                {raisonDAttendre}
              </p>
            )}
          </div>
          <div className="rel-actions">
            {mode === "volets" && verifies < total && (
              <Button size="pro" variant="ghost" icon="eye" onClick={prochainAVerifier}>
                Prochain volet à vérifier
              </Button>
            )}
            <Button
              size="pro"
              icon="check"
              onClick={ouvrirLaConfirmation}
              disabled={Boolean(raisonDAttendre)}
              aria-describedby={raisonDAttendre ? "raison-d-attendre" : undefined}
            >
              Confirmer la transcription…
            </Button>
          </div>
        </div>
      </section>

      <p className="rel-masque" aria-live="polite">
        {annonce}
      </p>

      <Dialogue
        ouvert={dialogue === "confirmation"}
        titre="Confirmer la transcription"
        onFermer={() => !envoi && setDialogue(null)}
        large
        pied={
          <>
            <Button size="pro" icon="check" onClick={() => void confirmerMaintenant()} loading={envoi}>
              Confirmer la transcription
            </Button>
            <Button size="pro" variant="ghost" onClick={() => setDialogue(null)} disabled={envoi}>
              Revenir à la relecture
            </Button>
          </>
        }
      >
        <p>
          {`Vous avez vérifié ${pluriel(total, "volet", "volets")} contre les pages. Une fois confirmée, la Transcription part au Contrôle d'un autre agent de relecture ; vous ne pourrez plus la modifier, sauf s'il vous la renvoie.`}
        </p>
        <h3 className="rel-dialogue-sous-titre">Ce que vous avez changé depuis l'ouverture</h3>
        <ListeDesChangements depart={ouverture.depart} volets={volets} />
        <div className="rel-champ">
          <label className="rel-champ-libelle" htmlFor={idResume}>
            Résumé de vos changements
          </label>
          <textarea
            id={idResume}
            data-focus-initial
            className="lf-input rel-resume"
            rows={3}
            maxLength={1000}
            value={resume}
            onChange={(e) => setResume(e.target.value)}
            aria-describedby={`${idResume}-aide`}
          />
          <span id={`${idResume}-aide`} className="rel-champ-aide">
            Une ou deux phrases pour le contrôleur. Proposé d'après vos changements : reprenez-le à votre main.
          </span>
        </div>
        {refus && (
          <Alert tone="danger" title={"message" in refus && refus.message && refus.statut !== 422 ? refus.message : refus.statut === 422 ? "La confirmation est refusée." : motDuRefus(refus.statut)}>
            {"erreurs" in refus && refus.erreurs?.length ? (
              <ul className="rel-liste-simple">
                {refus.erreurs.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            ) : null}
            {"nonVerifies" in refus && refus.nonVerifies?.length ? (
              <p>{`Volets non cochés : ${refus.nonVerifies.map((r) => r + 1).join(", ")}.`}</p>
            ) : null}
            {refus.statut === 422 && "message" in refus && refus.message && !("erreurs" in refus && refus.erreurs?.length) ? <p>{refus.message}</p> : null}
          </Alert>
        )}
      </Dialogue>

      <Dialogue
        ouvert={dialogue === "inutilisable"}
        titre="Document inutilisable"
        onFermer={() => !envoi && setDialogue(null)}
        pied={
          <>
            <Button size="pro" variant="danger" icon="x" onClick={() => void clore()} disabled={!raison} loading={envoi}>
              Clore sans Transcription
            </Button>
            <Button size="pro" variant="ghost" onClick={() => setDialogue(null)} disabled={envoi}>
              Revenir à la relecture
            </Button>
          </>
        }
      >
        <p>
          La Relecture sera close sans Transcription. Le Document reste dans le dossier tel qu'il a été numérisé ; personne ne
          rappelle le citoyen. Un passage illisible n'est pas une raison : faites-en un volet « Passage illisible ».
        </p>
        <fieldset className="rel-raisons">
          <legend className="rel-champ-libelle">Pourquoi ?</legend>
          {RAISONS_D_INUTILISABLE.map((r, i) => (
            <label key={r.code} className="rel-raison">
              <input
                type="radio"
                name="raison"
                value={r.code}
                checked={raison === r.code}
                onChange={() => setRaison(r.code)}
                data-focus-initial={i === 0 ? true : undefined}
              />
              <Icon name={r.icone} size={22} />
              <span>
                <strong>{r.libelle}</strong>
                <span className="rel-meta">{` ${r.aide}`}</span>
              </span>
            </label>
          ))}
        </fieldset>
        {refus && dialogue === "inutilisable" && <Alert tone="danger" title={"message" in refus && refus.message ? refus.message : motDuRefus(refus.statut)} />}
      </Dialogue>
    </div>
  );
}
