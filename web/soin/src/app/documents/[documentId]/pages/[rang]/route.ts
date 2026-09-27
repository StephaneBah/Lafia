import { servirUnePage } from "@lafia/commun/pages";

// Une page d'un Document, relayée au navigateur : lue au service soin avec la session du soignant (le
// service exige la relation de soin et trace la lecture).
export async function GET(_: Request, { params }: { params: Promise<{ documentId: string; rang: string }> }) {
  const { documentId, rang } = await params;
  return servirUnePage("soin", documentId, rang);
}
