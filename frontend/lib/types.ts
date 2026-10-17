export type Meme = {
  id: number;
  nome: string;
  youtube_url: string;
  inicio: number;
  fim: number;
  autor_fonte: string;
  tags: string[];
  status: string;
  /** Temporada do meme no catálogo (backend/data/memes/temporada-N.json). */
  temporada?: number;
  /** Ano aproximado de origem do meme (pode ser nulo quando desconhecido). */
  ano?: number | null;
  /** Onde o meme nasceu: TV, YouTube, Vine, rádio, política... */
  origem?: string;
  /** História/contexto do meme em poucas frases. */
  historia?: string;
};

export type Match = {
  id: number;
  tournament_id: number;
  round: number;
  posicao: number;
  meme_a_id: number | null;
  meme_b_id: number | null;
  winner_id: number | null;
  video_path: string | null;
  tiktok_url?: string | null;
  /** Reels no Instagram (opcional; preenchido via `app.cli video`). */
  instagram_url?: string | null;
  /** YouTube Shorts (opcional; preenchido via `app.cli video`). */
  youtube_url?: string | null;
  /** Quando o confronto foi publicado nas redes (ISO), usado para exibir "publicado". */
  publicado_em?: string | null;
  /** Prazo de votação do confronto (ISO). */
  deadline?: string | null;
  status: string;
  votos_a: number;
  votos_b: number;
};

export type Tournament = {
  id: number;
  nome: string;
  temporada: string;
  seed: number | null;
  tamanho: number;
  status: string;
  criado_em: string;
  /** Memes reservados num torneio que ainda aguarda oponentes (status "aguardando"). */
  participantes?: number[];
};

export type TournamentDetail = Tournament & {
  memes: Meme[];
  matches: Match[];
};

// Formato de `backend/data/estado.json` (fonte única da verdade).
export type Estado = {
  memes: Meme[];
  tournaments: Tournament[];
  matches: Match[];
  votes: unknown[];
};

// Uma rodada do chaveamento agrupada para renderização.
export type Rodada = {
  round: number;
  titulo: string;
  matches: Match[];
  /** Número de vagas/competidores que entram nesta rodada. */
  vagas: number;
};
