"use client";

import { Button, OrdonnanceLine, StatusBadge, formatDate, formatFcfa } from "@lafia/design";
import { useState } from "react";

import type { Ordonnance } from "../caisse";
import { encaisserLesLignes } from "./actions";

/**
 * L'ordonnance ouverte : ses lignes à cocher, le total de la sélection, et « Encaisser ». Les lignes
 * déjà payées sont montrées, marquées « Payé », et ne se cochent pas. Rien n'est saisi : chaque montant
 * vient du tarif de l'établissement.
 */
export function Encaissement({ ordonnance }: { ordonnance: Ordonnance }) {
  const aPayer = ordonnance.lignes.filter((ligne) => !ligne.payee);
  const [cochees, setCochees] = useState<Set<string>>(() => new Set(aPayer.map((ligne) => ligne.id)));
  const [envoi, setEnvoi] = useState(false);
  const selection = aPayer.filter((ligne) => cochees.has(ligne.id));
  const total = selection.reduce((somme, ligne) => somme + ligne.montant, 0);
  const toutPaye = aPayer.length === 0;

  function basculer(id: string, coche: boolean) {
    const suivantes = new Set(cochees);
    if (coche) suivantes.add(id);
    else suivantes.delete(id);
    setCochees(suivantes);
  }

  const patient = `${ordonnance.patient.prenoms} ${ordonnance.patient.nom}`.trim();

  return (
    <form className="caisse-grille" action={encaisserLesLignes} onSubmit={() => setEnvoi(true)}>
      <input type="hidden" name="numero" value={ordonnance.numero} />
      <section className="caisse-ordonnance" aria-labelledby="caisse-numero">
        <header className="caisse-ordonnance-tete">
          <div>
            <h2 id="caisse-numero" className="caisse-numero">
              {ordonnance.numero}
            </h2>
            <p className="caisse-meta">
              {[patient, ordonnance.prescripteur && `prescrite par ${ordonnance.prescripteur}`, ordonnance.date && formatDate(ordonnance.date)]
                .filter(Boolean)
                .join(" · ")}
            </p>
            <p className="caisse-meta">{ordonnance.etablissement}</p>
          </div>
          <StatusBadge status={toutPaye ? "paye" : "apayer"} size="pro" />
        </header>
        {ordonnance.lignes.map((ligne) => (
          <OrdonnanceLine
            key={ligne.id}
            mode="caisse"
            name="lignes"
            value={ligne.id}
            detail={`${ligne.quantite} × ${formatFcfa(ligne.prix_unitaire)} · tarif de l'établissement`}
            price={ligne.montant}
            status={ligne.payee ? "paye" : undefined}
            checked={ligne.payee ? false : cochees.has(ligne.id)}
            disabled={ligne.payee}
            onToggle={ligne.payee ? undefined : (coche) => basculer(ligne.id, coche)}
          >
            {ligne.libelle}
          </OrdonnanceLine>
        ))}
        {toutPaye && (
          <div className="caisse-tampon" aria-hidden="true">
            Payé
          </div>
        )}
      </section>
      <aside className="caisse-total">
        <p className="caisse-meta">Total à encaisser</p>
        <p className="caisse-montant" aria-live="polite">
          {formatFcfa(total)}
        </p>
        <p className="caisse-meta">
          {toutPaye
            ? "Toutes les lignes sont payées : rien à encaisser."
            : `${selection.length} ligne(s) sur ${aPayer.length} cochée(s). Aucun montant saisi : les tarifs viennent de l'établissement.`}
        </p>
        {!toutPaye && (
          <Button type="submit" size="pro" icon="money" block disabled={total === 0} loading={envoi}>
            {`Encaisser ${formatFcfa(total)}`}
          </Button>
        )}
      </aside>
    </form>
  );
}
