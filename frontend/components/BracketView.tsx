"use client";

import Link from "next/link";
import { useCallback, useMemo, useRef, useState } from "react";

import { hueStyle } from "@/components/MemeAvatar";
import { VideoLinks, linksDoMatch } from "@/components/VideoLinks";
import { GEOM, caminhoDoMeme, layoutBracket } from "@/lib/bracket";
import type { Match, Meme, TournamentDetail } from "@/lib/types";

const TOPO = 46; // faixa reservada para os títulos das rodadas
const ZOOM_MIN = 0.3;
const ZOOM_MAX = 1.4;

function suave(): ScrollBehavior {
  if (typeof window === "undefined" || !window.matchMedia) return "smooth";
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}

type SlotProps = {
  memeId: number | null;
  votos: number;
  vencedor: boolean;
  bye: boolean;
  memes: Map<number, Meme>;
  focusedId: number | null;
  onFocus: (id: number | null) => void;
};

function Slot({ memeId, votos, vencedor, bye, memes, focusedId, onFocus }: SlotProps) {
  if (!memeId) {
    return (
      <div className="bslot empty">
        <span className="name">{bye ? "avança (bye)" : "a definir"}</span>
      </div>
    );
  }

  const meme = memes.get(memeId);
  const ativo = focusedId === memeId;

  return (
    <button
      type="button"
      className={`bslot hue${vencedor ? " win" : ""}${ativo ? " on" : ""}`}
      style={hueStyle(memeId)}
      onClick={() => onFocus(ativo ? null : memeId)}
      title={ativo ? "Remover destaque" : `Destacar o caminho de ${meme?.nome ?? ""}`}
    >
      <span className="name">{meme?.nome ?? "?"}</span>
      <span className="score">{votos > 0 ? votos : ""}</span>
    </button>
  );
}

function MatchCard({
  match,
  x,
  y,
  memes,
  caminho,
  focusedId,
  delay,
  onFocus,
  onHover,
}: {
  match: Match;
  x: number;
  y: number;
  memes: Map<number, Meme>;
  caminho: Set<number> | null;
  focusedId: number | null;
  delay: number;
  onFocus: (id: number | null) => void;
  onHover: (id: number | null) => void;
}) {
  const bye = match.status === "finalizado" && (match.meme_a_id === null || match.meme_b_id === null);
  const onPath = caminho ? caminho.has(match.id) : false;
  const dimmed = caminho !== null && !onPath;
  const videos = linksDoMatch(match);
  const temVideo = Boolean(videos.tiktok || videos.instagram || videos.youtube);

  return (
    <>
      <div
        className={`bmatch${onPath ? " on-path" : ""}${dimmed ? " dimmed" : ""}`}
        style={{ left: x, top: y + TOPO, "--delay": `${delay}ms` } as React.CSSProperties}
        onMouseEnter={() => onHover(match.id)}
        onMouseLeave={() => onHover(null)}
      >
        <Slot
          memeId={match.meme_a_id}
          votos={match.votos_a}
          vencedor={match.winner_id !== null && match.winner_id === match.meme_a_id}
          bye={bye}
          memes={memes}
          focusedId={focusedId}
          onFocus={onFocus}
        />
        <Slot
          memeId={match.meme_b_id}
          votos={match.votos_b}
          vencedor={match.winner_id !== null && match.winner_id === match.meme_b_id}
          bye={bye}
          memes={memes}
          focusedId={focusedId}
          onFocus={onFocus}
        />
      </div>
      {temVideo ? (
        <div className="bmatch-video" style={{ left: x, top: y + TOPO + GEOM.cardH + 2 }}>
          <VideoLinks {...videos} variante="icons" />
        </div>
      ) : null}
    </>
  );
}

