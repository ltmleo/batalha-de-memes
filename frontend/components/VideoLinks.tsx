import type { ReactNode } from "react";

import type { Match } from "@/lib/types";

// ---------------------------------------------------------------------------
// Links de vídeo de um confronto nas redes (TikTok / Instagram / YouTube
// Shorts). Os votos são contados manualmente; estes links levam a torcida ao
// vídeo publicado. Plataformas sem URL ficam ocultas.
// ---------------------------------------------------------------------------

type Plataforma = "tiktok" | "instagram" | "youtube";

const ICONES: Record<Plataforma, ReactNode> = {
  tiktok: (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12.53 2h2.99c.16 1.35.66 2.6 1.5 3.61.86.99 2.03 1.68 3.34 1.9v3.03a8.2 8.2 0 0 1-4.5-1.5v6.13a6.34 6.34 0 1 1-6.34-6.34c.33 0 .65.03.97.08v3.15a3.24 3.24 0 1 0 2.32 3.11V2z" />
    </svg>
  ),
  instagram: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.3" cy="6.7" r="1.1" fill="currentColor" stroke="none" />
    </svg>
  ),
  youtube: (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M22 12c0-2-.2-3.4-.5-4.3a2.6 2.6 0 0 0-1.8-1.8C18.8 5.5 16.5 5.4 12 5.4s-6.8.1-7.7.5A2.6 2.6 0 0 0 2.5 7.7C2.2 8.6 2 10 2 12s.2 3.4.5 4.3c.2.8.9 1.5 1.8 1.8.9.4 3.2.5 7.7.5s6.8-.1 7.7-.5a2.6 2.6 0 0 0 1.8-1.8c.3-.9.5-2.3.5-4.3zM10 15.5v-7l6 3.5-6 3.5z" />
    </svg>
  ),
};

const ORDEM: { p: Plataforma; rotulo: string }[] = [
  { p: "tiktok", rotulo: "TikTok" },
  { p: "instagram", rotulo: "Instagram" },
  { p: "youtube", rotulo: "YouTube" },
];

export type VideoLinksProps = {
  tiktok?: string | null;
  instagram?: string | null;
  youtube?: string | null;
  /** "full" = ícone + nome; "icons" = só ícone (chaveamento/mini-duelos). */
  variante?: "full" | "icons";
  /** Texto exibido quando não há nenhum link (opcional). */
  msgVazio?: string | null;
  className?: string;
};

/** Extrai os links de vídeo de um confronto. */
export function linksDoMatch(match: Match): Pick<VideoLinksProps, "tiktok" | "instagram" | "youtube"> {
  return {
    tiktok: match.tiktok_url,
    instagram: match.instagram_url,
    youtube: match.youtube_url,
  };
}

export function VideoLinks({
  tiktok,
  instagram,
  youtube,
  variante = "full",
  msgVazio = null,
  className,
}: VideoLinksProps) {
  const porPlataforma: Record<Plataforma, string | null | undefined> = {
    tiktok,
    instagram,
    youtube,
  };
  const itens = ORDEM.filter(({ p }) => Boolean(porPlataforma[p]));

  if (itens.length === 0) {
    return msgVazio ? <span className="video-vazio mono">{msgVazio}</span> : null;
  }

  return (
    <div className={`video-links video-links--${variante}${className ? ` ${className}` : ""}`}>
      {itens.map(({ p, rotulo }) => (
        <a
          key={p}
          className={`video-link video-link--${p}`}
          href={porPlataforma[p] as string}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Assistir no ${rotulo}`}
          title={`Assistir no ${rotulo}`}
        >
          {ICONES[p]}
          {variante === "full" ? <span>{rotulo}</span> : null}
        </a>
      ))}
    </div>
  );
}
