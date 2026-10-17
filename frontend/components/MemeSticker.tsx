"use client";

import Link from "next/link";
import { useState } from "react";

import { hueStyle } from "@/components/MemeAvatar";
import { iniciais, youtubeThumb } from "@/lib/format";
import { votosTexto } from "@/lib/home";
import type { Meme } from "@/lib/types";

// ---------------------------------------------------------------------------
// A "figurinha": card quadrado com a foto do meme em cima e o nome embaixo.
// É a peça base do chaveamento — dois deles lado a lado formam um confronto.
// Quando o meme só tem link de busca (sem vídeo exato), a foto vira um adesivo
// colorido com as iniciais e um emoji, determinístico pelo id.
// ---------------------------------------------------------------------------

const EMOJIS = [
  "😂", "🐸", "🔥", "👑", "🤡", "🤠", "👽", "🤖",
  "🎃", "🦄", "🦑", "🦖", "🦈", "🍕", "🎲", "💀",
];

/** Emoji estável por meme — dá personalidade ao card. */
export function emojiDoMeme(id: number): string {
  return EMOJIS[id % EMOJIS.length];
}

export type MemeStickerProps = {
  /** Meme do slot; `null` desenha o card vazio ("a definir"). */
  meme: Meme | null;
  votos?: number | null;
  vencedor?: boolean;
  eliminado?: boolean;
  focado?: boolean;
  /** Rótulo do slot vazio (ex.: "a definir", "avança (bye)"). */
  vazio?: string;
  size?: "md" | "sm";
  /** Vira `<button>` (destacar caminho) ou `<Link>` (abrir o meme). */
  onClick?: () => void;
  href?: string;
  title?: string;
};

export function MemeSticker({
  meme,
  votos = null,
  vencedor = false,
  eliminado = false,
  focado = false,
  vazio = "a definir",
  size = "md",
  onClick,
  href,
  title,
}: MemeStickerProps) {
  const [quebrou, setQuebrou] = useState(false);
  const thumb = meme ? youtubeThumb(meme.youtube_url) : null;
  const usaFoto = Boolean(thumb) && !quebrou;
  const mostraVotos = votos !== null && votos > 0;

  const classes = [
    "bsticker",
    `bsticker--${size}`,
    meme ? "hue" : "is-empty",
    vencedor ? "is-win" : "",
    eliminado ? "is-out" : "",
    focado ? "is-on" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const rotulo = meme
    ? `${meme.nome}${mostraVotos ? ` — ${votosTexto(votos as number)} votos` : ""}`
    : vazio;

  const conteudo = (
    <>
      <span className={`bsticker-foto${usaFoto ? " bsticker-foto--img" : ""}`}>
        {usaFoto ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            className="bsticker-img"
            src={thumb as string}
            alt=""
            loading="lazy"
            decoding="async"
            onError={() => setQuebrou(true)}
          />
        ) : (
          <span className="bsticker-adesivo" aria-hidden>
            <b>{meme ? iniciais(meme.nome) : /bye/i.test(vazio) ? "🎟️" : "?"}</b>
            {meme ? <i className="bsticker-emoji">{emojiDoMeme(meme.id)}</i> : null}
          </span>
        )}

        {eliminado ? (
          <span className="bsticker-carimbo" aria-hidden>
            eliminado
          </span>
        ) : null}
        {mostraVotos ? (
          <span className="bsticker-votos" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 12.5 10 18l10-11" />
            </svg>
            {votosTexto(votos as number)}
          </span>
        ) : null}
      </span>

      {vencedor ? (
        <span className="bsticker-coroa" aria-hidden>
          🏆
        </span>
      ) : null}

      <span className="bsticker-nome">{meme ? meme.nome : vazio}</span>
    </>
  );

  const style = meme ? hueStyle(meme.id) : undefined;

  if (href) {
    return (
      <Link className={classes} style={style} href={href} title={title ?? rotulo} aria-label={rotulo}>
        {conteudo}
      </Link>
    );
  }

  if (onClick) {
    return (
      <button type="button" className={classes} style={style} onClick={onClick} title={title ?? rotulo} aria-label={rotulo}>
        {conteudo}
      </button>
    );
  }

  return (
    <div className={classes} style={style} title={title ?? rotulo}>
      {conteudo}
    </div>
  );
}
