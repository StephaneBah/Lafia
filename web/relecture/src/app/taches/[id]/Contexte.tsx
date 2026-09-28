// Ce qui se lit avant la Transcription : la lecture de démonstration, les notes d'un Contrôle, le rappel
// du pseudonymat, le texte brut lu par la machine. Sans état : rendu au serveur comme au navigateur.
import { dateEnLettres } from "@lafia/commun/transcription";
import { Alert, Icon } from "@lafia/design";

import type { Modele, NoteDeControle } from "../../../types";

export function Contexte({
  modele,
  notes,
  renvoyee,
  texte,
  consigne,
}: {
  modele: Modele | null;
  notes: NoteDeControle[];
  renvoyee?: boolean;
  texte: string | null;
  consigne: "relecture" | "controle" | "validation";
}) {
  return (
    <div className="rel-contexte">
      {notes.length > 0 && consigne === "relecture" && (
        <Alert
          tone="attention"
          title={renvoyee ? "Le Contrôle vous renvoie cette Transcription." : "Notes d'un Contrôle précédent"}
        >
          <ul className="rel-notes">
            {notes.map((note, i) => (
              <li key={`${note.date}-${i}`}>
                {note.date && <span className="rel-meta">{`${dateEnLettres(note.date.slice(0, 10))} · `}</span>}
                <span>{note.texte}</span>
              </li>
            ))}
          </ul>
          <p className="rel-meta">Reprenez ce qui est signalé, revérifiez les volets concernés, puis confirmez à nouveau.</p>
        </Alert>
      )}

      {modele?.demonstration && (
        <Alert tone="attention" title={`Lecture de démonstration — modèle ${modele.nom} ${modele.version}`}>
          {consigne === "validation"
            ? "Ces propositions ne viennent pas d'une vraie lecture de la page : comparez chacune avec la page avant de l'accepter."
            : consigne === "controle"
              ? "Le brouillon de départ ne venait pas d'une vraie lecture des pages. Seules les pages font foi : contrôlez chaque volet contre elles."
              : "Ce brouillon ne vient pas d'une vraie lecture des pages : il sert à montrer le travail. Tout ce qui compte est ce que vous lisez sur les pages."}
        </Alert>
      )}

      <p className="rel-pseudonymat">
        <Icon name="shield-check" size={22} />
        <span>Vous ne voyez pas qui est le patient. Si une page montre un nom, n'en faites rien.</span>
      </p>

      {texte && (
        <details className="rel-texte">
          <summary>{modele ? `Texte brut lu par la machine (${modele.nom} ${modele.version})` : "Texte brut lu par la machine"}</summary>
          <pre>{texte}</pre>
        </details>
      )}
    </div>
  );
}
