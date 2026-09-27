import { Alert, Button, Icon, Picto, StatusBadge, type NomPictogramme } from "@lafia/design";
import { connection } from "next/server";
import type { ReactNode } from "react";

import { Cadre, CarnetNonLu, Scene } from "../composants/cadre";
import { EtatDuService } from "../composants/EtatDuService";
import { LIBELLES_DES_MOMENTS, lire, quand, type Accueil, type StatutDeLigne } from "../lib/carnet";

/** Les pictogrammes de l'état d'une ordonnance : d'où l'on vient, où l'on en est. */
const PICTOS_D_ETAT: Record<StatutDeLigne, NomPictogramme[]> = {
  apayer: ["a-payer"],
  paye: ["paye"],
  aretirer: ["paye", "a-retirer"],
  partiel: ["paye", "retire-partie"],
  retire: ["paye", "retire"],
};

function Tuile({ href, marque, titre, detail }: { href: string; marque: ReactNode; titre: string; detail: string }) {
  return (
    <a className="carnet-tuile" href={href}>
      <span className="carnet-tuile-marque">{marque}</span>
      <span>
        {titre}
        <small>{detail}</small>
      </span>
      <Icon name="arrow-left" size={22} className="carnet-aller" />
    </a>
  );
}

function CarnetDuCitoyen({ carnet }: { carnet: Accueil }) {
  const { ordonnance, cas_recent: cas, prochain_moment: moment } = carnet;
  const vide = !ordonnance && !cas;
  return (
    <>
      <div>
        <h1 className="carnet-titre">{`Bonjour ${carnet.prenom}`}</h1>
        <p className="carnet-doux">{vide ? "Bienvenue dans votre carnet." : "Voici où vous en êtes."}</p>
      </div>

      {vide ? (
        <Scene illustration="citoyen-bienvenue" titre="Votre carnet est prêt.">
          <p className="carnet-doux">Après votre prochaine visite, vos soins, vos ordonnances et votre traitement apparaîtront ici.</p>
        </Scene>
      ) : (
        ordonnance && (
          <section className="carnet-etat-hero" aria-label="Mon ordonnance en cours">
            <div className="carnet-pictos" aria-hidden="true">
              {PICTOS_D_ETAT[ordonnance.statut].map((picto, i) => (
                <span key={picto} className="carnet-pictos">
                  {i > 0 && <Icon name="arrow-left" size={28} className="carnet-aller" />}
                  <Picto name={picto} size={56} decorative />
                </span>
              ))}
            </div>
            <StatusBadge status={ordonnance.statut} size="large" />
            <p className="carnet-grand">{ordonnance.message}</p>
            <Button href="/ordonnance" icon="receipt" size="citizen" block>
              Voir mon ordonnance
            </Button>
          </section>
        )
      )}

      {carnet.allergies.length > 0 && (
        <Alert tone="allergie" title={`Allergie : ${carnet.allergies.join(", ")}`}>
          Dites-le à chaque soignant et au pharmacien.
        </Alert>
      )}

      <nav className="carnet-tuiles" aria-label="Mon carnet">
        <Tuile
          href="/traitement"
          marque={<Picto name={moment ?? "matin"} size={44} decorative />}
          titre="Mon traitement"
          detail={
            moment
              ? `${LIBELLES_DES_MOMENTS[moment]} : ${carnet.prises_au_prochain_moment} ${carnet.prises_au_prochain_moment > 1 ? "médicaments" : "médicament"}`
              : "Rien d'autre à prendre aujourd'hui"
          }
        />
        <Tuile
          href={cas ? `/cas/${encodeURIComponent(cas.id)}` : "/cas"}
          marque={<Icon name="heartbeat" size={36} />}
          titre={cas?.en_cours ? "Mon cas en cours" : "Mes cas"}
          detail={cas ? `${cas.motif} · ${cas.visites} ${cas.visites > 1 ? "visites" : "visite"}` : "Aucun cas pour le moment"}
        />
        <Tuile
          href="/ordonnance"
          marque={<Icon name="receipt" size={36} />}
          titre="Mes ordonnances"
          detail={ordonnance ? `${ordonnance.numero} · ${quand(ordonnance.date, false)}` : "Aucune ordonnance"}
        />
        <Tuile
          href="/ma-sante"
          marque={<Icon name="shield-check" size={36} />}
          titre="Ma santé"
          detail="Groupe sanguin, allergies, maladies, médicaments de tous les jours"
        />
        <Tuile
          href="/documents"
          marque={<Icon name="copy" size={36} />}
          titre="Mes documents"
          detail="Vos anciens papiers, numérisés"
        />
        <Tuile
          href="/par-etablissement"
          marque={<Icon name="hospital" size={36} />}
          titre="Par établissement"
          detail="Vos anciens papiers relus, lieu par lieu"
        />
        <Tuile
          href="/acces"
          marque={<Picto name="consultation" size={44} decorative />}
          titre="Qui a ouvert mon dossier"
          detail={carnet.dernier_acces ? `Dernière fois : ${quand(carnet.dernier_acces.date)}` : "Personne d'autre que vous"}
        />
      </nav>
    </>
  );
}

export default async function Accueil() {
  // Rendu à chaque requête : le carnet du moment, jamais celui de la construction.
  await connection();
  const lecture = await lire<Accueil>("/carnet");
  const connecte = lecture.etat !== "sans-session";

  return (
    <Cadre connecte={connecte}>
      {lecture.etat === "lu" ? (
        <CarnetDuCitoyen carnet={lecture.valeur} />
      ) : lecture.etat === "sans-session" ? (
        <>
          <h1 className="carnet-titre">Mon carnet de santé</h1>
          <Scene illustration="citoyen-bienvenue" titre="Vos soins vous suivent, d'un centre de santé à l'autre.">
            <p className="carnet-doux">Ouvrez-le avec votre NPI et le code carnet imprimé sur votre reçu.</p>
            <Button href="/connexion" icon="lock-simple" size="citizen" block>
              Se connecter
            </Button>
          </Scene>
        </>
      ) : (
        <CarnetNonLu lecture={lecture} />
      )}
      <EtatDuService connecte={connecte} />
    </Cadre>
  );
}
