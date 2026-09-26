import { NextResponse, type NextRequest } from "next/server";

import { adressePasserelle, COOKIE_DE_RENOUVELLEMENT, COOKIE_DE_SESSION, DELAI_MS } from "./service";

/**
 * Renouvelle un jeton expiré avant de rendre la page (ADR 0004), sans jamais lire le jeton.
 *
 * Le navigateur laisse tomber le cookie du jeton à son expiration, et garde celui de la session.
 * Le serveur de l'application demande alors un nouveau jeton à identite, par l'entrée interne de la
 * passerelle, puis renvoie le navigateur à la même adresse avec les cookies qu'identite a posés.
 * Quand la session est finie, identite les efface, et la page se rend sans session.
 * Chaque application l'appelle depuis son `proxy.ts`, avant chacune de ses pages.
 */
export async function renouvelerLaSession(requete: NextRequest): Promise<NextResponse> {
  const identifiantDeSession = requete.cookies.get(COOKIE_DE_RENOUVELLEMENT)?.value;
  const aRenouveler =
    ["GET", "HEAD"].includes(requete.method) && !requete.cookies.has(COOKIE_DE_SESSION) && identifiantDeSession;
  if (!aRenouveler) return NextResponse.next();

  let reponse: Response;
  try {
    reponse = await fetch(`${adressePasserelle()}/api/identite/session/renouveler`, {
      method: "POST",
      cache: "no-store",
      headers: { Cookie: `${COOKIE_DE_RENOUVELLEMENT}=${identifiantDeSession}` },
      signal: AbortSignal.timeout(DELAI_MS),
    });
  } catch (erreur) {
    console.warn("identite injoignable : jeton non renouvelé", erreur);
    return NextResponse.next();
  }
  // La même adresse : Next.js la rend relative, puisqu'elle a l'origine de la requête.
  const suite = reponse.status === 204 ? NextResponse.redirect(requete.nextUrl, 303) : NextResponse.next();
  for (const cookie of reponse.headers.getSetCookie()) {
    suite.headers.append("Set-Cookie", cookie);
  }
  return suite;
}
