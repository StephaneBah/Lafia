import { Picto, StatusBadge, formatNpi } from "@lafia/design";
import type { ReactNode } from "react";

import { age, initiales, type Allergie, type Patient } from "../lib/types";

/** Nom, âge, sexe et NPI du patient, avec ses actions à droite. */
export function EnTetePatient({ patient, npi, children }: { patient: Patient; npi: string; children?: ReactNode }) {
  const ans = age(patient.naissance);
  return (
    <div className="sn-tete">
      <div className="sn-avatar" aria-hidden="true">
        {initiales(patient)}
      </div>
      <div>
        <div className="sn-nom">
          {`${patient.prenoms} ${patient.nom}`}
          {ans !== null && ` · ${ans} ans`}
          {patient.sexe && ` · ${patient.sexe}`}
        </div>
        <div className="sn-meta">
          <span className="lf-mono">{formatNpi(npi)}</span>
        </div>
      </div>
      <span className="sn-espace" />
      {children}
    </div>
  );
}

/** Les allergies d'abord : cadre rouge, pictogramme et mot ; ou la mention qu'aucune n'est connue. */
export function Allergies({ allergies }: { allergies: Allergie[] }) {
  if (allergies.length === 0) {
    return <p className="sn-meta">Aucune allergie déclarée.</p>;
  }
  return (
    <div className="sn-allergie" role="note">
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
