import { Icon, Picto, StatusBadge } from "@lafia/design";

import { age, initiales, libelleDuLien, npiMasque, type Allergie, type Bandeau } from "../lib/types";

/** Les allergies d'abord : cadre rouge, pictogramme et mot ; ou la mention qu'aucune n'est connue. */
export function Allergies({ allergies }: { allergies: Allergie[] }) {
  if (allergies.length === 0) {
    return (
      <p className="sn-meta sn-sans-allergie">
        <Icon name="check" size={16} />
        Aucune allergie déclarée.
      </p>
    );
  }
  return (
    <div className="sn-allergie" role="note" aria-label="Allergies">
      <b>
        <Picto name="allergie" size={24} decorative />
        {`Allergie : ${allergies.map((a) => a.libelle).join(", ")}`}
      </b>
      <span className="sn-badges">
        {allergies.map((a) => (
          <StatusBadge key={a.id} status="allergie" size="pro" label={a.code_atc ? `${a.libelle} (${a.code_atc})` : a.libelle} />
        ))}
      </span>
    </div>
  );
}

/**
 * Le bandeau patient, présent sur chaque écran de l'espace patient : qui est ce patient, ce qui peut le
 * sauver (allergies, groupe sanguin), puis, avec une relation de soin, ses antécédents et traitements.
 */
export function BandeauPatient({ bandeau }: { bandeau: Bandeau }) {
  const { patient, groupe_sanguin, allergies, antecedents, familiaux, traitements, relation_de_soin } = bandeau;
  const ans = patient.age ?? age(patient.naissance);
  const actifs = (antecedents ?? []).filter((a) => a.actif);
  return (
    <section className="sn-bandeau lf-card" aria-label="Bandeau patient">
      <div className="sn-bandeau-identite">
        <div className="sn-avatar" aria-hidden="true">
          {initiales(patient)}
        </div>
        <div>
          <h1 className="sn-nom">{`${patient.prenoms} ${patient.nom}`}</h1>
          <div className="sn-meta">
            {[patient.sexe, ans !== null ? `${ans} ans` : null].filter(Boolean).join(" · ")}
            {patient.npi && (
              <>
                {" · NPI "}
                <span className="lf-mono">{npiMasque(patient.npi)}</span>
              </>
            )}
          </div>
        </div>
        <span className="sn-espace" />
        <div className="sn-groupe" aria-label={`Groupe sanguin : ${groupe_sanguin ?? "inconnu"}`}>
          <span className="sn-groupe-titre">Groupe sanguin</span>
          <strong>{groupe_sanguin ?? "Inconnu"}</strong>
        </div>
      </div>

      <Allergies allergies={allergies} />

      {relation_de_soin && (
        <dl className="sn-bandeau-histoire">
          <div>
            <dt>Antécédents</dt>
            <dd>
              {actifs.length === 0 && (familiaux ?? []).length === 0
                ? "Aucun déclaré"
                : [
                    ...actifs.map((a) => a.libelle),
                    ...(familiaux ?? []).map((f) => `${f.libelle} (${libelleDuLien(f.lien).toLowerCase()})`),
                  ].join(" · ")}
            </dd>
          </div>
          <div>
            <dt>Traitements au long cours</dt>
            <dd>
              {(traitements ?? []).length === 0
                ? "Aucun"
                : (traitements ?? []).map((t) => (
                    <span key={t.id} className="sn-traitement-court">
                      <Icon name="pill" size={16} />
                      <b>{t.libelle}</b>
                      {t.posologie && ` · ${t.posologie}`}
                    </span>
                  ))}
            </dd>
          </div>
        </dl>
      )}
    </section>
  );
}
