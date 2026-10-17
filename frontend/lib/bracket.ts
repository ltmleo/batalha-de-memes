import type { Match, Rodada } from "./types";

// --- agrupamento ---------------------------------------------------------

export function tituloRodada(round: number, totalRodadas: number, vagas: number): string {
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
//
// O card do confronto é um "duelo de figurinhas": dois cards quadrados (foto do
// meme + nome embaixo) e um selo VS no meio. As medidas abaixo precisam casar
// com o CSS de `.bmatch`/`.bsticker` em globals.css.

export type Geom = {
  cardW: number;
  cardH: number;
  colGap: number;
  rowGap: number;
};

/** Chaveamento grande (`/torneio/[id]`). */
export const GEOM: Geom = {
  cardW: 258,
  cardH: 174,
  colGap: 66,
  rowGap: 26,
};

/** Variante compacta usada no glimpse da home. */
export const GEOM_COMPACT: Geom = {
  cardW: 180,
  cardH: 106,
  colGap: 34,
  rowGap: 22,
};

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

export function layoutBracket(matches: Match[], geom: Geom = GEOM): BracketLayout {
  const rodadas = agruparRodadas(matches);
  const unit = geom.cardH + geom.rowGap;
  const n1 = rodadas[0]?.matches.length ?? 0;
  const height = Math.max(n1, 1) * unit;
  const total = rodadas.length;

  const layoutRodadas: LayoutRodada[] = rodadas.map((rodada, index) => {
    const x = index * (geom.cardW + geom.colGap);
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
          y: centerY - geom.cardH / 2,
          w: geom.cardW,
          h: geom.cardH,
          centerY,
        };
      }),
    };
  });

  const width = total * geom.cardW + Math.max(total - 1, 0) * geom.colGap;
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

// --- chaveamento simétrico (estilo "Copa do Mundo", final ao centro) -------
// As últimas K rodadas (oitavas → final) são espelhadas: as extremidades
// esquerda e direita exibem as oitavas e o caminho afunila para a grande
// final no centro, sobre um pedestal glorioso. Cada rodada é dividida ao
// meio: a primeira metade alimenta o lado esquerdo, a segunda o direito.

export type SimLado = "esq" | "dir" | "centro";

export type SimNode = {
  match: Match;
  x: number;
  y: number;
  w: number;
  h: number;
  centerY: number;
  col: number;
  lado: SimLado;
};

export type SimColuna = {
  round: number;
  titulo: string;
  x: number;
  lado: SimLado;
  vagas: number;
};

export type SimLink = {
  key: string;
  d: string;
  lado: SimLado;
  fromId: number;
  toId: number;
};

export type SimLayout = {
  colunas: SimColuna[];
  nodes: SimNode[];
  links: SimLink[];
  largura: number;
  altura: number;
  topo: number;
  centroX: number;
  centroY: number;
  final: SimNode | null;
};

/** Altura extra da faixa central (pedestal da final, com a taça em cima). */
const FINAL_EXTRA = 34;

