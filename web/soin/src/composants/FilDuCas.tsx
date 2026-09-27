import { TimelineItem, formatDate } from "@lafia/design";

import type { Cas, Produit, Visite } from "../lib/types";

function icone(visite: Visite) {
  if (visite.urgence) return "warning-octagon" as const;
  if (visite.ordonnance) return "receipt" as const;
  if (visite.type === "soins-infirmiers") return "heartbeat" as const;
  return "stethoscope" as const;
}

/** Une valeur de mesure avec son unité lisible. */
export function valeurDeMesure(valeur: string | number, unite: string | null | undefined): string {
  const texte = String(valeur).replace(".", ",");
  if (!unite) return texte;
  return unite === "Cel" ? `${texte} °C` : `${texte} ${unite}`;
}

/** Une visite sur le fil : mesures, diagnostics, ordonnance. */
function ContenuDeVisite({ visite, formes }: { visite: Visite; formes: Map<string, string> }) {
  return (
    <div className="sn-visite">
      {visite.motif && <p>{visite.motif}</p>}
      {visite.mesures.length > 0 && (
        <dl className="sn-kv">
          {visite.mesures.map((m) => (
            <div key={m.id}>
              <dt>{m.libelle}</dt>
              <dd>{valeurDeMesure(m.valeur, m.unite)}</dd>
            </div>
          ))}
        </dl>
      )}
      {visite.diagnostics.map((d) => (
        <p key={d.id}>
          <b>{d.libelle}</b>
          {` · ${d.confirme ? "confirmé" : "provisoire"}`}
          {d.note && ` · ${d.note}`}
        </p>
      ))}
      {visite.ordonnance && (
        <div className="sn-ordonnance">
          <b className="lf-mono">{`Ordonnance ${visite.ordonnance.numero ?? ""}`}</b>
          <ul>
            {visite.ordonnance.lignes.map((l) => {
              const forme = l.produit ? formes.get(l.produit) : undefined;
              return (
                <li key={l.id}>
                  {l.libelle}
                  {l.posologie && <span className="sn-meta">{` · ${l.posologie}`}</span>}
                  {l.quantite !== null && <span className="sn-meta">{` · ${l.quantite}${forme ? ` ${forme}` : ""}`}</span>}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Le fil d'un cas : ses visites dans l'ordre, la dernière en cours tant que le cas l'est. */
export function FilDuCas({ cas, produits = [] }: { cas: Cas; produits?: Produit[] }) {
  const formes = new Map(produits.filter((p) => p.forme).map((p) => [p.code, p.forme as string]));
  if (cas.visites.length === 0) return <div className="sn-vide">Aucune visite encore dans ce cas.</div>;
  return (
    <ol className="lf-timeline">
      {cas.visites.map((v, i) => (
        <TimelineItem
          key={v.id}
          first={i === 0}
          last={i === cas.visites.length - 1}
          state={cas.statut === "en-cours" && i === cas.visites.length - 1 ? "current" : "done"}
          icon={icone(v)}
          date={v.date ? formatDate(v.date) : undefined}
          place={[v.etablissement, v.soignant].filter(Boolean).join(" · ")}
          title={v.type_libelle}
          animate
          index={i}
        >
          <ContenuDeVisite visite={v} formes={formes} />
        </TimelineItem>
      ))}
    </ol>
  );
}
