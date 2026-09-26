"use client";

import {
  Alert,
  Button,
  Card,
  OrdonnanceLine,
  Picto,
  Posology,
  StatusBadge,
  TextInput,
  formatDate,
  type Moment,
  type Status,
} from "@lafia/design";
import { useState, type FormEvent } from "react";

// Ce que le service pharmacie rend (`pharmacie.ordonnance.OrdonnanceVue`) ; la page le demande depuis
// le navigateur, par la passerelle, sous le cookie de session de l'application.
type Ligne = {
  id: string;
  libelle: string;
  prescrite: number;
  payee: boolean;
  remise: number;
  reste: number;
  statut: "apayer" | "aretirer" | "partiel" | "retire";
  posologie: { moments: Moment[]; jours: number | null; dose: number | null; texte: string | null };
};
type Ordonnance = {
  numero: string;
  patient: { nom: string; prenoms: string };
  prescripteur: string | null;
  date: string | null;
  lignes: Ligne[];
  allergies: { libelle: string; lignes: string[] }[];
};
type Delivrance = { id: string; ligne: string; libelle: string; quantite: number; reste: number };

const API = "/api/pharmacie/ordonnances";

async function detail(reponse: Response): Promise<string | null> {
  try {
    const corps = (await reponse.json()) as { detail?: unknown };
    return typeof corps.detail === "string" ? corps.detail : null;
  } catch {
    return null;
  }
}

function messageDeRefus(statut: number, texte: string | null): string {
  if (statut === 401) return "Votre session a expiré : reconnectez-vous.";
  if (statut === 403) return texte === "rôle non admis" ? "Ce comptoir est réservé aux pharmaciens." : "Cette ordonnance se sert dans un autre établissement.";
  if (statut === 404) return "Aucune ordonnance à remettre sous ce numéro. Vérifiez-le sur le reçu.";
  if (statut === 409 && texte) return `Rien n'a été remis : ${texte}.`;
  return "Le service pharmacie ne répond pas. Réessayez dans un instant.";
}

/** Le statut de l'ordonnance entière : ce que le pharmacien voit d'un coup d'œil. */
function statutGlobal(lignes: Ligne[]): Status {
  if (lignes.length && lignes.every((l) => l.statut === "retire")) return "retire";
  if (lignes.some((l) => l.remise > 0)) return "partiel";
  if (lignes.some((l) => l.statut === "aretirer")) return "paye";
  return "apayer";
}

function quantiteDe(ligne: Ligne): string {
  if (ligne.remise === 0) return `${ligne.prescrite} prescrit${ligne.prescrite > 1 ? "s" : ""}`;
  return `${ligne.remise} remis sur ${ligne.prescrite} · reste ${ligne.reste}`;
}

