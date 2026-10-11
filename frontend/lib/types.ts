export type Meme = {
  id: number;
  nome: string;
  youtube_url: string;
  inicio: number;
  fim: number;
  autor_fonte: string;
  tags: string[];
  status: string;
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
  tiktok_url: string | null;
  status: string;
  votos_a: number;
  votos_b: number;
};

export type Tournament = {
  id: number;
  nome: string;
  temporada: string;
  seed: number;
  tamanho: number;
  status: string;
  criado_em: string;
};

export type TournamentDetail = Tournament & {
  memes: Meme[];
  matches: Match[];
};
