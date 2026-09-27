"use client";

import { Button } from "@lafia/design";
import { useEffect, useRef, useState } from "react";

// `BarcodeDetector` (Shape Detection API) n'est pas encore dans les types du DOM de TypeScript.
type CodeLu = { rawValue: string };
type Detecteur = { detect(source: HTMLVideoElement): Promise<CodeLu[]> };
type ConstructeurDeDetecteur = {
  new (options: { formats: string[] }): Detecteur;
  getSupportedFormats?: () => Promise<string[]>;
};

function constructeur(): ConstructeurDeDetecteur | null {
  if (typeof window === "undefined") return null;
  const brut = (window as unknown as { BarcodeDetector?: ConstructeurDeDetecteur }).BarcodeDetector;
  // `mediaDevices` manque hors d'un contexte sûr (HTTPS) : sans caméra, pas de scanner.
  return brut && "mediaDevices" in navigator && typeof navigator.mediaDevices.getUserMedia === "function" ? brut : null;
}

/** Le numéro d'ordonnance dans ce que porte le QR code du reçu : le numéro lui-même, ou un texte qui le contient. */
export function numeroDuQr(texte: string): string {
  const trouve = texte.toUpperCase().match(/ORD-?[0-9A-Z]{3}-?[0-9A-Z]{3}/);
  return trouve ? trouve[0] : texte.trim();
}

/**
 * Le bouton « Scanner » : ouvre la caméra et lit le QR code du reçu avec `BarcodeDetector`. Le
 * navigateur qui ne sait pas lire un QR code ne montre pas le bouton ; taper le numéro marche toujours.
 */
export function Scanner({ onNumero }: { onNumero: (numero: string) => void }) {
  const [disponible, setDisponible] = useState(false);
  const [ouvert, setOuvert] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const video = useRef<HTMLVideoElement>(null);
  const rappel = useRef(onNumero);
  useEffect(() => {
    rappel.current = onNumero;
  }, [onNumero]);

  useEffect(() => {
    const Detecteur = constructeur();
    if (!Detecteur) return;
    let actif = true;
    const formats = Detecteur.getSupportedFormats ? Detecteur.getSupportedFormats() : Promise.resolve(["qr_code"]);
    formats.then((liste) => actif && setDisponible(liste.includes("qr_code"))).catch(() => undefined);
    return () => {
      actif = false;
    };
  }, []);

  useEffect(() => {
    if (!ouvert) return;
    const Detecteur = constructeur();
    if (!Detecteur) return;
    let flux: MediaStream | null = null;
    let minuterie: ReturnType<typeof setTimeout> | undefined;
    let actif = true;
    const detecteur = new Detecteur({ formats: ["qr_code"] });

    async function lire() {
      const element = video.current;
      if (!actif || !element) return;
      try {
        if (element.readyState >= 2) {
          const codes = await detecteur.detect(element);
          if (actif && codes.length && codes[0].rawValue) {
            rappel.current(numeroDuQr(codes[0].rawValue));
            setOuvert(false);
            return;
          }
        }
      } catch {
        // Une image illisible : on relit la suivante.
      }
      minuterie = setTimeout(lire, 250);
    }

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then(async (obtenu) => {
        if (!actif) {
          obtenu.getTracks().forEach((piste) => piste.stop());
          return;
        }
        flux = obtenu;
        if (video.current) {
          video.current.srcObject = obtenu;
          await video.current.play().catch(() => undefined);
        }
        lire();
      })
      .catch(() => setErreur("La caméra n’est pas accessible. Tapez le numéro."));

    return () => {
      actif = false;
      clearTimeout(minuterie);
      flux?.getTracks().forEach((piste) => piste.stop());
    };
  }, [ouvert]);

  if (!disponible) return null;
  return (
    <>
      <Button
        type="button"
        size="pro"
        variant="secondary"
        icon="qr-code"
        onClick={() => {
          setErreur(null);
          setOuvert(true);
        }}
      >
        Scanner
      </Button>
      {ouvert && (
        <div className="cp-scanner" role="dialog" aria-modal="true" aria-label="Scanner le QR code du reçu">
          <div className="cp-scanner-cadre">
            <video ref={video} className="cp-scanner-video" muted playsInline />
            <span className="cp-scanner-viseur" aria-hidden="true" />
          </div>
          <p className="cp-scanner-texte">{erreur ?? "Présentez le QR code du reçu devant la caméra."}</p>
          <Button type="button" size="pro" variant="secondary" icon="x" onClick={() => setOuvert(false)}>
            Fermer
          </Button>
        </div>
      )}
    </>
  );
}
