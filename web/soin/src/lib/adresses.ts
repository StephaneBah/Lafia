/** L'adresse d'un écran de l'espace patient : par l'id de sa ressource Patient, jamais par son NPI. */
export function adresseDuPatient(patientId: string, suite = ""): string {
  return `/patients/${encodeURIComponent(patientId)}${suite}`;
}
