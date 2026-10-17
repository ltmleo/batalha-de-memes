import { Fragment } from "react";

import { MemeSticker } from "@/components/MemeSticker";
import { VideoLinks, linksDoMatch } from "@/components/VideoLinks";
import { GEOM_COMPACT, layoutBracket } from "@/lib/bracket";
import type { Meme, Rodada } from "@/lib/types";

const TOPO = 46; // faixa dos títulos das rodadas (igual ao BracketView)

/**
 * Vista compacta do chaveamento para a home: as três rodadas finais
 * (quartas → final), que cabem inteiras na moldura, com conectores em SVG,
 * cards quadrados dos memes, vencedores coroados e perdedores carimbados.
 */
export function ChaveGlimpse({
  rodadas,
  memes,
}: {
  rodadas: Rodada[];
  memes: Map<number, Meme>;
}) {
  const ultimas = rodadas.slice(-3);
  const matches = ultimas.flatMap((r) => r.matches);
  const layout = layoutBracket(matches, GEOM_COMPACT);
  const { cardW, cardH, colGap } = GEOM_COMPACT;

  const conectores: { key: string; d: string }[] = [];
  for (let r = 0; r < layout.rodadas.length - 1; r++) {
    const atual = layout.rodadas[r];
    const proxima = layout.rodadas[r + 1];
    atual.matches.forEach((node, i) => {
      const pai = proxima.matches[Math.floor(i / 2)];
      if (!pai) return;
      const x1 = node.x + cardW;
      const y1 = TOPO + node.centerY;
      const meio = node.x + cardW + colGap / 2;
      const x2 = pai.x;
      const y2 = TOPO + pai.centerY;
      conectores.push({ key: `${node.match.id}-${pai.match.id}`, d: `M ${x1} ${y1} H ${meio} V ${y2} H ${x2}` });
    });
  }

  return (
    <div className="chave-wrap">
      <div className="chave-overflow">
        <div
          className="bracket-canvas chave-canvas"
          style={{ width: layout.width, height: layout.height + TOPO }}
        >
          <svg className="bracket-svg" width={layout.width} height={layout.height + TOPO} aria-hidden>
            {conectores.map((c) => (
              <path key={c.key} className="bconn" d={c.d} />
            ))}
          </svg>

          {layout.rodadas.map((r) => (
            <div key={r.round} className="round-head" style={{ left: r.x, width: cardW }}>
              {r.titulo}
              <span className="round-count">{r.vagas}</span>
            </div>
          ))}

          {layout.rodadas.map((r) =>
            r.matches.map((node, i) => {
              const m = node.match;
              const decidido = m.winner_id !== null;
              const bye = decidido && (m.meme_a_id === null || m.meme_b_id === null);
              const a = m.meme_a_id ? memes.get(m.meme_a_id) ?? null : null;
              const b = m.meme_b_id ? memes.get(m.meme_b_id) ?? null : null;
              const venceuA = decidido && m.winner_id === m.meme_a_id;
              const venceuB = decidido && m.winner_id === m.meme_b_id;
              const videos = linksDoMatch(m);
              const temVideo = Boolean(videos.tiktok || videos.instagram || videos.youtube);
              return (
                <Fragment key={m.id}>
                  <div
                    className={`bmatch bmatch--sm bmatch--${decidido ? "decidido" : a && b ? "ativo" : "vazio"}`}
                    style={{
                      left: node.x,
                      top: node.y + TOPO,
                      width: node.w,
                      height: node.h,
                      "--delay": `${Math.min(r.index * 90 + i * 5, 640)}ms`,
                    } as React.CSSProperties}
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
                  </div>
                  {temVideo ? (
                    <div className="bmatch-video" style={{ left: node.x, top: node.y + TOPO + cardH + 2 }}>
                      <VideoLinks {...videos} variante="icons" />
                    </div>
                  ) : null}
                </Fragment>
              );
            }),
          )}
        </div>
      </div>
      <div className="chave-hint mono">
        deslize para o lado · o vencedor de cada duelo sobe uma rodada rumo à taça
      </div>
    </div>
  );
}
