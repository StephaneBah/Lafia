// Une page d'un Document, relayée au navigateur par le serveur d'une application (soin, citoyen) :
// l'application la lit à son service, par la passerelle, avec la session de l'utilisateur (le service
// vérifie ses droits et trace la lecture), puis en rend les octets. Côté serveur seulement.
import { cookies } from "next/headers";

import { adressePasserelle, COOKIE_DE_SESSION } from "./service";

const ID = /^[A-Za-z0-9.-]{1,64}$/;
const PAGES_MAX = 20;
const DELAI_DES_PAGES_MS = 30_000;
const EXTENSIONS: Record<string, string> = { "image/jpeg": ".jpg", "image/png": ".png", "application/pdf": ".pdf" };

/**
 * La page `rang` du Document `documentId`, lue à `GET /api/<service>/documents/<id>/pages/<rang>`.
 * 404 pour un identifiant ou un rang mal formé, le statut du service quand il refuse, 502 quand il
 * rend autre chose qu'un JPEG, un PNG ou un PDF, 503 quand la passerelle ne répond pas.
 */
export async function servirUnePage(service: string, documentId: string, rang: string): Promise<Response> {
  const n = Number(rang);
  if (!ID.test(documentId) || !Number.isInteger(n) || n < 1 || n > PAGES_MAX) return new Response(null, { status: 404 });

  const jeton = (await cookies()).get(COOKIE_DE_SESSION)?.value;
  if (!jeton) return new Response(null, { status: 401 });
  let reponse: Response;
  try {
    reponse = await fetch(`${adressePasserelle()}/api/${service}/documents/${encodeURIComponent(documentId)}/pages/${n}`, {
      cache: "no-store",
      headers: { Cookie: `${COOKIE_DE_SESSION}=${jeton}` },
      signal: AbortSignal.timeout(DELAI_DES_PAGES_MS),
    });
  } catch (erreur) {
    console.warn(`passerelle injoignable : /api/${service}/documents`, erreur);
    return new Response(null, { status: 503 });
  }

  const format = (reponse.headers.get("content-type") ?? "").split(";")[0].trim();
  if (!reponse.ok || !(format in EXTENSIONS)) return new Response(null, { status: reponse.ok ? 502 : reponse.status });
  return new Response(reponse.body, {
    status: 200,
    headers: {
      "Content-Type": format,
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
      // Un PDF s'ouvre dans l'onglet, jamais enregistré sans le vouloir.
      "Content-Disposition": `inline; filename="page-${n}${EXTENSIONS[format]}"`,
    },
  });
}
