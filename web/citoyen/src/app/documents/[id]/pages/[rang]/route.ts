import { servirUnePage } from "@lafia/commun/pages";

// Une page d'un de mes documents, relayée au navigateur : lue au service citoyen avec la session du
// citoyen (qui ne voit que les siens, lecture tracée).
export async function GET(_: Request, { params }: { params: Promise<{ id: string; rang: string }> }) {
  const { id, rang } = await params;
  return servirUnePage("citoyen", id, rang);
}
