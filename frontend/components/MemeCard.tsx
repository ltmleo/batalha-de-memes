import Link from "next/link";

import { FotoMeme } from "@/components/FotoMeme";
import { hueStyle } from "@/components/MemeAvatar";
import { ehBusca } from "@/lib/format";
import type { Meme } from "@/lib/types";

/**
 * Card de competidor. Usado tanto em páginas server (sem ação de chaveamento)
 * quanto dentro de componentes client (com `onFocusBracket`). O link principal
 * cobre o card inteiro; as ações ficam acima dele (z-index).
 */
export function MemeCard({
  meme,
  focused = false,
  onFocusBracket,
}: {
  meme: Meme;
  focused?: boolean;
  onFocusBracket?: (id: number) => void;
}) {
  const busca = ehBusca(meme.youtube_url);

  return (
    <article className={`glass mcard${focused ? " is-focused" : ""}`} style={hueStyle(meme.id)}>
      <Link
        className="mcard-overlay"
        href={`/meme/${meme.id}`}
        aria-label={`Ver detalhes de ${meme.nome}`}
      />

      <div className="mcard-top">
        <FotoMeme id={meme.id} nome={meme.nome} youtube={meme.youtube_url} decorativo />
        <div className="mcard-id">
          <h3 className="mname">{meme.nome}</h3>
          <div className="mmeta">
            {meme.ano ? `${meme.ano} · ` : ""}
            {meme.origem || "Internet"}
          </div>
        </div>
      </div>

      {meme.historia ? <p className="mhist">{meme.historia}</p> : null}

      <div className="mcard-foot">
        <div className="chips">
          {meme.tags.slice(0, 3).map((t) => (
            <span key={t} className="chip chip--hue">
              {t}
            </span>
          ))}
        </div>
        <span className={`badge${busca ? "" : " badge--live"}`}>
          {busca ? "buscar" : "vídeo"}
        </span>
      </div>

      <div className="mcard-actions">
        <a
          className="btn btn--sm"
          href={meme.youtube_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <path d="M7 4.8v14.4a1 1 0 0 0 1.53.85l11.3-7.2a1 1 0 0 0 0-1.7L8.53 3.95A1 1 0 0 0 7 4.8Z" />
          </svg>
          {busca ? "Buscar no YouTube" : "Vídeo original"}
        </a>
        {onFocusBracket ? (
          <button
            type="button"
            className="btn btn--sm btn--ghost"
            onClick={() => onFocusBracket(meme.id)}
          >
            Chaveamento
          </button>
        ) : (
          <Link className="btn btn--sm btn--ghost" href={`/meme/${meme.id}`}>
            Abrir →
          </Link>
        )}
      </div>
    </article>
  );
}