/** Le comptoir : numéro, ordonnance, allergie à reconnaître, lignes à remettre, remise. */
export function Comptoir() {
  const [saisie, setSaisie] = useState("");
  const [ordonnance, setOrdonnance] = useState<Ordonnance | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(false);
  const [choisies, setChoisies] = useState<Record<string, boolean>>({});
  const [quantites, setQuantites] = useState<Record<string, number>>({});
  const [allergieReconnue, setAllergieReconnue] = useState(false);
  const [remises, setRemises] = useState<Delivrance[] | null>(null);

  function preparer(vue: Ordonnance) {
    setOrdonnance(vue);
    const allergiques = new Set(vue.allergies.flatMap((a) => a.lignes));
    const aRemettre = vue.lignes.filter((l) => l.payee && l.reste > 0);
    // Une ligne concernée par une allergie n'est jamais cochée d'avance.
    setChoisies(Object.fromEntries(aRemettre.map((l) => [l.id, !allergiques.has(l.id)])));
    setQuantites(Object.fromEntries(aRemettre.map((l) => [l.id, l.reste])));
    setAllergieReconnue(false);
  }

  async function ouvrir(numero: string): Promise<boolean> {
    const reponse = await fetch(`${API}/${encodeURIComponent(numero.trim())}`, { cache: "no-store" });
    if (!reponse.ok) {
      setErreur(messageDeRefus(reponse.status, await detail(reponse)));
      return false;
    }
    preparer((await reponse.json()) as Ordonnance);
    return true;
  }

  async function chercher(evenement: FormEvent) {
    evenement.preventDefault();
    if (!saisie.trim()) return;
    setChargement(true);
    setErreur(null);
    setRemises(null);
    setOrdonnance(null);
    try {
      await ouvrir(saisie);
    } catch {
      setErreur(messageDeRefus(0, null));
    } finally {
      setChargement(false);
    }
  }

  if (!ordonnance) {
    return (
      <>
        <h1 className="lf-app-titre">Remettre une ordonnance</h1>
        <form className="cp-recherche" onSubmit={chercher}>
          <TextInput
            size="pro"
            label="Numéro d’ordonnance"
            hint="Il figure sur le reçu du patient : ORD-7K4-M2P."
            icon="receipt"
            className="cp-numero"
            value={saisie}
            onChange={(e) => setSaisie(e.target.value)}
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            autoFocus
            required
          />
          <Button type="submit" size="pro" icon="magnifying-glass" loading={chargement}>
            Ouvrir
          </Button>
        </form>
        {erreur && (
          <Alert tone="attention" title="Ordonnance non ouverte">
            {erreur} {erreur.startsWith("Votre session") && <a href="/connexion">Se connecter</a>}
          </Alert>
        )}
      </>
    );
  }

  const vue = ordonnance;
  const lignesAllergiques = new Set(vue.allergies.flatMap((a) => a.lignes));
  const aRemettre = vue.lignes.filter((l) => l.reste > 0);
  const remisesLignes = vue.lignes.filter((l) => l.remise > 0);
  const choix = aRemettre.filter((l) => l.payee && choisies[l.id]);
  const allergieEnJeu = aRemettre.some((l) => l.payee && lignesAllergiques.has(l.id));
  const allergieChoisie = choix.some((l) => lignesAllergiques.has(l.id));
  const quantitesValides = choix.every((l) => {
    const q = quantites[l.id];
    return Number.isInteger(q) && q >= 1 && q <= l.reste;
  });
  const peutRemettre = choix.length > 0 && quantitesValides && (!allergieChoisie || allergieReconnue);
  const libelleDe = (id: string) => vue.lignes.find((l) => l.id === id)?.libelle ?? id;

  async function remettre() {
    setChargement(true);
    setErreur(null);
    try {
      const reponse = await fetch(`${API}/${encodeURIComponent(vue.numero)}/delivrances`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lignes: choix.map((l) => ({ id: l.id, quantite: quantites[l.id] })),
          allergie_reconnue: allergieReconnue,
        }),
      });
      if (reponse.status !== 201) {
        setErreur(messageDeRefus(reponse.status, await detail(reponse)));
        return;
      }
      const { delivrances } = (await reponse.json()) as { delivrances: Delivrance[] };
      setRemises(delivrances);
      await ouvrir(vue.numero);
    } catch {
      setErreur(messageDeRefus(0, null));
    } finally {
      setChargement(false);
    }
  }

  function autreOrdonnance() {
    setOrdonnance(null);
    setRemises(null);
    setErreur(null);
    setSaisie("");
  }

  return (
    <>
      <div className="cp-entete">
        <div>
          <div className="cp-numero-ord">{vue.numero}</div>
          <div className="cp-meta">
            {[`${vue.patient.prenoms} ${vue.patient.nom}`.trim(), vue.prescripteur && `Dr ${vue.prescripteur}`, vue.date && formatDate(vue.date)]
              .filter(Boolean)
              .join(" · ")}
          </div>
        </div>
        <span className="cp-espace" />
        <StatusBadge status={statutGlobal(vue.lignes)} size="pro" />
        <Button size="pro" variant="secondary" icon="arrow-left" onClick={autreOrdonnance}>
          Autre ordonnance
        </Button>
      </div>

      {remises && remises.length > 0 && (
        <Alert tone="succes" title="Remis au patient">
          <ul className="cp-liste">
            {remises.map((d) => (
              <li key={d.id}>
                {`${d.libelle} : ${d.quantite} remis`}
                {d.reste > 0 ? `, reste ${d.reste} à retirer plus tard` : ", ligne complète"}
              </li>
            ))}
          </ul>
        </Alert>
      )}

      {allergieEnJeu &&
        vue.allergies.map((allergie) => (
          <Alert
            key={allergie.libelle}
            tone="allergie"
            title={`Allergie : ${allergie.libelle} · ${allergie.lignes.map(libelleDe).join(", ")}`}
            actions={
              <label className="cp-reconnaitre">
                <input
                  type="checkbox"
                  checked={allergieReconnue}
                  onChange={(e) => setAllergieReconnue(e.target.checked)}
                />
                <span>J’ai vu l’allergie. Je remets en connaissance de cause, après avis du prescripteur.</span>
              </label>
            }
          >
            Le patient a déclaré une allergie qui concerne cette ligne. Ne la remettez pas sans l’avis du prescripteur ;
            décochez-la pour la laisser de côté.
          </Alert>
        ))}

      {erreur && (
        <Alert tone="danger" title="Remise refusée">
          {erreur}
        </Alert>
      )}

      <div className="cp-grille">
        <section aria-labelledby="cp-a-remettre">
          <h2 className="cp-colonne" id="cp-a-remettre">
            <Picto name="a-retirer" size={24} decorative />
            {`À remettre (${aRemettre.length})`}
          </h2>
          {aRemettre.length === 0 ? (
            <div className="cp-vide">Toutes les lignes sont remises.</div>
          ) : (
            <Card dense className="cp-lignes">
              {aRemettre.map((ligne) => {
                const allergique = lignesAllergiques.has(ligne.id);
                const choisie = Boolean(choisies[ligne.id]) && ligne.payee;
                return (
                  <div key={ligne.id} className={allergique ? "cp-ligne has-allergy" : "cp-ligne"}>
                    <OrdonnanceLine
                      mode="pharmacie"
                      status={allergique && ligne.payee ? "allergie" : ligne.statut}
                      detail={ligne.payee ? quantiteDe(ligne) : "À payer d’abord à la caisse"}
                      allergy={allergique ? "Allergie déclarée : voir l’alerte" : undefined}
                      checked={choisie}
                      disabled={!ligne.payee}
                      onToggle={(coche) => setChoisies({ ...choisies, [ligne.id]: coche })}
                    >
                      {ligne.libelle}
                    </OrdonnanceLine>
                    <div className="cp-ligne-pied">
                      <Posology
                        size={28}
                        count={ligne.posologie.dose ?? undefined}
                        moments={ligne.posologie.moments}
                        days={ligne.posologie.jours ?? undefined}
                      />
                      {ligne.payee && (
                        <label className="cp-quantite">
                          <span>Quantité remise</span>
                          <input
                            type="number"
                            className="lf-input"
                            min={1}
                            max={ligne.reste}
                            step={1}
                            value={quantites[ligne.id] ?? ligne.reste}
                            disabled={!choisie}
                            onChange={(e) => setQuantites({ ...quantites, [ligne.id]: Number(e.target.value) })}
                          />
                          <span className="cp-sur">{`sur ${ligne.reste}`}</span>
                        </label>
                      )}
                    </div>
                  </div>
                );
              })}
            </Card>
          )}
          <div className="cp-actions">
            <Button size="pro" icon="check" disabled={!peutRemettre} loading={chargement} onClick={remettre}>
              {choix.length > 1 ? `Remettre ${choix.length} lignes` : "Remettre"}
            </Button>
            {allergieChoisie && !allergieReconnue && (
              <span className="cp-meta">Reconnaissez l’allergie, ou décochez la ligne concernée.</span>
            )}
          </div>
        </section>

        <section aria-labelledby="cp-remis">
          <h2 className="cp-colonne" id="cp-remis">
            <Picto name="retire" size={24} decorative />
            {`Remis (${remisesLignes.length})`}
          </h2>
          {remisesLignes.length === 0 ? (
            <div className="cp-vide">Rien n’a encore été remis sur cette ordonnance.</div>
          ) : (
            remisesLignes.map((ligne) => (
              <div key={ligne.id} className="cp-remise">
                <div>
                  <div className="cp-remise-nom">{ligne.libelle}</div>
                  <div className="cp-meta">{`${ligne.remise} remis sur ${ligne.prescrite}`}</div>
                </div>
                <StatusBadge status={ligne.reste > 0 ? "partiel" : "retire"} size="pro" />
              </div>
            ))
          )}
        </section>
      </div>
    </>
  );
}
