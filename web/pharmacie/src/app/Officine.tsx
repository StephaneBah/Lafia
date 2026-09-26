"use client";

import {
  Alert,
  Button,
  Card,
  Icon,
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

import { detail } from "./Comptoir";
import { Scanner } from "./Scanner";

// Ce que le service pharmacie rend à une officine (`pharmacie.officine.OrdonnanceEnOfficine`) :
// de quoi vérifier l'ordonnance, et ce qu'elle peut en vendre ; jamais le patient.
type Ligne = {
  id: string;
  libelle: string;
  prescrite: number;
  remise: number;
  reste: number;
  posologie: { moments: Moment[]; jours: number | null; dose: number | null; texte: string | null };
  vendable: boolean;
  raison: string | null;
};
type Ordonnance = {
  numero: string;
  prescripteur: string | null;
  date: string | null;
  etablissement: string | null;
  lignes: Ligne[];
};
type Vente = { id: string; ligne: string; libelle: string; quantite: number; reste: number };

const API = "/api/pharmacie/officine/ordonnances";

function messageDeRefus(statut: number, texte: string | null): string {
  if (statut === 401) return "Votre session a expiré : reconnectez-vous.";
  if (statut === 403) return "Cet écran est réservé aux officines.";
  if (statut === 404) return "Aucune ordonnance sous ce numéro. Vérifiez-le sur le reçu : une ordonnance inconnue n’est pas authentique.";
  if ((statut === 409 || statut === 422) && texte) return `Rien n’a été déclaré : ${texte}.`;
  return "Le service pharmacie ne répond pas. Réessayez dans un instant.";
}

function statutDe(ligne: Ligne): Status {
  if (ligne.reste === 0) return "retire";
  if (!ligne.vendable) return "paye";
  return ligne.remise > 0 ? "partiel" : "aretirer";
}

/** L'officine : numéro ou QR code, vérification de l'ordonnance, lignes vendues, déclaration. */
export function Officine() {
  const [saisie, setSaisie] = useState("");
  const [ordonnance, setOrdonnance] = useState<Ordonnance | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(false);
  const [choisies, setChoisies] = useState<Record<string, boolean>>({});
  const [quantites, setQuantites] = useState<Record<string, number>>({});
  const [ventes, setVentes] = useState<Vente[] | null>(null);

  function preparer(vue: Ordonnance) {
    setOrdonnance(vue);
    const vendables = vue.lignes.filter((l) => l.vendable);
    // Rien n'est coché d'avance : l'officine déclare ce qu'elle a vraiment vendu.
    setChoisies(Object.fromEntries(vendables.map((l) => [l.id, false])));
    setQuantites(Object.fromEntries(vendables.map((l) => [l.id, l.reste])));
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

  async function lancer(numero: string) {
    if (!numero.trim()) return;
    setChargement(true);
    setErreur(null);
    setVentes(null);
    setOrdonnance(null);
    try {
      await ouvrir(numero);
    } catch {
      setErreur(messageDeRefus(0, null));
    } finally {
      setChargement(false);
    }
  }

  async function chercher(evenement: FormEvent) {
    evenement.preventDefault();
    await lancer(saisie);
  }

  if (!ordonnance) {
    return (
      <>
        <h1 className="lf-app-titre">Vérifier une ordonnance</h1>
        <form className="cp-recherche" onSubmit={chercher}>
          <TextInput
            size="pro"
            label="Numéro d’ordonnance"
            hint="Il figure sur le reçu du patient, avec son QR code : ORD-7K4-M2P."
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
            Vérifier
          </Button>
          <Scanner
            onNumero={(numero) => {
              setSaisie(numero);
              void lancer(numero);
            }}
          />
        </form>
        {erreur && (
          <Alert tone="attention" title="Ordonnance non vérifiée">
            {erreur} {erreur.startsWith("Votre session") && <a href="/connexion">Se connecter</a>}
          </Alert>
        )}
      </>
    );
  }

  const vue = ordonnance;
  const vendables = vue.lignes.filter((l) => l.vendable);
  const autres = vue.lignes.filter((l) => !l.vendable);
  const choix = vendables.filter((l) => choisies[l.id]);
  const quantitesValides = choix.every((l) => {
    const q = quantites[l.id];
    return Number.isInteger(q) && q >= 1 && q <= l.reste;
  });
  const peutDeclarer = choix.length > 0 && quantitesValides;

  async function declarer() {
    setChargement(true);
    setErreur(null);
    try {
      const reponse = await fetch(`${API}/${encodeURIComponent(vue.numero)}/ventes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lignes: choix.map((l) => ({ id: l.id, quantite: quantites[l.id] })) }),
      });
      if (reponse.status !== 201) {
        setErreur(messageDeRefus(reponse.status, await detail(reponse)));
        return;
      }
      const { delivrances } = (await reponse.json()) as { delivrances: Vente[] };
      setVentes(delivrances);
      await ouvrir(vue.numero);
    } catch {
      setErreur(messageDeRefus(0, null));
    } finally {
      setChargement(false);
    }
  }

  function autreOrdonnance() {
    setOrdonnance(null);
    setVentes(null);
    setErreur(null);
    setSaisie("");
  }

  return (
    <>
      <div className="cp-entete">
        <div className="cp-numero-ord">{vue.numero}</div>
        <span className="cp-espace" />
        <Button size="pro" variant="secondary" icon="arrow-left" onClick={autreOrdonnance}>
          Autre ordonnance
        </Button>
      </div>

      <Card className="of-verification">
        <div className="of-authentique">
          <Icon name="shield-check" size={28} />
          <div>
            <div className="of-authentique-titre">Ordonnance authentique</div>
            <div className="cp-meta">Émise dans Lafia sous ce numéro. Comparez avec le papier présenté.</div>
          </div>
        </div>
        <dl className="of-faits">
          <div>
            <dt>Prescripteur</dt>
            <dd>{vue.prescripteur ? `Dr ${vue.prescripteur}` : "Non renseigné"}</dd>
          </div>
          <div>
            <dt>Date</dt>
            <dd>{vue.date ? formatDate(vue.date) : "Non renseignée"}</dd>
          </div>
          <div>
            <dt>Établissement</dt>
            <dd>{vue.etablissement ?? "Non renseigné"}</dd>
          </div>
        </dl>
      </Card>

      {ventes && ventes.length > 0 && (
        <Alert tone="succes" title="Vente déclarée">
          <ul className="cp-liste">
            {ventes.map((v) => (
              <li key={v.id}>
                {`${v.libelle} : ${v.quantite} vendu${v.quantite > 1 ? "s" : ""}`}
                {v.reste > 0 ? `, reste ${v.reste} sur l’ordonnance` : ", ligne complète"}
              </li>
            ))}
          </ul>
        </Alert>
      )}

      {erreur && (
        <Alert tone="danger" title="Vente non déclarée">
          {erreur}
        </Alert>
      )}

      <div className="cp-grille">
        <section aria-labelledby="of-a-vendre">
          <h2 className="cp-colonne" id="of-a-vendre">
            <Picto name="a-retirer" size={24} decorative />
            {`À vendre (${vendables.length})`}
          </h2>
          {vendables.length === 0 ? (
            <div className="cp-vide">Aucune ligne de cette ordonnance ne se vend en officine.</div>
          ) : (
            <Card dense className="cp-lignes">
              {vendables.map((ligne) => {
                const choisie = Boolean(choisies[ligne.id]);
                return (
                  <div key={ligne.id} className="cp-ligne">
                    <OrdonnanceLine
                      mode="pharmacie"
                      status={statutDe(ligne)}
                      detail={
                        ligne.remise > 0
                          ? `${ligne.remise} déjà remis sur ${ligne.prescrite} · reste ${ligne.reste}`
                          : `${ligne.prescrite} prescrit${ligne.prescrite > 1 ? "s" : ""}`
                      }
                      checked={choisie}
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
                      <label className="cp-quantite">
                        <span>Quantité vendue</span>
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
                    </div>
                  </div>
                );
              })}
            </Card>
          )}
          <div className="cp-actions">
            <Button size="pro" icon="check" disabled={!peutDeclarer} loading={chargement} onClick={declarer}>
              {choix.length > 1 ? `Déclarer la vente de ${choix.length} lignes` : "Déclarer la vente"}
            </Button>
            <span className="cp-meta">Le paiement reste dans votre logiciel de caisse.</span>
          </div>
        </section>

        <section aria-labelledby="of-hors">
          <h2 className="cp-colonne" id="of-hors">
            <Picto name="retire" size={24} decorative />
            {`Pas en officine (${autres.length})`}
          </h2>
          {autres.length === 0 ? (
            <div className="cp-vide">Toutes les lignes peuvent se vendre ici.</div>
          ) : (
            autres.map((ligne) => (
              <div key={ligne.id} className="cp-remise">
                <div>
                  <div className="cp-remise-nom">{ligne.libelle}</div>
                  <div className="cp-meta">{ligne.raison ?? `${ligne.remise} remis sur ${ligne.prescrite}`}</div>
                </div>
                <StatusBadge status={statutDe(ligne)} size="pro" />
              </div>
            ))
          )}
        </section>
      </div>
    </>
  );
}
