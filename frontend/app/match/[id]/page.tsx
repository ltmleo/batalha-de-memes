import { existsSync } from "node:fs";
import path from "node:path";

import Link from "next/link";
import { notFound } from "next/navigation";

import { Countdown } from "@/components/Countdown";
import { FotoMeme } from "@/components/FotoMeme";
import { Reveal } from "@/components/Reveal";
import { VideoLinks, linksDoMatch } from "@/components/VideoLinks";
import { agruparRodadas } from "@/lib/bracket";
import { carregarEstado, obterMatch, obterMeme, obterTorneio } from "@/lib/estado";
import { placar, votosTexto } from "@/lib/home";
import { SITE_URL, urlAbsoluta } from "@/lib/site";
import type { Match, Meme } from "@/lib/types";

// Página do confronto: o link que vai na bio/legenda do vídeo. Mostra os dois
// memes, como votar (comentando A ou B no vídeo), prazo e placar apurado.

export function generateStaticParams() {
  return carregarEstado().matches.map((m) => ({ id: String(m.id) }));
}

/** Capa gerada pelo kit de vídeo (copiada para public/capas pelo pipeline). */
function capaDoMatch(id: number): string | null {
  const arquivo = path.join(process.cwd(), "public", "capas", `match_${id}.jpg`);
  return existsSync(arquivo) ? `/capas/match_${id}.jpg` : null;
}

function fase(match: Match): { titulo: string; jogo: string | null } {
  const detalhe = obterTorneio(match.tournament_id);
  const rodada = detalhe
    ? agruparRodadas(detalhe.matches).find((r) => r.round === match.round)
    : undefined;
  const jogos = rodada?.matches.length ?? 0;
  return {
    titulo: rodada?.titulo ?? `Rodada ${match.round}`,
    jogo: jogos > 1 ? `jogo ${match.posicao + 1} de ${jogos}` : null,
  };
}

function nomeDe(meme: Meme | null): string {
  return meme?.nome ?? "a definir";
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const match = obterMatch(Number(id));
  if (!match) return { title: "Confronto não encontrado — Batalha de Memes" };
  const a = match.meme_a_id ? obterMeme(match.meme_a_id) : null;
  const b = match.meme_b_id ? obterMeme(match.meme_b_id) : null;
  const titulo = `${nomeDe(a)} vs ${nomeDe(b)} — Batalha de Memes`;
  const descricao = `${fase(match).titulo}: quem vence? Comente A ou B no vídeo e acompanhe o chaveamento.`;
  const capa = capaDoMatch(match.id);
  return {
    title: titulo,
    description: descricao,
    alternates: { canonical: urlAbsoluta(`/match/${match.id}`) },
    openGraph: {
      title: titulo,
      description: descricao,
      url: urlAbsoluta(`/match/${match.id}`),
      type: "website",
      ...(capa ? { images: [{ url: `${SITE_URL}${capa}`, width: 540, height: 960 }] } : {}),
    },
  };
}

function Lado({ meme, letra, votos, pct }: { meme: Meme | null; letra: "A" | "B"; votos: number; pct: number }) {
  return (
    <div className={`match-lado match-lado--${letra.toLowerCase()}`}>
      <span className="match-letra" aria-hidden>
        {letra}
      </span>
      {meme ? (
        <Link href={`/meme/${meme.id}`} className="match-foto" title={`Abrir o card de ${meme.nome}`}>
          <FotoMeme id={meme.id} nome={meme.nome} youtube={meme.youtube_url} className="avatar--xl" decorativo />
        </Link>
      ) : (
        <div className="match-foto match-foto--vazia" aria-hidden>
          ?
        </div>
      )}
      <h2 className="match-nome">{nomeDe(meme)}</h2>
      <p className="match-votos mono">
        <b>{votosTexto(votos)}</b> votos · {pct}%
      </p>
    </div>
  );
}

export default async function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const match = obterMatch(Number(id));
  if (!match) notFound();

  const a = match.meme_a_id ? obterMeme(match.meme_a_id) : null;
  const b = match.meme_b_id ? obterMeme(match.meme_b_id) : null;
  const torneio = obterTorneio(match.tournament_id);
  const { titulo, jogo } = fase(match);
  const p = placar(match);
  const capa = capaDoMatch(match.id);
  const vencedor = match.winner_id ? obterMeme(match.winner_id) : null;
  const aberto = !vencedor && Boolean(a && b) && match.status !== "cancelado";
  const prazoFuturo = match.deadline && Date.parse(match.deadline) > Date.now() ? match.deadline : null;

  return (
    <div className="wrap" style={{ paddingTop: 40 }}>
      <Reveal>
        <Link href={torneio ? `/torneio/${torneio.id}` : "/"} className="breadcrumb">
          ← {torneio ? torneio.nome : "início"}
        </Link>

        <section className="glass match-head">
          <span className="kicker">
            {titulo}
            {jogo ? ` · ${jogo}` : ""}
          </span>
          <h1 className="match-titulo">
            {nomeDe(a)} <em>vs</em> {nomeDe(b)}
          </h1>

          <div className="match-arena">
            <Lado meme={a} letra="A" votos={p.a} pct={p.pctA} />
            <span className="match-vs" aria-hidden>
              VS
            </span>
            <Lado meme={b} letra="B" votos={p.b} pct={p.pctB} />
          </div>

          <div className="match-barra" role="img" aria-label={`A ${p.pctA}%, B ${p.pctB}%`}>
            <i className="match-barra-a" style={{ width: `${p.pctA}%` }} />
            <i className="match-barra-b" style={{ width: `${p.pctB}%` }} />
          </div>

          {vencedor ? (
            <p className="match-status match-status--fim">
              <b>{vencedor.nome}</b> venceu e avança na chave.
            </p>
          ) : null}
          {aberto && prazoFuturo ? (
            <div className="match-status">
              <span className="mono">a votação encerra em</span>
              <Countdown alvo={prazoFuturo} />
            </div>
          ) : null}
          {!a || !b ? (
            <p className="match-status">Aguardando o vencedor do confronto anterior.</p>
          ) : null}
        </section>

        {a && b ? (
          <section className="match-grade">
            <article className="glass match-como">
              <h2 className="section-title">Como votar</h2>
              <ol>
                <li>Abra o vídeo do confronto.</li>
                <li>
                  Comente <b>A</b> para {a.nome} ou <b>B</b> para {b.nome}.
                </li>
                <li>Vale um voto por perfil — o primeiro comentário com A ou B.</li>
              </ol>
              <VideoLinks {...linksDoMatch(match)} msgVazio="vídeo ainda não publicado" />
              {p.total > 0 ? (
                <p className="section-note">
                  Placar apurado nos comentários: {votosTexto(p.total)} votos válidos.
                </p>
              ) : null}
            </article>

            {capa ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                className="match-capa"
                src={`${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}${capa}`}
                alt={`Capa do confronto ${a.nome} vs ${b.nome}`}
                width={540}
                height={960}
                loading="lazy"
              />
            ) : null}
          </section>
        ) : null}
      </Reveal>
    </div>
  );
}
