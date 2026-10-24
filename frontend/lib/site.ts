/** Endereços públicos do site (GitHub Pages) e do repositório. */

/** Origem + basePath, sem barra final. Mude junto com `basePath` em next.config.mjs. */
export const SITE_URL = "https://ltmleo.github.io/batalha-de-memes";

export const REPO_URL = "https://github.com/ltmleo/batalha-de-memes";

/** URL absoluta de uma rota do site (ex.: "/match/3" → https://…/match/3/). */
export function urlAbsoluta(rota: string): string {
  const limpa = rota.replace(/^\/+|\/+$/g, "");
  return limpa ? `${SITE_URL}/${limpa}/` : `${SITE_URL}/`;
}
