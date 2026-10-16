import Link from "next/link";
import { Fragment } from "react";

import { hueStyle } from "@/components/MemeAvatar";
import { VideoLinks, linksDoMatch } from "@/components/VideoLinks";
import { GEOM, layoutBracket } from "@/lib/bracket";
import { votosTexto } from "@/lib/home";
import type { Meme, Rodada } from "@/lib/types";

const TOPO = 46; // faixa dos títulos das rodadas (igual ao BracketView)

function Slot({
  memeId,
  votos,
  vencedor,
  decidido,
  memes,
}: {
  memeId: number | null;
  votos: number;
  vencedor: boolean;
  decidido: boolean;
  memes: Map<number, Meme>;
}) {
  if (!memeId) {
    return (
      <div className="bslot empty">
        <span className="name">a definir</span>
      </div>
    );
  }
  const meme = memes.get(memeId);
  const out = decidido && !vencedor;
  return (
    <Link
      href={`/meme/${memeId}`}
      className={`bslot hue${vencedor ? " win" : ""}${out ? " out" : ""}`}
      style={hueStyle(memeId)}
      title={meme?.nome ?? ""}
    >
      <span className="name">{meme?.nome ?? "?"}</span>
      <span className="score">{votos > 0 ? votosTexto(votos) : ""}</span>
    </Link>
  );
}

/**
 * Vista compacta do chaveamento para a home: as quatro últimas rodadas
 * (oitavas → final) com conectores em SVG, vencedores destacados e perdedores
 * carimbados como eliminados.
 */
export function ChaveGlimpse({
  rodadas,
  memes,
}: {
  rodadas: Rodada[];
  memes: Map<number, Meme>;
}) {
  const ultimas = rodadas.slice(-4);
  const matches = ultimas.flatMap((r) => r.matches);
  const layout = layoutBracket(matches);

  const conectores: { key: string; d: string }[] = [];
  for (let r = 0; r < layout.rodadas.length - 1; r++) {
    const atual = layout.rodadas[r];
    const proxima = layout.rodadas[r + 1];
    atual.matches.forEach((node, i) => {
      const pai = proxima.matches[Math.floor(i / 2)];
      if (!pai) return;
      const x1 = node.x + GEOM.cardW;
      const y1 = TOPO + node.centerY;
      const meio = node.x + GEOM.cardW + GEOM.colGap / 2;
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
            <div key={r.round} className="round-head" style={{ left: r.x, width: GEOM.cardW }}>
              {r.titulo}
              <span className="round-count">{r.vagas}</span>
            </div>
          ))}

          {layout.rodadas.map((r) =>
            r.matches.map((node, i) => {
              const m = node.match;
              const decidido = m.winner_id !== null;
              const videos = linksDoMatch(m);
              const temVideo = Boolean(videos.tiktok || videos.instagram || videos.youtube);
              return (
                <Fragment key={m.id}>
                  <div
                    className="bmatch"
                    style={{ left: node.x, top: node.y + TOPO, "--delay": `${Math.min(r.index * 90 + i * 5, 640)}ms` } as React.CSSProperties}
                  >
                    <Slot
                      memeId={m.meme_a_id}
                      votos={m.votos_a}
                      vencedor={decidido && m.winner_id === m.meme_a_id}
                      decidido={decidido}
                      memes={memes}
                    />
                    <Slot
                      memeId={m.meme_b_id}
                      votos={m.votos_b}
                      vencedor={decidido && m.winner_id === m.meme_b_id}
                      decidido={decidido}
                      memes={memes}
                    />
                  </div>
                  {temVideo ? (
                    <div className="bmatch-video" style={{ left: node.x, top: node.y + TOPO + GEOM.cardH + 2 }}>
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
        role para o lado · o vencedor de cada duelo sobe uma rodada rumo à taça
      </div>
    </div>
  );
}
