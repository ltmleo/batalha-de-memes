"use client";

import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(useGSAP, ScrollTrigger);

/**
 * Camadas de movimento da home ("Copa do Meme"):
 * - `.home-rise`: seções entram com subida suave conforme o scroll.
 * - `.home-scale`: cards do ringue/cemitério entram em lote, crescendo de 0.94.
 * Tudo desligado com `prefers-reduced-motion: reduce` (fallback estático).
 */
export function HomeMotion({ children }: { children: React.ReactNode }) {
  const raiz = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();

      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.utils.toArray<HTMLElement>(".home-rise").forEach((el) => {
          gsap.fromTo(
            el,
            { opacity: 0, y: 38 },
            {
              opacity: 1,
              y: 0,
              duration: 0.9,
              ease: "power3.out",
              scrollTrigger: { trigger: el, start: "top 86%", once: true },
            },
          );
        });

        const cards = gsap.utils.toArray<HTMLElement>(".home-scale");
        if (cards.length) {
          gsap.fromTo(
            cards,
            { opacity: 0, y: 26, scale: 0.94 },
            {
              opacity: 1,
              y: 0,
              scale: 1,
              duration: 0.7,
              stagger: 0.09,
              ease: "power2.out",
              scrollTrigger: {
                trigger: cards[0].parentElement,
                start: "top 82%",
                once: true,
              },
            },
          );
        }
      });

      return () => mm.revert();
    },
    { scope: raiz },
  );

  return <div ref={raiz}>{children}</div>;
}