// GitHub Pages serve o projeto em https://ltmleo.github.io/batalha-de-memes/
// (mude junto com SITE_URL em lib/site.ts se o repositório mudar de nome).
const basePath = "/batalha-de-memes";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Site 100% estático: `npm run build` gera HTML/CSS/JS em `out/`.
  output: "export",
  // todo link/asset do Next ganha esse prefixo automaticamente; <img> cru usa
  // NEXT_PUBLIC_BASE_PATH (ex.: capas em public/capas)
  basePath,
  env: { NEXT_PUBLIC_BASE_PATH: basePath },
  // URLs limpas terminando em `/` (ex.: torneio/1 -> torneio/1/index.html),
  // o formato mais robusto para GitHub Pages.
  trailingSlash: true,
};

export default nextConfig;
