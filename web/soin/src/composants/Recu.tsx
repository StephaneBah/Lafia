"use client";

import { Alert, Button, Logo, Posology } from "@lafia/design";

import { adresseDuPatient } from "../lib/adresses";
import { traceQr } from "../lib/qr";
import type { Catalogue, Recu } from "../lib/types";

function Qr({ texte }: { texte: string }) {
  const { chemin, cote } = traceQr(texte);
  return (
    <svg className="sn-qr" viewBox={`0 0 ${cote} ${cote}`} role="img" aria-label={`QR code du numéro ${texte}`} shapeRendering="crispEdges">
      <rect width={cote} height={cote} fill="#FFFFFF" />
      <path d={chemin} fill="#121212" />
    </svg>
  );
}

function dateEtHeure(iso: string): string {
  const d = new Date(iso);
  const deux = (n: number) => String(n).padStart(2, "0");
  return `${deux(d.getDate())}/${deux(d.getMonth() + 1)}/${d.getFullYear()} ${deux(d.getHours())}:${deux(d.getMinutes())}`;
}

/** Le reçu de la visite, à imprimer sur papier thermique 80 mm, noir seul : numéro, QR, posologie, code carnet. */
export function RecuImprimable({
  recu,
  catalogue,
  patientId,
  adresseDuCarnet,
}: {
  recu: Recu;
  catalogue: Catalogue;
  patientId: string;
  adresseDuCarnet: string;
}) {
  const libelles = new Map(catalogue.produits.map((p) => [p.code, p.libelle]));
  return (
    <div className="sn-recu-ecran">
      <div className="sn-recu-actions">
        <Alert tone="succes" title="Visite enregistrée.">
          Imprimez le reçu et remettez-le au patient{recu.numero ? " : il le montre à la caisse, puis à la pharmacie." : "."}
        </Alert>
        <div className="sn-actions">
          <Button size="pro" icon="printer" onClick={() => window.print()}>
            Imprimer le reçu
          </Button>
          <Button href={adresseDuPatient(patientId, "/cas")} size="pro" variant="secondary" icon="eye">
            Voir le dossier
          </Button>
          <Button href="/" size="pro" variant="ghost" icon="magnifying-glass">
            Patient suivant
          </Button>
        </div>
        {!recu.code && (
          <Alert tone="attention" title="Le code carnet n’a pas été émis.">
            identite n’a pas répondu : le patient garde son code précédent.
          </Alert>
        )}
      </div>

      <article className="sn-papier" aria-label="Reçu imprimé">
        <Logo tone="noir" height={34} />
        <div className="sn-petit">
          {recu.etablissement}
          <br />
          {`${dateEtHeure(recu.date)} · ${recu.soignant}`}
          <br />
          {recu.patient}
        </div>
        {recu.numero && (
          <>
            <div className="sn-trait" />
            <div className="sn-petit sn-centre sn-gras">N° D’ORDONNANCE</div>
            <div className="sn-numero">{recu.numero}</div>
            <div className="sn-qr-ligne">
              <Qr texte={recu.numero} />
              <div className="sn-petit">Montrez ce reçu à la caisse, puis à la pharmacie.</div>
            </div>
            <div className="sn-trait" />
            {recu.lignes.map((l, i) => (
              <div key={i} className="sn-pligne">
                <b>{libelles.get(l.produit) ?? l.produit}</b>
                {l.produit.startsWith("MED-") ? (
                  <div className="sn-pictos">
                    <Posology count={l.dose} moments={l.moments} days={l.jours} size={30} />
                  </div>
                ) : null}
                <div className="sn-petit">{`Quantité : ${l.quantite}${l.unite ? ` ${l.unite}` : ""}`}</div>
              </div>
            ))}
          </>
        )}
        {recu.code && (
          <>
            <div className="sn-trait" />
            <div className="sn-code">
              <div className="sn-petit sn-gras">CODE CARNET</div>
              <span>{recu.code}</span>
            </div>
            <div className="sn-petit sn-centre">
              {"Votre carnet : "}
              <b className="lf-mono">{adresseDuCarnet}</b>
            </div>
          </>
        )}
      </article>
    </div>
  );
}
