/** Utilidades de formatação compartilhadas (server + client). */

/** Cor (matiz HSL) estável por id — dá identidade visual a cada competidor. */
export function hueForId(id: number): number {
  return (id * 47) % 360;
}

/** Iniciais para o avatar (até 2 letras). */
export function iniciais(nome: string): string {
  const partes = nome
    .replace(/[^\p{L}\p{N} ]/gu, " ")
    .split(/\s+/)
    .filter(Boolean);
  if (partes.length === 0) return "?";
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[1][0]).toUpperCase();
}

/** O link é uma busca do YouTube (não o vídeo exato)? */
export function ehBusca(url: string): boolean {
  return /youtube\.com\/results/.test(url);
}

/** Extrai o id do vídeo do YouTube (null quando o link é uma busca ou inválido). */
export function youtubeId(url: string): string | null {
  if (!url || ehBusca(url)) return null;
  const m =
    url.match(/[?&]v=([\w-]{6,})/) ??
    url.match(/youtu\.be\/([\w-]{6,})/) ??
    url.match(/youtube\.com\/shorts\/([\w-]{6,})/) ??
    url.match(/youtube\.com\/embed\/([\w-]{6,})/);
  return m ? m[1] : null;
}

/** Extrai o id do vídeo e monta uma URL de embed (ou null para buscas). */
export function youtubeEmbed(url: string): string | null {
  const id = youtubeId(url);
  return id ? `https://www.youtube.com/embed/${id}` : null;
}

/** "Foto" do meme: miniatura do vídeo original (null quando só há busca). */
export function youtubeThumb(url: string): string | null {
  const id = youtubeId(url);
  return id ? `https://i.ytimg.com/vi/${id}/hqdefault.jpg` : null;
}

/** Título curto para o confronto. */
export function rotuloConfronto(a: string | null, b: string | null): string {
  if (a && b) return `${a} × ${b}`;
  return a ?? b ?? "a definir";
}

export function anoTexto(ano?: number | null): string {
  return ano ? String(ano) : "—";
}
