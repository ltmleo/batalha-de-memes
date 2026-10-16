"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { hueStyle } from "@/components/MemeAvatar";
import { VideoLinks, linksDoMatch } from "@/components/VideoLinks";
import { GEOM, caminhoDoMeme, layoutSimetrico } from "@/lib/bracket";
import { votosTexto } from "@/lib/home";
import type { Match, Meme, TournamentDetail } from "@/lib/types";

const ZOOM_MIN = 0.3;
const ZOOM_MAX = 1.4;

function suave(): ScrollBehavior {
  if (typeof window === "undefined" || !window.matchMedia) return "smooth";
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}

/** Estado visual de um confronto na árvore. */
type EstadoCard = "vazio" | "ativo" | "decidido";

function estadoDo(match: Match): EstadoCard {
  const definido = Boolean(match.meme_a_id && match.meme_b_id);
  if (!definido) return "vazio";
  return match.winner_id ? "decidido" : "ativo";
}

function Slot({
  memeId,
  votos,
  vencedor,
  decidido,
  bye,
  memes,
  focusedId,
  onFocus,
}: {
  memeId: number | null;
  votos: number;
  vencedor: boolean;
  decidido: boolean;
  bye: boolean;
  memes: Map<number, Meme>;
  focusedId: number | null;
  onFocus: (id: number | null) => void;
}) {
  if (!memeId) {
    return (
      <div className="bslot empty">
        <span className="name">{bye ? "avança (bye)" : "a definir"}</span>
      </div>
    );
  }
  const meme = memes.get(memeId);
  const ativo = focusedId === memeId;
  const fora = decidido && !vencedor;
  return (
    <button
      type="button"
      className={`bslot hue${vencedor ? " win" : ""}${fora ? " out" : ""}${ativo ? " on" : ""}`}
      style={hueStyle(memeId)}
      onClick={() => onFocus(ativo ? null : memeId)}
      title={ativo ? "Remover destaque" : `Destacar o caminho de ${meme?.nome ?? ""}`}
    >
      <span className="name">{meme?.nome ?? "?"}</span>
      <span className="score">{votos > 0 ? votosTexto(votos) : ""}</span>
    </button>
  );
}

function MatchCard(props: {
  node: import("@/lib/bracket").SimNode;
  memes: Map<number, Meme>;
  caminho: Set<number> | null;
  focusedId: number | null;
  delay: number;
  onFocus: (id: number | null) => void;
  onHover?: (id: number | null) => void;
}) {
  const { node, memes, caminho, focusedId, delay, onFocus, onHover } = props;
  const hoverFn = onHover ?? (() => {});
  const match = node.match;
  const estado = estadoDo(match);
  const decidido = estado === "decidido";
  const bye = decidido && (match.meme_a_id === null || match.meme_b_id === null);
  const onPath = caminho ? caminho.has(match.id) : false;
  const dimmed = caminho !== null && !onPath;
  const videos = linksDoMatch(match);
  const temVideo = Boolean(videos.tiktok || videos.instagram || videos.youtube);
  const ehFinal = node.lado === "centro";

  return (
    <>
      <div
        className={`bmatch bmatch--${node.lado}${ehFinal ? " is-final" : ""} bmatch--${estado}${
          onPath ? " on-path" : ""
        }${dimmed ? " dimmed" : ""}`}
        style={
          {
            left: node.x,
            top: node.y,
            width: node.w,
            height: node.h,
            "--delay": `${delay}ms`,
            "--hue-a": (hueStyle(match.meme_a_id ?? 0) as any)["--hue"],
          } as React.CSSProperties
        }
        onMouseEnter={() => hoverFn(match.id)}
        onMouseLeave={() => hoverFn(null)}
      >
        <Slot
          memeId={match.meme_a_id}
          votos={match.votos_a}
          vencedor={decidido && match.winner_id === match.meme_a_id}
          decidido={decidido}
          bye={bye}
          memes={memes}
          focusedId={focusedId}
          onFocus={onFocus}
        />
        <Slot
          memeId={match.meme_b_id}
          votos={match.votos_b}
          vencedor={decidido && match.winner_id === match.meme_b_id}
          decidido={decidido}
          bye={bye}
          memes={memes}
          focusedId={focusedId}
          onFocus={onFocus}
        />

        {estado === "ativo" ? (
          <Link className="bmatch-cta" href="/#ringue" onClick={(e) => e.stopPropagation()}>
            vote agora
          </Link>
        ) : null}

        {ehFinal ? (
          <span className="final-trophy" aria-hidden>
            <svg viewBox="0 0 64 76" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M16 8h32v8a16 16 0 0 1-32 0z" />
              <path d="M16 12H7a5 5 0 0 0 5 9" />
              <path d="M48 12h9a5 5 0 0 1-5 9" />
              <path d="M32 30v18" />
              <path d="M21 48h22" />
              <path d="M24 56h16" />
              <path d="M28 56v6M36 56v6" />
            </svg>
          </span>
        ) : null}
      </div>

      {temVideo ? (
        <div className={`bmatch-video${node.lado === "dir" ? " bmatch-video--dir" : ""}`} style={{ left: node.x, top: node.y + node.h + 2 }}>
          <VideoLinks {...videos} variante="icons" />
        </div>
      ) : null}
    </>
  );
}

