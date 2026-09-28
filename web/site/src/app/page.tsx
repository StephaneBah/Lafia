import { Button, Icon, ORDRE_DES_ACTEURS, ServiceCard, SiteFooter, SiteHeader, SoonCard, adresse, type Acteur } from "@lafia/design";
import { Illustration, type NomIllustration } from "@lafia/design/illustration";
import { connection } from "next/server";
import type { ReactNode } from "react";

import { Parcours } from "./Parcours";

const PROBLEMES: Array<[NomIllustration, string]> = [
  ["probleme-carnet", "Le carnet papier se perd."],
  ["probleme-registres", "Chaque établissement tient son propre registre."],
  ["probleme-exemplaire", "Le résultat d'analyse n'existe qu'en un exemplaire."],
  ["probleme-interpretations", "Sans l'historique, chaque médecin interprète les maux du patient à sa manière."],
];

const PILIERS: Array<{ illustration: NomIllustration; titre: string; texte: string; badge?: string }> = [
  {
    illustration: "pilier-memoire",
    titre: "Une mémoire commune, une porte par métier.",
    texte:
      "Toutes les données médicales vivent en un seul endroit. Soignant, caissière, pharmacien, citoyen : chacun entre par sa propre porte et ne voit que ce dont son métier a besoin. La caissière voit une ordonnance et ses montants, jamais le diagnostic.",
  },
  {
    illustration: "pilier-interoperable",
    titre: "Interopérable dès le premier jour.",
    texte:
      "Lafia parle la langue internationale des données de santé. Un laboratoire, une officine ou un service de télémédecine s'y branche sans rien reconstruire et sans copier les données. Lafia n'est lié à aucun fournisseur : il peut être hébergé sur l'infrastructure numérique de l'État. Le dossier appartient au patient, pas à un logiciel.",
    badge: "Standard international HL7 FHIR",
  },
  {
    illustration: "pilier-securite",
    titre: "La sécurité se voit.",
    texte:
      "Un soignant n'ouvre un dossier que s'il soigne ce patient. L'urgence vitale reste possible, avec un motif déclaré. Chaque ouverture du dossier est tracée, et le citoyen voit lui-même qui l'a ouvert, et quand.",
  },
  {
    illustration: "pilier-sans-lire",
    titre: "Compris sans savoir lire.",
    texte: "Le carnet se lit en images : ce qui est payé, ce qui reste à retirer, quand prendre chaque médicament.",
  },
];

const ETAPES: Array<{ illustration: NomIllustration; lieu: string; texte: ReactNode }> = [
  {
    illustration: "parcours-1-centre",
    lieu: "Centre de santé",
    texte: (
      <>
        Le soignant retrouve Awa par son NPI, ouvre un cas, écrit la visite et <strong>émet l'ordonnance</strong>.
      </>
    ),
  },
  {
    illustration: "parcours-2-recu",
    lieu: "Le reçu",
    texte: (
      <>
        Awa reçoit son reçu : <strong>le numéro d'ordonnance</strong>, son QR code et son code carnet.
      </>
    ),
  },
  {
    illustration: "parcours-3-caisse",
    lieu: "Caisse",
    texte: (
      <>
        La caissière saisit le numéro. Les lignes arrivent avec leur tarif ; <strong>rien n'est retapé</strong>.
      </>
    ),
  },
  {
    illustration: "parcours-4-pharmacie",
    lieu: "Pharmacie",
    texte: (
      <>
        Le pharmacien voit les lignes payées et <strong>les allergies avant de remettre</strong>.
      </>
    ),
  },
  {
    illustration: "parcours-5-telephone",
    lieu: "Le carnet",
    texte: (
      <>
        Sur le téléphone de son fils, Awa voit ce qu'elle a payé, retiré, et <strong>comment prendre son traitement</strong>.
      </>
    ),
  },
];

