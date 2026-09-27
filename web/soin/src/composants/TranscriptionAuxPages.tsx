"use client";

import { Icon } from "@lafia/design";
import { MENTION_PATRIMONIALE, RenduDeTranscription, lireTranscription } from "@lafia/commun/transcription";
import { useRouter } from "next/navigation";

/**
 * La Transcription relue d'un Document (ADR 0010), rendue à côté de ses pages. Toucher les pages d'un
 * volet ou une photo montre cette page dans la visionneuse. Les images passent par la route de page de
 * l'application, comme les pages elles-mêmes : relation de soin exigée, lecture tracée.
 */
export function TranscriptionAuxPages({ documentId, markdown, pages }: { documentId: string; markdown: string; pages: number }) {
  const router = useRouter();
  const transcription = lireTranscription(markdown, pages);
  const urlDePage = (n: number) => `/documents/${encodeURIComponent(documentId)}/pages/${n}`;
  const surPage = (n: number) => {
    router.push(`?document=${encodeURIComponent(documentId)}&page=${n}`, { scroll: false });
    // Côte à côte, la visionneuse est déjà sous les yeux ; empilée (petit écran), on la ramène.
    const visionneuse = document.getElementById("visionneuse");
    const cadre = visionneuse?.getBoundingClientRect();
    if (visionneuse && cadre && (cadre.bottom < 0 || cadre.top > window.innerHeight)) {
      visionneuse.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };
  return (
    <div className="sn-transcription">
      <p className="lf-mention-patrimoniale">
        <Icon name="info" size={20} />
        <span>{MENTION_PATRIMONIALE}</span>
      </p>
      <RenduDeTranscription transcription={transcription} urlDePage={urlDePage} surPage={surPage} variante="fil" />
    </div>
  );
}