const CONFETE = Array.from({ length: 26 }, (_, i) => ({
  x: (i * 37 + 5) % 100,
  dx: ((i % 5) - 2) * 18,
  atraso: -((i % 9) * 0.6),
  dur: 7 + ((i * 11) % 6) * 0.8,
  cor: ["#ffd93d", "#ff4757", "#2f7bff", "#7c3aed", "#ffffff"][i % 5],
  tam: 5 + (i % 3) * 3,
}));
const EMOJIS = ["😂", "🏆", "🔥", "😍", "🎉", "❤️", "💀", "👑"];

export function BracketView({
  detail,
  focusedId,
  onFocusChange,
}: {
  detail: TournamentDetail;
  focusedId: number | null;
  onFocusChange: (id: number | null) => void;
}) {
  const layout = useMemo(() => layoutSimetrico(detail.matches), [detail.matches]);
  const memes = useMemo(() => new Map(detail.memes.map((m) => [m.id, m])), [detail.memes]);
  const [zoom, setZoom] = useState(0.5);
  const [hover, setHover] = useState<number | null>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const ajustado = useRef(false);

  const caminho = useMemo(
    () => (focusedId ? caminhoDoMeme(detail.matches, focusedId) : null),
    [focusedId, detail.matches],
  );
  const focado = focusedId ? memes.get(focusedId) : null;

  const ajustar = useCallback(() => {
    const vp = viewportRef.current;
    if (!vp) return;
    const alvo = (vp.clientWidth - 24) / layout.largura;
    setZoom(Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, alvo)));
  }, [layout.largura]);

  // ajusta o zoom na primeira medição para a árvore inteira caber na tela
  useEffect(() => {
    if (ajustado.current) return;
    const vp = viewportRef.current;
    if (!vp) return;
    ajustado.current = true;
    ajustar();
  }, [ajustar]);

  const scrollParaColuna = useCallback(
    (x: number) => {
      const vp = viewportRef.current;
      if (!vp) return;
      vp.scrollTo({ left: Math.max(0, x * zoom - 20), behavior: suave() });
    },
    [zoom],
  );

  // nav: uma aba por rodada, apontando para a coluna esquerda (ou a final)
  const abas = useMemo(() => {
    const porRound = new Map<number, { titulo: string; x: number }>();
    for (const c of layout.colunas) {
      if (c.lado === "dir") continue;
      porRound.set(c.round, { titulo: c.titulo, x: c.x });
    }
    return [...porRound.entries()].sort((a, b) => a[0] - b[0]).map(([round, v]) => ({ round, ...v }));
  }, [layout.colunas]);

  const estadoConector = (c: import("@/lib/bracket").SimLink) => {
    if (hover !== null && (c.fromId === hover || c.toId === hover)) return " on";
    if (caminho) return caminho.has(c.fromId) ? " on" : " dim";
    return "";
  };

  const larguraTotal = layout.largura * zoom;
  const alturaTotal = layout.altura * zoom;
  const ativo = detail.matches.some((m) => estadoDo(m) === "ativo");

  return (
    <div className="bracket-shell">
      {/* ── hero do chaveamento ─────────────────────────────────────────── */}
      <div className="chave-hero">
        <div className="confete" aria-hidden>
          {CONFETE.map((c, i) => (
            <i
              key={i}
              style={
                {
                  "--x": `${c.x}%`,
                  "--dx": `${c.dx}px`,
                  "--atraso": `${c.atraso}s`,
                  "--dur": `${c.dur}s`,
                  "--cor": c.cor,
                  "--tam": `${c.tam}px`,
                } as React.CSSProperties
              }
            />
          ))}
        </div>
        <div className="hero-arena" aria-hidden>
          <span />
          <span />
          <span />
        </div>
        <div className="chave-hero-emojis" aria-hidden>
          {EMOJIS.map((e, i) => (
            <span key={i} className="chave-emoji" style={{ "--x": `${8 + ((i * 13) % 84)}%`, "--y": `${12 + ((i * 29) % 72)}%`, "--dur": `${7 + (i % 5) * 1.5}s` } as React.CSSProperties}>
              {e}
            </span>
          ))}
        </div>
        <div className="chave-hero-body">
          <span className="kicker">chaveamento</span>
          <h2 className="chave-hero-title">
            O CHAVEAMENTO DO SÉCULO: <em>QUEM SERÁ O MAIOR MEME?</em>
          </h2>
          <p className="chave-hero-sub">Acompanhe a jornada até a grande final</p>
        </div>
      </div>

      {/* ── barra de ferramentas ───────────────────────────────────────── */}
      <div className="bracket-bar">
        <div className="rounds-nav" role="tablist" aria-label="Ir para rodada">
          {abas.map((a) => (
            <button key={a.round} type="button" onClick={() => scrollParaColuna(a.x)}>
              {a.titulo}
            </button>
          ))}
        </div>
        <span className="spacer" />
        {focado ? (
          <span className="badge badge--live focus-chip">
            <span className="dot" />
            {focado.nome}
            <Link className="focus-open" href={`/meme/${focado.id}`} title={`Abrir o card de ${focado.nome}`}>
              abrir →
            </Link>
            <button type="button" className="focus-clear" onClick={() => onFocusChange(null)} aria-label="Limpar destaque">
              ×
            </button>
          </span>
        ) : null}
        <div className="zoom" role="group" aria-label="Zoom do chaveamento">
          <button type="button" onClick={() => setZoom((z) => Math.max(ZOOM_MIN, +(z - 0.1).toFixed(2)))} aria-label="Diminuir zoom">
            −
          </button>
          <span className="zoom-val">{Math.round(zoom * 100)}%</span>
          <button type="button" onClick={() => setZoom((z) => Math.min(ZOOM_MAX, +(z + 0.1).toFixed(2)))} aria-label="Aumentar zoom">
            +
          </button>
        </div>
        <button type="button" className="btn btn--sm btn--ghost" onClick={ajustar}>
          Ajustar
        </button>
      </div>

      {/* ── árvore simétrica ───────────────────────────────────────────── */}
      <div className="bracket-viewport" ref={viewportRef}>
        <div className="bracket-zoombox" style={{ width: larguraTotal, height: alturaTotal }}>
          <div className="bracket-canvas" style={{ width: layout.largura, height: layout.altura, transform: `scale(${zoom})` }}>
            <div className="chave-centro" aria-hidden style={{ left: layout.centroX, top: layout.centroY }} />
            <div className="chave-luz" aria-hidden />

            <svg className="bracket-svg" width={layout.largura} height={layout.altura} aria-hidden>
              {layout.links.map((c) => (
                <path key={c.key} className={`bconn bconn--${c.lado}${estadoConector(c)}`} d={c.d} />
              ))}
            </svg>

            {layout.colunas.map((c) => (
              <div
                key={`${c.lado}-${c.round}`}
                className={`round-head${c.lado === "centro" ? " round-head--final" : ""}${c.lado === "dir" ? " round-head--dir" : ""}`}
                style={{ left: c.x, width: GEOM.cardW }}
              >
                {c.titulo}
              </div>
            ))}

            {layout.nodes.map((node, i) => (
              <MatchCard
                key={node.match.id}
                node={node}
                memes={memes}
                caminho={caminho}
                focusedId={focusedId}
                delay={Math.min(node.col * 90 + (i % 6) * 30, 700)}
                onFocus={onFocusChange}
                  onHover={setHover}
                />
            ))}
          </div>
        </div>
      </div>

      <div className="bracket-hint">
        {focado
          ? `Destacando o caminho de ${focado.nome}. Clique de novo para limpar.`
          : ativo
            ? "Confrontos ativos piscam em neon — vote no ringue. Clique num meme para ver o caminho dele até a final."
            : "Ainda sem votos: a chave completa espera o primeiro duelo. Sorteio já definido."}
      </div>
    </div>
  );
}
