import { Fragment } from "react";

import { MemeSticker } from "@/components/MemeSticker";
import { VideoLinks, linksDoMatch } from "@/components/VideoLinks";
import { GEOM_COMPACT, layoutSimetrico } from "@/lib/bracket";
import type { Meme, Rodada } from "@/lib/types";

/**
 * Vista compacta do chaveamento para a home: a mesma árvore simétrica de
 * `/torneio/[id]` (1ª rodada — o sorteio real — nas duas extremidades e a
 * grande final ao centro, sobre o pedestal da taça), só que em tamanho
 * reduzido. A moldura rola nos dois eixos quando a árvore não cabe inteira.
 */
export function ChaveGlimpse({
  rodadas,
  memes,
}: {
  rodadas: Rodada[];
  memes: Map<number, Meme>;
}) {
  const layout = layoutSimetrico(
    rodadas.flatMap((r) => r.matches),
    GEOM_COMPACT,
  );
  const { cardW } = GEOM_COMPACT;

  if (layout.nodes.length === 0) return null;

  // folga embaixo pros links de vídeo que ficam sob o último confronto
  const alturaCanvas = layout.altura + 24;

  return (
    <div className="chave-wrap">
      <div className="chave-overflow">
        <div
          className="bracket-canvas chave-canvas"
          style={{ width: layout.largura, height: alturaCanvas }}
        >
          <div className="chave-centro" aria-hidden style={{ left: layout.centroX, top: layout.centroY }} />
          <div className="chave-luz" aria-hidden />

          <svg className="bracket-svg" width={layout.largura} height={alturaCanvas} aria-hidden>
            {layout.links.map((c) => (
              <path key={c.key} className={`bconn bconn--${c.lado}`} d={c.d} />
            ))}
          </svg>

          {layout.colunas.map((c) => (
            <div
              key={`${c.lado}-${c.round}`}
              className={`round-head${c.lado === "centro" ? " round-head--final" : ""}${
                c.lado === "dir" ? " round-head--dir" : ""
              }`}
              style={{ left: c.x, width: cardW }}
            >
              {c.titulo}
            </div>
          ))}

          {layout.nodes.map((node, i) => {
            const m = node.match;
            const decidido = m.winner_id !== null;
            const bye = decidido && (m.meme_a_id === null || m.meme_b_id === null);
            const a = m.meme_a_id ? memes.get(m.meme_a_id) ?? null : null;
            const b = m.meme_b_id ? memes.get(m.meme_b_id) ?? null : null;
            const venceuA = decidido && m.winner_id === m.meme_a_id;
            const venceuB = decidido && m.winner_id === m.meme_b_id;
            const videos = linksDoMatch(m);
            const temVideo = Boolean(videos.tiktok || videos.instagram || videos.youtube);
            const ehFinal = node.lado === "centro";
            const estado = decidido ? "decidido" : a && b ? "ativo" : "vazio";

            return (
              <Fragment key={m.id}>
                <div
                  className={`bmatch bmatch--sm bmatch--${node.lado}${
                    ehFinal ? " is-final" : ""
                  } bmatch--${estado}`}
                  style={
                    {
                      left: node.x,
                      top: node.y,
                      width: node.w,
                      height: node.h,
                      "--delay": `${Math.min(node.col * 70 + (i % 6) * 35, 620)}ms`,
                    } as React.CSSProperties
                  }
                >
                  <MemeSticker
                    size="sm"
                    meme={a}
                    votos={m.votos_a}
                    vencedor={venceuA}
                    eliminado={decidido && !venceuA && !bye}
                    vazio={bye ? "avança (bye)" : "a definir"}
                    href={a ? `/meme/${a.id}` : undefined}
                    title={a ? `Abrir o card de ${a.nome}` : undefined}
                  />
                  <span className="bmatch-vs" aria-hidden>
                    VS
                  </span>
                  <MemeSticker
                    size="sm"
                    meme={b}
                    votos={m.votos_b}
                    vencedor={venceuB}
                    eliminado={decidido && !venceuB && !bye}
                    vazio={bye ? "avança (bye)" : "a definir"}
                    href={b ? `/meme/${b.id}` : undefined}
                    title={b ? `Abrir o card de ${b.nome}` : undefined}
                  />

                  {ehFinal ? (
                    <span className="final-trophy" aria-hidden>
                      <svg viewBox="0 0 64 76" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M16 8h32v8a16 16 0 0 1-32 0z" />
                        <path d="M16 12H7a5 5 0 0 0 5 9" />
                        <path d="M48 12h9a5 5 0 0 1 5 9" />
                        <path d="M32 30v18" />
                        <path d="M21 48h22" />
                        <path d="M24 56h16" />
                        <path d="M28 56v6M36 56v6" />
                      </svg>
                    </span>
                  ) : null}
                </div>

                {temVideo ? (
                  <div className="bmatch-video" style={{ left: node.x, top: node.y + node.h + 2 }}>
                    <VideoLinks {...videos} variante="icons" />
                  </div>
                ) : null}
              </Fragment>
            );
          })}
        </div>
      </div>
      <div className="chave-hint mono">
        deslize para percorrer a chave · o vencedor de cada duelo sobe uma rodada rumo à taça
      </div>
    </div>
  );
}
