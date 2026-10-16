import type { Match, Meme, Rodada } from "./types";

// ---------------------------------------------------------------------------
// Derivados de estado usados pela home "Copa do Meme": fase ao vivo, placar
// percentual, eliminados (cemitério) e apelidos de torcida. Tudo calculado a
// partir de `data/estado.json` — nada hardcoded no componente.
// ---------------------------------------------------------------------------

export type FaseAoVivo = { rodada: Rodada; duelos: Match[] };

/** Primeira rodada com confronto ao vivo (os dois lados definidos e sem vencedor). */
export function faseAoVivo(rodadas: Rodada[]): FaseAoVivo | null {
  const vivos = (r: Rodada) =>
    r.matches.filter(
      (m) => m.meme_a_id && m.meme_b_id && !m.winner_id && m.status !== "cancelado",
    );

  for (const rodada of rodadas) {
    const duelos = vivos(rodada);
    if (duelos.length > 0) return { rodada, duelos };
  }

  // temporada encerrada: destaca a final
  const ultima = rodadas[rodadas.length - 1];
  return ultima ? { rodada: ultima, duelos: ultima.matches } : null;
}

export type Placar = { a: number; b: number; total: number; pctA: number; pctB: number };

/** Placar percentual de um confronto (50/50 enquanto não há votos). */
export function placar(match: Match): Placar {
  const a = Math.max(0, match.votos_a ?? 0);
  const b = Math.max(0, match.votos_b ?? 0);
  const total = a + b;
  const pctA = total > 0 ? Math.round((a / total) * 100) : 50;
  return { a, b, total, pctA, pctB: 100 - pctA };
}

export function votosTexto(n: number): string {
  return new Intl.NumberFormat("pt-BR").format(n);
}

export type Eliminado = { meme: Meme; fase: string; round: number; matchId: number };

/** Perdedores de todos os confrontos decididos, do mais recente para o mais antigo. */
export function eliminados(
  rodadas: Rodada[],
  porId: Map<number, Meme>,
  limite?: number,
): Eliminado[] {
  const lista: Eliminado[] = [];
  for (const rodada of rodadas) {
    for (const m of rodada.matches) {
      if (!m.winner_id) continue;
      const perdedor = m.winner_id === m.meme_a_id ? m.meme_b_id : m.meme_a_id;
      const meme = perdedor ? porId.get(perdedor) : undefined;
      if (meme) lista.push({ meme, fase: rodada.titulo, round: rodada.round, matchId: m.id });
    }
  }
  lista.sort(
    (x, y) =>
      y.round - x.round ||
      x.meme.nome.localeCompare(y.meme.nome, "pt-BR", { sensitivity: "base" }),
  );
  return typeof limite === "number" ? lista.slice(0, limite) : lista;
}

/** Apelido de torcida estável por meme — "(O CLÁSSICO)", "(A PENSADORA)"... */
const EPITETOS = [
  "O CLÁSSICO",
  "A PENSADORA",
  "O CONTUNDENTE",
  "A SENSAÇÃO",
  "O VETERANO",
  "A REVELAÇÃO",
  "O TERROR DA REDE",
  "A LENDA",
  "O DEVASTADOR",
  "A QUERIDINHA",
  "O IMPLACÁVEL",
  "A FRITURA ETERNA",
];

export function epiteto(meme: Meme): string {
  return EPITETOS[meme.id % EPITETOS.length];
}
