"use client";

// Le Contrôle : un second agent de relecture lit la Transcription confirmée contre les pages, sans la
// modifier, puis l'accepte (elle devient relue) ou la renvoie à son relecteur avec une note.
import { LIBELLES_DES_VOLETS, lireTranscription, RenduDeVolet } from "@lafia/commun/transcription";
import { Alert, Button, Icon } from "@lafia/design";
import { useRouter } from "next/navigation";
import { useCallback, useId, useMemo, useState } from "react";

import { adresseDeLaPage, pluriel } from "../../../libelles";
import type { DocumentARelire, Modele } from "../../../types";
import { controlerLaTranscription } from "../../actions";
import { Contexte } from "./Contexte";
import { Dialogue } from "./Dialogue";
import { Feuilles, type Citation } from "./Feuilles";
import { adresseDeLaSuite, avecSession, motDuRefus } from "./session";

export function Controler({
  tache,
  document: doc,
  description,
  markdown,
  resume,
  modele,
  texte,
}: {
  tache: string;
  document: DocumentARelire;
  description: string;
  markdown: string;
  resume: string | null;
  modele: Modele | null;
  texte: string | null;
}) {
  const router = useRouter();
  const pages = Math.max(1, doc.pages);
  const idNote = useId();
  const transcription = useMemo(() => lireTranscription(markdown, pages), [markdown, pages]);
  const [pageEnVue, setPageEnVue] = useState(1);
  const [cible, setCible] = useState<{ page: number; n: number } | null>(null);
  const [dialogue, setDialogue] = useState<null | "accepter" | "renvoyer">(null);
  const [note, setNote] = useState("");
  const [envoi, setEnvoi] = useState(false);
  const [refus, setRefus] = useState<string | null>(null);
  const [lus, setLus] = useState<Set<number>>(new Set());

  const citations = useMemo(() => {
    const parPage: Record<number, Citation[]> = {};
    transcription.volets.forEach((v) => {
      for (const p of v.pages) (parPage[p] ??= []).push({ cle: String(v.rang), libelle: `${v.rang + 1} · ${LIBELLES_DES_VOLETS[v.type]}` });
    });
    return parPage;
  }, [transcription]);

  const voirVolet = useCallback((cle: string) => {
    const carte = document.getElementById(`volet-${cle}`);
    carte?.scrollIntoView({ block: "start", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    carte?.focus({ preventScroll: true });
  }, []);

  function voirPage(page: number) {
    setCible((c) => ({ page, n: (c?.n ?? 0) + 1 }));
  }

  async function decider(decision: "accepter" | "renvoyer") {
    if (decision === "renvoyer" && !note.trim()) {
      setRefus("Écrivez ce que le relecteur doit reprendre : la note lui est rendue avec la tâche.");
      return;
    }
    setEnvoi(true);
    setRefus(null);
    let issue;
    try {
      issue = await avecSession(() => controlerLaTranscription(tache, decision, note));
    } catch {
      issue = { ok: false as const, statut: 0 };
    }
    if (issue.ok) {
      router.push(adresseDeLaSuite(issue.suivante, decision === "accepter" ? "acceptee" : "renvoyee"));
      return;
    }
    setEnvoi(false);
    setRefus(motDuRefus(issue.statut));
  }

  const total = transcription.volets.length;

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
      />

      <section className="rel-panneau" aria-labelledby="titre-controle">
        <Contexte modele={modele} notes={[]} texte={texte} consigne="controle" />

        <div className="rel-panneau-tete">
          <h2 className="lf-app-sous-titre-fort" id="titre-controle">
            Transcription confirmée
          </h2>
          <p className="rel-meta">
            Lisez chaque volet contre ses pages. Vous ne la modifiez pas : acceptez-la, ou renvoyez-la avec ce qui est à reprendre.
          </p>
        </div>

        <figure className="rel-resume-du-relecteur">
          <figcaption>Résumé du relecteur</figcaption>
          <blockquote>{resume?.trim() || "Le relecteur n'a pas laissé de résumé."}</blockquote>
        </figure>

        {transcription.erreurs.length > 0 && (
          <Alert tone="attention" title="Points hors du format de l'ADR 0010">
            <ul className="rel-liste-simple">
              {transcription.erreurs.map((e, i) => (
                <li key={`${i}-${e}`}>{e}</li>
              ))}
            </ul>
          </Alert>
        )}

        <ol className="rel-volets" aria-label="Les volets de la Transcription">
          {transcription.volets.map((v) => {
            const enVue = v.pages.includes(pageEnVue);
            const lu = lus.has(v.rang);
            return (
              <li
                key={v.rang}
                id={`volet-${v.rang}`}
                tabIndex={-1}
                className={["rel-volet", enVue && "is-en-vue", lu && "is-verifie"].filter(Boolean).join(" ")}
              >
                <div className="rel-volet-outils">
                  <span className="rel-volet-rang rel-chiffres">{`Volet ${v.rang + 1} / ${total}`}</span>
                  {enVue && (
                    <span className="rel-marque rel-marque--vue">
                      <Icon name="eye" size={16} />
                      <span>{`page ${pageEnVue} en vue`}</span>
                    </span>
                  )}
                </div>
                <RenduDeVolet volet={v} urlDePage={(n) => adresseDeLaPage(tache, n)} surPage={voirPage} />
                <label className="rel-verifie">
                  <input
                    type="checkbox"
                    checked={lu}
                    onChange={(e) =>
                      setLus((deja) => {
                        const suivant = new Set(deja);
                        if (e.target.checked) suivant.add(v.rang);
                        else suivant.delete(v.rang);
                        return suivant;
                      })
                    }
                  />
                  <span>
                    <strong>Lu contre les pages</strong>
                    <span className="rel-meta"> : pour vous repérer, rien n'est envoyé.</span>
                  </span>
                </label>
              </li>
            );
          })}
        </ol>

        <div className="rel-confirmer">
          <div className="rel-confirmer-compte">
            <p className="rel-confirmer-chiffres">
              <span className="rel-chiffres">{`${lus.size} / ${total}`}</span>
              <span>{` ${total > 1 ? "volets lus" : "volet lu"}`}</span>
            </p>
          </div>
          <div className="rel-actions">
            <Button
              size="pro"
              variant="secondary"
              icon="arrow-left"
              onClick={() => {
                setRefus(null);
                setDialogue("renvoyer");
              }}
            >
              Renvoyer au relecteur…
            </Button>
            <Button
              size="pro"
              icon="check"
              onClick={() => {
                setRefus(null);
                setDialogue("accepter");
              }}
            >
              Accepter la transcription…
            </Button>
          </div>
        </div>
      </section>

      <Dialogue
        ouvert={dialogue === "accepter"}
        titre="Accepter la transcription"
        onFermer={() => !envoi && setDialogue(null)}
        pied={
          <>
            <Button size="pro" icon="check" onClick={() => void decider("accepter")} loading={envoi} data-focus-initial>
              Accepter la transcription
            </Button>
            <Button size="pro" variant="ghost" onClick={() => setDialogue(null)} disabled={envoi}>
              Revenir au Contrôle
            </Button>
          </>
        }
      >
        <p>
          {`La Transcription (${pluriel(total, "volet")}) devient relue : le soignant et le citoyen pourront la lire à côté des pages, avec la mention qu'elle n'est pas une donnée clinique vérifiée.`}
        </p>
        {lus.size < total && (
          <p className="rel-meta">{`Vous avez marqué ${lus.size} volet${lus.size > 1 ? "s" : ""} sur ${total} comme lus.`}</p>
        )}
        {refus && <Alert tone="danger" title={refus} />}
      </Dialogue>

      <Dialogue
        ouvert={dialogue === "renvoyer"}
        titre="Renvoyer au relecteur"
        onFermer={() => !envoi && setDialogue(null)}
        pied={
          <>
            <Button size="pro" icon="arrow-left" onClick={() => void decider("renvoyer")} loading={envoi}>
              Renvoyer avec cette note
            </Button>
            <Button size="pro" variant="ghost" onClick={() => setDialogue(null)} disabled={envoi}>
              Revenir au Contrôle
            </Button>
          </>
        }
      >
        <p>Le relecteur retrouve la tâche dans sa semaine, avec votre note en tête. Son brouillon reste tel qu'il l'a confirmé.</p>
        <div className="rel-champ">
          <label className="rel-champ-libelle" htmlFor={idNote}>
            Ce qu'il doit reprendre (obligatoire)
          </label>
          <textarea
            id={idNote}
            data-focus-initial
            className="lf-input rel-resume"
            rows={4}
            maxLength={2000}
            required
            aria-required="true"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            aria-describedby={`${idNote}-aide`}
          />
          <span id={`${idNote}-aide`} className="rel-champ-aide">
            Citez le volet et la page : « Volet 3, page 5 : la date est 2019-03-15, pas 2019-03-14. »
          </span>
        </div>
        {refus && <Alert tone="danger" title={refus} />}
      </Dialogue>
    </div>
  );
}
