import type { MetadataRoute } from "next";

import { carregarEstado } from "@/lib/estado";
import { urlAbsoluta } from "@/lib/site";

// Gerado no build (export estático): home, competidores e todas as páginas
// de torneio, meme e confronto.
export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const estado = carregarEstado();
  const rotas = [
    "/",
    "/competidores",
    ...estado.tournaments.map((t) => `/torneio/${t.id}`),
    ...estado.memes.map((m) => `/meme/${m.id}`),
    ...estado.matches.map((m) => `/match/${m.id}`),
  ];
  return rotas.map((rota) => ({ url: urlAbsoluta(rota) }));
}
