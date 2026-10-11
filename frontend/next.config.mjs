/** @type {import('next').NextConfig} */
const nextConfig = {
  // Site 100% estático: `npm run build` gera HTML/CSS/JS em `out/`.
  output: "export",
  // GitHub Pages serve o projeto em https://ltmleo.github.io/batalha-de-memes/
  // — todo link/asset ganha esse prefixo automaticamente.
  basePath: "/batalha-de-memes",
  // URLs limpas terminando em `/` (ex.: torneio/1 -> torneio/1/index.html),
  // o formato mais robusto para GitHub Pages.
  trailingSlash: true,
};

export default nextConfig;
