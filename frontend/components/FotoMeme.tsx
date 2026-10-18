"use client";

import { useState } from "react";

import { hueStyle } from "@/components/MemeAvatar";
import { iniciais, youtubeThumb } from "@/lib/format";

/**
 * A "foto" do meme: miniatura do vídeo original do YouTube, quadradinha como
 * uma figurinha. Quando o link é só uma busca (ou a imagem falha), cai no
 * adesivo de iniciais colorido — o mesmo critério do `MemeSticker` da chave.
 */
export function FotoMeme({
  id,
  nome,
  youtube,
  className = "",
  decorativo = false,
}: {
  id: number;
  nome: string;
  /** URL do vídeo original — a miniatura é derivada dela. */
  youtube?: string | null;
  /** Classes extras de tamanho (ex.: `avatar--xl`). */
  className?: string;
  /** Foto puramente decorativa (o nome já aparece ao lado). */
  decorativo?: boolean;
}) {
  const [quebrou, setQuebrou] = useState(false);
  const thumb = youtube ? youtubeThumb(youtube) : null;
  const usaFoto = Boolean(thumb) && !quebrou;

  return (
    <span
      className={`avatar${className ? ` ${className}` : ""}${usaFoto ? " avatar--foto" : ""}`}
      style={hueStyle(id)}
      aria-hidden={decorativo || undefined}
    >
      {usaFoto ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={thumb as string}
          alt={decorativo ? "" : `Foto de ${nome}`}
          loading="lazy"
          decoding="async"
          onError={() => setQuebrou(true)}
        />
      ) : (
        <b>{iniciais(nome)}</b>
      )}
    </span>
  );
}
