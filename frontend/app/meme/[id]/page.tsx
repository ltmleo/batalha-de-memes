import Link from "next/link";
import { notFound } from "next/navigation";

import { MemeAvatar, hueStyle } from "@/components/MemeAvatar";
import { Reveal } from "@/components/Reveal";
import { agruparRodadas } from "@/lib/bracket";
import { confrontosDoMeme, listarMemes, obterMeme, obterTorneio } from "@/lib/estado";
import { anoTexto, ehBusca, youtubeEmbed } from "@/lib/format";
import type { Match } from "@/lib/types";

export function generateStaticParams() {
  return listarMemes().map((m) => ({ id: String(m.id) }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const meme = obterMeme(Number(id));
  if (!meme) return { title: "Meme não encontrado — Batalha de Memes" };
  return {
    title: `${meme.nome} — Batalha de Memes`,
    description: meme.historia
      ? meme.historia.slice(0, 155)
      : `${meme.nome} na Batalha de Memes: história, vídeo e caminho no chaveamento.`,
  };
}

/** Rótulo humano da fase (Final, Semifinal, Quartas…) de um confronto. */
function tituloDaFase(match: Match): string {
  const detalhe = obterTorneio(match.tournament_id);
  if (!detalhe) return `Rodada ${match.round}`;
  const rodada = agruparRodadas(detalhe.matches).find((r) => r.round === match.round);
  return rodada?.titulo ?? `Rodada ${match.round}`;
}

export default async function MemePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const meme = obterMeme(Number(id));
  if (!meme) notFound();

  const todos = listarMemes();
  const index = todos.findIndex((m) => m.id === meme.id);
  const anterior = index > 0 ? todos[index - 1] : null;
  const proximo = index >= 0 && index < todos.length - 1 ? todos[index + 1] : null;

  const confrontos = confrontosDoMeme(meme.id);
  const busca = ehBusca(meme.youtube_url);
  const embed = youtubeEmbed(meme.youtube_url);

  const nomes = new Map(todos.map((m) => [m.id, m.nome]));

  return (
    <div className="wrap" style={{ paddingTop: 40 }}>
      <Reveal>
        <Link href="/competidores" className="breadcrumb">
          ← competidores
        </Link>

        <section className="glass detail-head" style={hueStyle(meme.id)}>
          <div className="who">
            <MemeAvatar id={meme.id} nome={meme.nome} />
            <div>
              <h1>{meme.nome}</h1>
              <div className="chips" style={{ marginTop: 10 }}>
                {meme.tags.map((t) => (
                  <span key={t} className="chip chip--hue">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="meta-grid">
            <div className="meta-item">
              <div className="k">Ano</div>
              <div className="v">{anoTexto(meme.ano)}</div>
            </div>
            <div className="meta-item">
              <div className="k">Origem</div>
              <div className="v">{meme.origem || "Internet"}</div>
            </div>
            <div className="meta-item">
              <div className="k">Fonte</div>
              <div className="v">{meme.autor_fonte || "—"}</div>
            </div>
            <div className="meta-item">
              <div className="k">Vídeo</div>
              <div className="v">{busca ? "busca" : "original"}</div>
            </div>
          </div>
        </section>
      </Reveal>

      <div className="detail" style={{ marginTop: 26 }}>
        <Reveal>
          <section className="glass" style={{ padding: 26 }}>
            <span className="eyebrow">História</span>
            <div className="prose">
              <p>{meme.historia || "Ainda não temos o contexto deste meme registrado."}</p>
            </div>
          </section>
        </Reveal>

        <Reveal delay={0.06}>
          <section className="stack-sm">
            {embed ? (
              <div className="video-frame">
                <iframe
                  src={embed}
                  title={`Vídeo de ${meme.nome}`}
                  loading="lazy"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  allowFullScreen
                />
              </div>
            ) : (
              <div className="glass" style={{ padding: 22, textAlign: "center" }}>
                <p className="muted" style={{ marginTop: 0 }}>
                  Não temos o link exato do vídeo original.
                </p>
                <a
                  className="btn btn--primary"
                  href={meme.youtube_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
                    <circle cx="11" cy="11" r="7" />
                    <path d="m21 21-4.3-4.3" />
                  </svg>
                  Buscar no YouTube
                </a>
              </div>
            )}

            {embed ? (
              <a
                className="btn btn--ghost"
                href={meme.youtube_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Abrir no YouTube ↗
              </a>
            ) : null}
          </section>
        </Reveal>
      </div>

      <Reveal>
        <section className="section">
          <span className="eyebrow">Campanha</span>
          <h2 className="section-title">Caminho no chaveamento</h2>
          {confrontos.length === 0 ? (
            <div className="empty-box" style={{ marginTop: 16 }}>
              Este meme ainda não entrou em nenhum confronto.
            </div>
          ) : (
            <div className="path-list">
              {confrontos.map((c) => {
                const adversarioId =
                  c.meme_a_id === meme.id ? c.meme_b_id : c.meme_a_id;
                const adversario = adversarioId ? nomes.get(adversarioId) ?? "?" : null;
                const venceu = c.winner_id === meme.id;
                const decidido = c.winner_id !== null;
                return (
                  <div className="path-item" key={c.id}>
                    <span className="rnd">{tituloDaFase(c)}</span>
                    <span className="vs">
                      vs <b>{adversario ?? "a definir"}</b>
                    </span>
                    {decidido ? (
                      <span
                        className="res"
                        style={{ color: venceu ? "var(--win)" : "var(--muted)" }}
                      >
                        {venceu ? "vitória ▸" : "eliminado"}
                      </span>
                    ) : (
                      <span className="res muted">a decidir</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </Reveal>

      <nav className="pager" aria-label="Navegação entre competidores">
        {anterior ? (
          <Link className="btn btn--ghost" href={`/meme/${anterior.id}`}>
            ← {anterior.nome}
          </Link>
        ) : (
          <span />
        )}
        {proximo ? (
          <Link className="btn btn--ghost" href={`/meme/${proximo.id}`}>
            {proximo.nome} →
          </Link>
        ) : (
          <span />
        )}
      </nav>
    </div>
  );
}
