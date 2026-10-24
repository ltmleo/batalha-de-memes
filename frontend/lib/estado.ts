import { readFileSync } from "node:fs";
import path from "node:path";

import type { Estado, Match, Meme, Tournament, TournamentDetail } from "./types";

// Leitura em tempo de build: `data/estado.json` é a fonte única da verdade.
// Ajuste com a variável de ambiente ESTADO_JSON se o arquivo estiver em outro lugar.
const CAMINHO =
  process.env.ESTADO_JSON ?? path.resolve(process.cwd(), "../backend/data/estado.json");

const VAZIO: Estado = { memes: [], tournaments: [], matches: [], votes: [] };

// O JSON não muda durante o build: lê e parseia uma vez só (cada página e
// cada helper chamava o parse de novo). Em `next dev` relê a cada requisição
// para refletir edições no arquivo sem reiniciar o servidor.
let cache: Estado | null = null;

export function carregarEstado(): Estado {
  if (cache && process.env.NODE_ENV === "production") return cache;
  try {
    cache = JSON.parse(readFileSync(CAMINHO, "utf-8")) as Estado;
  } catch {
    cache = VAZIO;
  }
  return cache;
}

/** Um confronto pelo id (ou null). */
export function obterMatch(id: number): Match | null {
  return carregarEstado().matches.find((m) => m.id === id) ?? null;
}

export function listarTorneios(): Tournament[] {
  return [...carregarEstado().tournaments].sort((a, b) => b.id - a.id);
}

/** Todos os memes (competidores) do catálogo, em ordem alfabética. */
export function listarMemes(): Meme[] {
  return [...carregarEstado().memes].sort((a, b) =>
    a.nome.localeCompare(b.nome, "pt-BR", { sensitivity: "base" }),
  );
}

export function obterMeme(id: number): Meme | null {
  return carregarEstado().memes.find((m) => m.id === id) ?? null;
}

export function obterTorneio(id: number): TournamentDetail | null {
  const estado = carregarEstado();
  const torneio = estado.tournaments.find((t) => t.id === id);
  if (!torneio) return null;

  return {
    ...torneio,
    memes: estado.memes,
    matches: estado.matches
      .filter((m) => m.tournament_id === id)
      .sort((a, b) => a.round - b.round || a.posicao - b.posicao),
  };
}

/** Confrontos (de todos os torneios) em que um meme participa. */
export function confrontosDoMeme(memeId: number): Match[] {
  return carregarEstado()
    .matches.filter((m) => m.meme_a_id === memeId || m.meme_b_id === memeId)
    .sort((a, b) => a.tournament_id - b.tournament_id || a.round - b.round);
}

/** IDs dos memes que efetivamente disputam um torneio. */
export function memesDoTorneio(detail: TournamentDetail): Meme[] {
  const ids = new Set<number>();
  // Torneio aguardando oponentes: participantes ficam reservados sem confrontos.
  for (const id of detail.participantes ?? []) ids.add(id);
  for (const m of detail.matches) {
    if (m.meme_a_id) ids.add(m.meme_a_id);
    if (m.meme_b_id) ids.add(m.meme_b_id);
  }
  return detail.memes
    .filter((m) => ids.has(m.id))
    .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR", { sensitivity: "base" }));
}

/** Torneio que ainda aguarda oponentes para completar a chave. */
export function estaAguardando(torneio: Pick<Tournament, "status">): boolean {
  return torneio.status === "aguardando";
}

export type Estatisticas = {
  totalMemes: number;
  totalTorneios: number;
  totalConfrontos: number;
  decididos: number;
};

export function estatisticas(detail?: TournamentDetail): Estatisticas {
  if (detail) {
    const decididos = detail.matches.filter((m) => m.winner_id !== null).length;
    return {
      totalMemes: memesDoTorneio(detail).length,
      totalTorneios: 1,
      totalConfrontos: detail.matches.length,
      decididos,
    };
  }
  const estado = carregarEstado();
  return {
    totalMemes: estado.memes.length,
    totalTorneios: estado.tournaments.length,
    totalConfrontos: estado.matches.length,
    decididos: estado.matches.filter((m) => m.winner_id !== null).length,
  };
}