export function layoutSimetrico(matches: Match[], geom: Geom = GEOM): SimLayout {
  const topo = 62; // faixa dos títulos das rodadas
  const rodadas = agruparRodadas(matches).slice(-4);
  if (rodadas.length === 0) {
    return { colunas: [], nodes: [], links: [], largura: 0, altura: topo, topo, centroX: 0, centroY: topo, final: null };
  }

  const cardW = geom.cardW;
  const cardH = geom.cardH;
  const finalH = cardH + FINAL_EXTRA;
  const K = rodadas.length;
  const S = cardH + geom.rowGap;
  const nCol = 2 * K - 1; // K-1 colunas por lado + 1 central
  const colFinal = K - 1;
  const colX = (c: number) => c * (cardW + geom.colGap);

  // confrontos por lado na rodada mais larga (a primeira exibida)
  const totalPrim = rodadas[0].matches.length;
  const porLado = Math.max(Math.floor(totalPrim / 2), 1);

  const altura = (porLado - 1) * S + cardH;
  const centroY = topo + altura / 2;
  const centroX = colX(colFinal) + cardW / 2;

  // y dos níveis por lado (índice 0..porLado-1); níveis seguintes = ponto médio
  const niveisY: number[][] = [
    Array.from({ length: porLado }, (_, i) => centroY + (i - (porLado - 1) / 2) * S),
  ];
  for (let k = 1; k <= K - 2; k++) {
    const ant = niveisY[k - 1];
    const n = Math.floor(ant.length / 2);
    niveisY.push(Array.from({ length: n }, (_, j) => (ant[2 * j] + ant[2 * j + 1]) / 2));
  }

  // nós dos lados + final
  const nodes: SimNode[] = [];
  const porChave = new Map<string, SimNode>();
  for (let k = 0; k <= K - 2; k++) {
    const rodada = rodadas[k];
    const metade = Math.floor(rodada.matches.length / 2);
    for (const m of rodada.matches) {
      const esq = m.posicao < metade;
      const lado: SimLado = esq ? "esq" : "dir";
      const idx = esq ? m.posicao : m.posicao - metade;
      const centerY = niveisY[k][idx] ?? centroY;
      const col = esq ? k : nCol - 1 - k;
      const node: SimNode = {
        match: m,
        x: colX(col),
        y: centerY - cardH / 2,
        w: cardW,
        h: cardH,
        centerY,
        col,
        lado,
      };
      nodes.push(node);
      porChave.set(`${m.round}:${m.posicao}`, node);
    }
  }
  let final: SimNode | null = null;
  const fm = rodadas[K - 1].matches[0];
  if (fm) {
    final = {
      match: fm,
      x: colX(colFinal),
      y: centroY - finalH / 2,
      w: cardW,
      h: finalH,
      centerY: centroY,
      col: colFinal,
      lado: "centro",
    };
    nodes.push(final);
    porChave.set(`${fm.round}:${fm.posicao}`, final);
  }

  // conectores: cada confronto de lado liga-se ao confronto-pai (próxima
  // rodada, mesma metade). A semi liga-se à final ao centro.
  const links: SimLink[] = [];
  for (const node of nodes) {
    if (node.lado === "centro") continue;
    const pai = porChave.get(`${node.match.round + 1}:${Math.floor(node.match.posicao / 2)}`);
    if (!pai) continue;
    const esq = node.lado === "esq";
    const x1 = esq ? node.x + cardW : node.x;
    const y1 = node.centerY;
    const x2 = esq ? pai.x : pai.x + pai.w;
    const y2 = pai.centerY;
    const meio = esq ? (node.x + cardW + pai.x) / 2 : (node.x + pai.x + pai.w) / 2;
    links.push({
      key: `${node.match.id}-${pai.match.id}`,
      d: `M ${x1} ${y1} H ${meio} V ${y2} H ${x2}`,
      lado: node.lado,
      fromId: node.match.id,
      toId: pai.match.id,
    });
  }

  // títulos das colunas (espelhados; a central vira "Grande final")
  const colunas: SimColuna[] = [];
  for (let k = 0; k <= K - 2; k++) {
    const rodada = rodadas[k];
    colunas.push({ round: rodada.round, titulo: rodada.titulo, x: colX(k), lado: "esq", vagas: rodada.vagas });
    colunas.push({ round: rodada.round, titulo: rodada.titulo, x: colX(nCol - 1 - k), lado: "dir", vagas: rodada.vagas });
  }
  const finalRod = rodadas[K - 1];
  colunas.push({ round: finalRod.round, titulo: "Grande final", x: colX(colFinal), lado: "centro", vagas: finalRod.vagas });

  const largura = nCol * cardW + Math.max(nCol - 1, 0) * geom.colGap;
  return { colunas, nodes, links, largura, altura: altura + topo, topo, centroX, centroY, final };
}
