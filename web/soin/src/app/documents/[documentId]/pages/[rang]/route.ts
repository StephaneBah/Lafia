import { lirePage } from "../../../../../lib/soin";

// Une page d'un Document, relayée au navigateur : l'application la lit au service soin avec la session
// du soignant (le service exige la relation de soin et trace la lecture), puis en rend les octets.

const ID = /^[A-Za-z0-9.-]{1,64}$/;
const FORMATS = new Set(["image/jpeg", "image/png", "application/pdf"]);

export async function GET(_: Request, { params }: { params: Promise<{ documentId: string; rang: string }> }) {
  const { documentId, rang } = await params;
  const n = Number(rang);
  if (!ID.test(documentId) || !Number.isInteger(n) || n < 1 || n > 20) return new Response(null, { status: 404 });

  const reponse = await lirePage(documentId, n);
  const format = (reponse.headers.get("content-type") ?? "").split(";")[0].trim();
  if (!reponse.ok || !FORMATS.has(format)) return new Response(null, { status: reponse.ok ? 502 : reponse.status });
  return new Response(reponse.body, {
    status: 200,
    headers: {
      "Content-Type": format,
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
      // Un PDF s'ouvre dans l'onglet, jamais enregistré sans le vouloir.
      "Content-Disposition": `inline; filename="page-${n}${format === "application/pdf" ? ".pdf" : format === "image/png" ? ".png" : ".jpg"}"`,
    },
  });
}