const SERVICES: Record<Acteur, { illustration: NomIllustration; pourQui: string; description: string; points: string[] }> = {
  citoyen: {
    illustration: "acteur-citoyen",
    pourQui: "Pour les citoyens",
    description: "Son dossier dans sa poche, lisible sans savoir lire.",
    points: [
      "Ce qui est payé, ce qui reste à retirer, quand prendre chaque médicament.",
      "Ses antécédents, ses papiers numérisés, son histoire par établissement.",
      "Qui a ouvert son dossier, et quand.",
    ],
  },
  soin: {
    illustration: "acteur-soignant",
    pourQui: "Pour les médecins et infirmiers",
    description: "Tout le patient sur un seul écran, retrouvé par son NPI.",
    points: [
      "Allergies, antécédents et traitements toujours en vue.",
      "Le cas de visite relie visites, analyses et ordonnances.",
      "Le passé papier du patient, relu, à côté de ses pages.",
    ],
  },
  caisse: {
    illustration: "acteur-caissiere",
    pourQui: "Pour les caissiers",
    description: "Un numéro saisi ou scanné, et l'ordonnance arrive tarifée.",
    points: ["Rien n'est retapé.", "Le patient paie ce qu'il peut aujourd'hui, le reste attend.", "Les montants, jamais le diagnostic."],
  },
  pharmacie: {
    illustration: "acteur-pharmacien",
    pourQui: "Pour les pharmacies et les officines",
    description: "Remettre les bons médicaments, en sécurité.",
    points: [
      "Les lignes payées, et rien d'autre.",
      "Une allergie arrête la remise tant qu'elle n'est pas vue.",
      "Une délivrance partielle est normale : le reste est à retirer plus tard.",
    ],
  },
  numerisation: {
    illustration: "probleme-carnet",
    pourQui: "Pour les agents de numérisation",
    description: "Le passé papier d'un citoyen entre dans son dossier, en une seule venue.",
    points: ["L'identité vérifiée avant tout document.", "Chaque page contrôlée : netteté, cadrage, lumière.", "Le citoyen repart avec ses papiers."],
  },
  relecture: {
    illustration: "probleme-registres",
    pourQui: "Pour les agents de relecture et les soignants",
    description: "Des scans aux récits fiables, relus par des humains.",
    points: [
      "Les pages à gauche, la transcription à droite, volet par volet.",
      "Double confirmation, puis le contrôle d'un second relecteur.",
      "Sans jamais savoir de qui est le dossier.",
    ],
  },
};

const DEMAIN: Array<{ illustration: NomIllustration; icone: "video-camera" | "chart-line" | "microphone" | "test-tube"; titre: string; accroche: string; texte: string }> = [
  {
    illustration: "demain-telemedecine",
    icone: "video-camera",
    titre: "Télémédecine",
    accroche: "Consulter à distance.",
    texte:
      "Une visite par vidéo ou par téléphone, rangée dans le même cas de visite : le spécialiste de Cotonou suit le patient de Kandi sans qu'il fasse le voyage.",
  },
  {
    illustration: "demain-insights",
    icone: "chart-line",
    titre: "Lafia Insights",
    accroche: "Décider sur des données fiables.",
    texte:
      "Des tableaux de suivi pour les institutions de décision, le ministère et l'ARS : épidémies, couverture des soins, parcours des patients. Ils sont calculés sur des données anonymisées, jamais sur le dossier des patients.",
  },
  {
    illustration: "demain-assistant",
    icone: "microphone",
    titre: "Assistant IA de compte rendu",
    accroche: "Moins de saisie, plus de soin.",
    texte:
      "Le soignant dicte ou note librement ; l'assistant prépare le compte rendu de la visite et propose la mise à jour du dossier (mesures, diagnostic, ordonnance). Rien n'est enregistré sans la validation du soignant.",
  },
  {
    illustration: "demain-laboratoire",
    icone: "test-tube",
    titre: "Laboratoire",
    accroche: "Les résultats arrivent seuls.",
    texte: "Le laboratoire dépose ses résultats directement dans le cas de visite, sans papier.",
  },
];

