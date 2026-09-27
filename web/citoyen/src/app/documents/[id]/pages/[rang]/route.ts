import { lirePage } from "../../../../../lib/carnet";

// Une page d'un de mes documents, relayée au navigateur : l'application la lit au service citoyen
// avec la session du citoyen (qui ne voit que les siens, lecture tracée), puis en rend les octets.

const ID = /^[A-Za-z0-9.-]{1,64}$/;
const FORMATS = new Set(["image/jpeg", "image/png", "application/pdf"]);

export async function GET(_: Request, { params }: { params: Promise<{ id: string; rang: string }> }) {
  const { id, rang } = await params;
  const n = Number(rang);
  if (!ID.test(id) || !Number.isInteger(n) || n < 1 || n > 20) return new Response(null, { status: 404 });

  const reponse = await lirePage(id, n);
  const format = (reponse.headers.get("content-type") ?? "").split(";")[0].trim();
  if (!reponse.ok || !FORMATS.has(format)) return new Response(null, { status: reponse.ok ? 502 : reponse.status });
  return new Response(reponse.body, {
    status: 200,
    headers: {
      "Content-Type": format,
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
      "Content-Disposition": `inline; filename="page-${n}${format === "application/pdf" ? ".pdf" : format === "image/png" ? ".png" : ".jpg"}"`,
    },
  });
}
