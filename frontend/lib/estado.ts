import { readFileSync } from "node:fs";
import path from "node:path";

import type { Estado, Tournament, TournamentDetail } from "./types";

// Leitura em tempo de build: `data/estado.json` é a fonte única da verdade.
// Ajuste com a variável de ambiente ESTADO_JSON se o arquivo estiver em outro lugar.
const CAMINHO =
  process.env.ESTADO_JSON ?? path.resolve(process.cwd(), "../backend/data/estado.json");

const VAZIO: Estado = { memes: [], tournaments: [], matches: [], votes: [] };

function carregar(): Estado {
  try {
    return JSON.parse(readFileSync(CAMINHO, "utf-8")) as Estado;
  } catch {
    return VAZIO;
  }
}

export function listarTorneios(): Tournament[] {
  return [...carregar().tournaments].sort((a, b) => b.id - a.id);
}

export function obterTorneio(id: number): TournamentDetail | null {
  const estado = carregar();
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