export default async function Accueil() {
  // Le domaine n'est connu qu'au démarrage du conteneur : localhost en local.
  await connection();
  const domaine = process.env.LAFIA_DOMAINE || "localhost";
  const carnet = adresse(domaine, "citoyen");

  return (
    <>
      <a className="lf-skip" href="#main">
        Aller au contenu
      </a>
      <SiteHeader ctaHref={carnet} animateLogo />

      <main id="main" className="site">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="wrap">
            <div className="hero-text">
              <h1 id="hero-title">Votre dossier de santé vous suit, partout au Bénin.</h1>
              <p className="lead">
                Avec votre seul NPI, chaque soignant retrouve votre histoire médicale, d'un centre de santé à l'autre, de la
                caisse à la pharmacie.
              </p>
              <div className="hero-actions">
                <Button href={carnet} icon="identification-card">
                  Ouvrir mon carnet
                </Button>
                <Button href="#services" variant="secondary">
                  Je suis un professionnel
                </Button>
              </div>
            </div>
            <div className="illu hero-illu">
              <Illustration name="site-heros" />
            </div>
          </div>
        </section>

        <section className="today" aria-labelledby="today-title">
          <div className="wrap">
            <div className="sec-head">
              <span className="eyebrow">Aujourd'hui</span>
              <h2 className="h-display" id="today-title">
                Aujourd'hui, la mémoire médicale est éparpillée.
              </h2>
            </div>
            <div className="cards3">
              {PROBLEMES.map(([illustration, texte]) => (
                <article key={illustration} className="pcard">
                  <div className="illu">
                    <Illustration name={illustration} decorative />
                  </div>
                  <p>{texte}</p>
                </article>
              ))}
            </div>
            <p className="closing">
              Le patient est <b>le seul lien</b> entre ses soignants.
            </p>
          </div>
        </section>

        <section id="vision" aria-labelledby="vision-title">
          <div className="wrap">
            <div className="sec-head">
              <span className="eyebrow">La vision</span>
              <h2 className="h-display" id="vision-title">
                Une personne, un dossier, dans tout le pays.
              </h2>
            </div>
            <div className="vision-grid">
              <article className="vpoint">
                <span className="vicon">
                  <Icon name="identification-card" size={28} />
                </span>
                <h3>Le NPI suffit</h3>
                <p>Pas de nouveau numéro, pas de carte à créer.</p>
              </article>
              <article className="vpoint">
                <span className="vicon">
                  <Icon name="heartbeat" size={28} />
                </span>
                <h3>Chaque problème de santé, du début à la fin</h3>
                <p>Le cas de visite relie les visites, les analyses et les ordonnances, même d'un établissement à l'autre.</p>
              </article>
              <article className="vpoint">
                <span className="vicon">
                  <Icon name="eye" size={28} />
                </span>
                <h3>Le citoyen voit son carnet</h3>
                <p>Ce qu'il doit payer, retirer et prendre, et qui a ouvert son dossier.</p>
              </article>
            </div>
          </div>
        </section>

        <section id="comment" aria-labelledby="comment-title" className="sans-haut">
          <div className="wrap">
            <div className="sec-head">
              <span className="eyebrow">Comment nous l'avons pensé</span>
              <h2 className="h-display" id="comment-title">
                Quatre choix qui changent tout pour le patient.
              </h2>
            </div>
            <div className="pillars">
              {PILIERS.map((pilier) => (
                <article key={pilier.illustration} className="pillar">
                  <div className="illu">
                    <Illustration name={pilier.illustration} decorative />
                  </div>
                  <div className="pillar-text">
                    <h3>{pilier.titre}</h3>
                    <p>{pilier.texte}</p>
                    {pilier.badge && <span className="tech-badge">{pilier.badge}</span>}
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="journey-sec" aria-labelledby="journey-title" id="parcours">
          <div className="wrap">
            <div className="sec-head">
              <span className="eyebrow">Un parcours, zéro ressaisie</span>
              <h2 className="h-display" id="journey-title">
                Un numéro suit Awa d'un bout à l'autre.
              </h2>
              <p className="lead">
                L'ordonnance <span className="lf-mono">ORD-7K4-M2P</span> est écrite une fois. Ensuite, personne ne la retape.
              </p>
            </div>
            <Parcours numero="ORD-7K4-M2P">
              {ETAPES.map((etape, i) => (
                <li key={etape.illustration} className={i === 0 ? "jstep is-awake" : "jstep"}>
                  <span className="jnode" aria-hidden="true" />
                  <div className="illu">
                    <Illustration name={etape.illustration} decorative />
                  </div>
                  <span className="jnum">{`Étape ${i + 1} · ${etape.lieu}`}</span>
                  <p>{etape.texte}</p>
                </li>
              ))}
            </Parcours>
          </div>
        </section>

        <section id="services" aria-labelledby="services-title">
          <div className="wrap">
            <div className="sec-head">
              <span className="eyebrow">Les services ouverts aujourd'hui</span>
              <h2 className="h-display" id="services-title">
                Une porte par métier.
              </h2>
              <p className="lead">Chaque métier a son application, à sa propre adresse. Un compte n'ouvre que la sienne : c'est voulu.</p>
            </div>
            <div className="services-grid">
              {ORDRE_DES_ACTEURS.map((acteur) => (
                <ServiceCard
                  key={acteur}
                  actor={acteur}
                  domaine={domaine}
                  forWhom={SERVICES[acteur].pourQui}
                  description={SERVICES[acteur].description}
                  illustration={<Illustration name={SERVICES[acteur].illustration} decorative />}
                  points={SERVICES[acteur].points}
                />
              ))}
            </div>
          </div>
        </section>

        <section className="tomorrow" id="demain" aria-labelledby="demain-title">
          <div className="wrap">
            <div className="sec-head">
              <span className="eyebrow">Demain</span>
              <h2 className="h-display" id="demain-title">
                La plateforme grandit sans être reconstruite.
              </h2>
            </div>
            <div className="soon-grid">
              {DEMAIN.map((service) => (
                <SoonCard
                  key={service.titre}
                  title={service.titre}
                  tagline={service.accroche}
                  icon={service.icone}
                  illustration={
                    <div className="illu">
                      <Illustration name={service.illustration} decorative />
                    </div>
                  }
                >
                  {service.texte}
                </SoonCard>
              ))}
            </div>
            <p className="closing">
              Chaque nouveau service se branche sur <b>le même dossier</b>, sans rien reconstruire.
            </p>
          </div>
        </section>
      </main>

      <SiteFooter domaine={domaine} />
    </>
  );
}
