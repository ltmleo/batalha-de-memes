import type { Match, Rodada } from "./types";

// --- agrupamento ---------------------------------------------------------

export function tituloRodada(round: number, totalRodadas: number, vagas: number): string {
  // A 1ª rodada é a qualificatória (85 memes entram numa chave de 128 → 43 byes).
  if (round === 1) return "Qualificatória";
  if (round === 2) return "Fase 2";
  if (round === totalRodadas) return "Final";
  if (round === totalRodadas - 1 && totalRodadas > 1) return "Semifinal";
  if (vagas === 8) return "Quartas de final";
  if (vagas === 16) return "Oitavas de final";
  return `Fase de ${vagas}`;
}

export function agruparRodadas(matches: Match[]): Rodada[] {
  const rounds = [...new Set(matches.map((m) => m.round))].sort((a, b) => a - b);
  const total = rounds.length;
  return rounds.map((round, i) => {
    const daRodada = matches
      .filter((m) => m.round === round)
      .sort((a, b) => a.posicao - b.posicao);
    // vagas = competidores que entram na rodada = nº de confrontos * 2.
    const vagas = daRodada.length * 2;
    return {
      round,
      titulo: tituloRodada(i + 1, total, vagas),
      matches: daRodada,
      vagas,
    };
  });
}

// --- geometria do chaveamento -------------------------------------------
// Cada confronto da 1ª rodada ocupa uma "faixa" vertical de altura G. As rodadas
// seguintes alinham-se ao centro do par de confrontos que as alimenta, então o
// deslocamento dobra a cada rodada (1, 2, 4, 8...).

export const GEOM = {
  cardW: 240,
  cardH: 62,
  colGap: 68,
  rowGap: 22,
} as const;

export type MatchNode = {
  match: Match;
  x: number;
  y: number;
  w: number;
  h: number;
  centerY: number;
};

export type LayoutRodada = {
  round: number;
  titulo: string;
  index: number;
  x: number;
  /** Competidores/vagas que entram nesta rodada. */
  vagas: number;
  matches: MatchNode[];
};

export type BracketLayout = {
  rodadas: LayoutRodada[];
  width: number;
  height: number;
  unit: number;
};

export function layoutBracket(matches: Match[]): BracketLayout {
  const rodadas = agruparRodadas(matches);
  const unit = GEOM.cardH + GEOM.rowGap;
  const n1 = rodadas[0]?.matches.length ?? 0;
  const height = Math.max(n1, 1) * unit;
  const total = rodadas.length;

  const layoutRodadas: LayoutRodada[] = rodadas.map((rodada, index) => {
    const x = index * (GEOM.cardW + GEOM.colGap);
    const fator = 2 ** index;
    return {
      round: rodada.round,
      titulo: rodada.titulo,
      index,
      x,
      vagas: rodada.vagas,
      matches: rodada.matches.map((match, i) => {
        const centerY = (i + 0.5) * unit * fator;
        return {
          match,
          x,
          y: centerY - GEOM.cardH / 2,
          w: GEOM.cardW,
          h: GEOM.cardH,
          centerY,
        };
      }),
    };
  });

  const width = total * GEOM.cardW + Math.max(total - 1, 0) * GEOM.colGap;
  return { rodadas: layoutRodadas, width, height, unit };
}

// --- caminho de um competidor -------------------------------------------

export function caminhoDoMeme(matches: Match[], memeId: number): Set<number> {
  const ids = new Set<number>();
  for (const m of matches) {
    if (m.meme_a_id === memeId || m.meme_b_id === memeId) ids.add(m.id);
  }
  return ids;
}
