import type { Tournament, TournamentDetail } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function req<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

export const listarTorneios = () => req<Tournament[]>("/tournaments");
export const obterTorneio = (id: number) => req<TournamentDetail>(`/tournaments/${id}`);