export function BracketView({
  detail,
  focusedId,
  onFocusChange,
}: {
  detail: TournamentDetail;
  focusedId: number | null;
  onFocusChange: (id: number | null) => void;
}) {
  const layout = useMemo(() => layoutBracket(detail.matches), [detail.matches]);
  const memes = useMemo(() => new Map(detail.memes.map((m) => [m.id, m])), [detail.memes]);
  const [zoom, setZoom] = useState(0.62);
  const [hover, setHover] = useState<number | null>(null);
  const viewportRef = useRef<HTMLDivElement>(null);

  const caminho = useMemo(
    () => (focusedId ? caminhoDoMeme(detail.matches, focusedId) : null),
    [focusedId, detail.matches],
  );
  const focado = focusedId ? memes.get(focusedId) : null;

  const scrollParaRodada = useCallback(
    (index: number) => {
      const vp = viewportRef.current;
      if (!vp) return;
      vp.scrollTo({ left: layout.rodadas[index].x * zoom - 16, behavior: suave() });
    },
    [layout, zoom],
  );

  const ajustar = useCallback(() => {
    const vp = viewportRef.current;
    if (!vp) return;
    const alvo = (vp.clientWidth - 28) / layout.width;
    setZoom(Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, alvo)));
  }, [layout.width]);

  // Conectores: cada confronto liga-se ao confronto-pai da rodada seguinte.
  const conectores = useMemo(() => {
    const lista: {
      key: string;
      d: string;
      childMatchId: number;
      parentMatchId: number;
    }[] = [];
    for (let r = 0; r < layout.rodadas.length - 1; r++) {
      const atual = layout.rodadas[r];
      const proxima = layout.rodadas[r + 1];
      atual.matches.forEach((node, i) => {
        const parent = proxima.matches[Math.floor(i / 2)];
        if (!parent) return;
        const x1 = node.x + GEOM.cardW;
        const y1 = TOPO + node.centerY;
        const mx = node.x + GEOM.cardW + GEOM.colGap / 2;
        const x2 = parent.x;
        const y2 = TOPO + parent.centerY;
        lista.push({
          key: `${node.match.id}-${parent.match.id}`,
          d: `M ${x1} ${y1} H ${mx} V ${y2} H ${x2}`,
          childMatchId: node.match.id,
          parentMatchId: parent.match.id,
        });
      });
    }
    return lista;
  }, [layout]);

  const estadoConector = (c: { childMatchId: number; parentMatchId: number }) => {
    if (hover !== null && (c.childMatchId === hover || c.parentMatchId === hover)) return " on";
    if (caminho) return caminho.has(c.childMatchId) ? " on" : " dim";
    return "";
  };

  const larguraTotal = layout.width * zoom;
  const alturaTotal = (layout.height + TOPO) * zoom;

  return (
    <div className="bracket-shell">
      <div className="bracket-bar">
        <div className="rounds-nav" role="tablist" aria-label="Ir para rodada">
          {layout.rodadas.map((r, i) => (
            <button key={r.round} type="button" onClick={() => scrollParaRodada(i)}>
              {r.titulo}
            </button>
          ))}
        </div>
        <span className="spacer" />
        {focado ? (
          <span className="badge badge--live focus-chip">
            <span className="dot" />
            {focado.nome}
            <Link
              className="focus-open"
              href={`/meme/${focado.id}`}
              title={`Abrir o card de ${focado.nome}`}
            >
              abrir →
            </Link>
            <button
              type="button"
              className="focus-clear"
              onClick={() => onFocusChange(null)}
              aria-label="Limpar destaque"
            >
              ×
            </button>
          </span>
        ) : null}
        <div className="zoom" role="group" aria-label="Zoom do chaveamento">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(ZOOM_MIN, +(z - 0.1).toFixed(2)))}
            aria-label="Diminuir zoom"
          >
            −
          </button>
          <span className="zoom-val">{Math.round(zoom * 100)}%</span>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(ZOOM_MAX, +(z + 0.1).toFixed(2)))}
            aria-label="Aumentar zoom"
          >
            +
          </button>
        </div>
        <button type="button" className="btn btn--sm btn--ghost" onClick={ajustar}>
          Ajustar
        </button>
      </div>

      <div className="bracket-viewport" ref={viewportRef}>
        <div className="bracket-zoombox" style={{ width: larguraTotal, height: alturaTotal }}>
          <div
            className="bracket-canvas"
            style={{ width: layout.width, height: layout.height + TOPO, transform: `scale(${zoom})` }}
          >
            <svg
              className="bracket-svg"
              width={layout.width}
              height={layout.height + TOPO}
              aria-hidden
            >
              {conectores.map((c) => (
                <path key={c.key} className={`bconn${estadoConector(c)}`} d={c.d} />
              ))}
            </svg>

            {layout.rodadas.map((r) => (
              <div
                key={r.round}
                className="round-head"
                style={{ left: r.x, width: GEOM.cardW }}
              >
                {r.titulo}
                <span className="round-count">{r.vagas}</span>
              </div>
            ))}

            {layout.rodadas.map((r) =>
              r.matches.map((node, i) => (
                <MatchCard
                  key={node.match.id}
                  match={node.match}
                  x={node.x}
                  y={node.y}
                  memes={memes}
                  caminho={caminho}
                  focusedId={focusedId}
                  delay={Math.min(r.index * 90 + i * 4, 700)}
                  onFocus={onFocusChange}
                  onHover={setHover}
                />
              )),
            )}
          </div>
        </div>
      </div>

      <div className="bracket-hint">
        {focado
          ? `Destacando o caminho de ${focado.nome}. Clique de novo para limpar.`
          : "Clique em um competidor para destacar o caminho dele no chaveamento."}
      </div>
    </div>
  );
}
