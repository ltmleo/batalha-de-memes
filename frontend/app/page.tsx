import Link from "next/link";
import type { CSSProperties } from "react";

import { ChaveGlimpse } from "@/components/ChaveGlimpse";
import { Countdown } from "@/components/Countdown";
import { HomeMotion } from "@/components/HomeMotion";
import { hueStyle } from "@/components/MemeAvatar";
import { RingueDuelo } from "@/components/RingueDuelo";
import { VideoLinks, linksDoMatch } from "@/components/VideoLinks";
import { agruparRodadas } from "@/lib/bracket";
import {
  estatisticas,
  listarMemes,
  listarTorneios,
  memesDoTorneio,
  obterTorneio,
} from "@/lib/estado";
import { iniciais } from "@/lib/format";
import { eliminados, epiteto, faseAoVivo, placar, votosTexto } from "@/lib/home";
import type { Meme } from "@/lib/types";

const CORES_CONFETE = ["#ffd93d", "#ff4757", "#2f7bff", "#7c3aed", "#ffffff"];

/** Confete determinístico do hero (sem aleatoriedade: HTML estável no build). */
const CONFETE = Array.from({ length: 34 }, (_, i) => ({
  x: (i * 41 + 7) % 100,
  dx: ((i % 5) - 2) * 22,
  atraso: -((i % 11) * 0.75),
  dur: 6.5 + ((i * 13) % 7) * 0.7,
  cor: CORES_CONFETE[i % CORES_CONFETE.length],
  tam: 6 + (i % 3) * 3,
}));

export default function Home() {
  const torneios = listarTorneios();
  const memes = listarMemes();

  const porId = new Map(memes.map((m) => [m.id, m]));
  const meme = (id: number | null | undefined): Meme | null => (id ? porId.get(id) ?? null : null);

  const principal = torneios.find((t) => t.status !== "aguardando") ?? torneios[0];
  const principalDetail = principal ? obterTorneio(principal.id) : null;

  const rodadas = principalDetail ? agruparRodadas(principalDetail.matches) : [];

  // Números da home escopados na temporada em disputa (o que foi sorteado) —
  // nunca nos totais globais, que também contam as temporadas aguardando.
  const stats = estatisticas(principalDetail ?? undefined);

  // Elenco da faixa de nomes: só quem foi sorteado, não o catálogo inteiro.
  const elenco = principalDetail ? memesDoTorneio(principalDetail) : memes;

  // Salas de espera em ordem de temporada (não em ordem de id decrescente).
  const salasEspera = torneios
    .filter((t) => t.status === "aguardando")
    .sort((a, b) => Number(a.temporada) - Number(b.temporada))
    .map((t) => ({
      torneio: t,
      vagas: t.tamanho,
      reservados: (obterTorneio(t.id)?.participantes ?? [])
        .map((id) => meme(id))
        .filter((m): m is Meme => Boolean(m)),
    }));

  const fase = faseAoVivo(rodadas);
  const noRingue = fase?.duelos ?? [];
  const destaque = noRingue[0] ?? null;
  const laterais = noRingue.slice(1, 5);

  const destaquesA = destaque ? meme(destaque.meme_a_id) : null;
  const destaquesB = destaque ? meme(destaque.meme_b_id) : null;

  const mortos = eliminados(rodadas, porId);
  const vitrine = mortos.slice(0, 12);
  const vivos = rodadas.length ? stats.totalMemes : 0;

  const faseNome = fase?.rodada.titulo ?? "A disputa";

  return (
    <HomeMotion>
      {/* ── Hero: a festa de abertura ───────────────────────────────────── */}
      <section className="home-hero">
        <div className="confete" aria-hidden>
          {CONFETE.map((c, i) => (
            <i
              key={i}
              style={
                {
                  "--x": `${c.x}%`,
                  "--dx": `${c.dx}px`,
                  "--atraso": `${c.atraso}s`,
                  "--dur": `${c.dur}s`,
                  "--cor": c.cor,
                  "--tam": `${c.tam}px`,
                } as CSSProperties
              }
            />
          ))}
        </div>

        <div className="hero-arena" aria-hidden>
          <span />
          <span />
          <span />
        </div>

        <div className="hero-emblem" aria-hidden>
          <svg viewBox="0 0 64 76" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <path d="M16 8h32v8a16 16 0 0 1-32 0z" />
            <path d="M16 12H7a5 5 0 0 0 5 9" />
            <path d="M48 12h9a5 5 0 0 1-5 9" />
            <path d="M32 30v18" />
            <path d="M21 48h22" />
            <path d="M24 56h16" />
            <path d="M28 56v6M36 56v6" />
          </svg>
        </div>

        <div className="wrap">
          <div className="hero-stage">
            <span className="hero-kicker">
              <span className="live">
                <span className="dot" aria-hidden />
                ao vivo agora
              </span>
              <span className="mono">
                temporada {principal?.temporada ?? "1"} · {faseNome}
              </span>
            </span>

            <h1 className="hero-h1">
              A COPA DO MUNDO DA INTERNET: <em>QUEM LEVA A TAÇA?</em>
            </h1>

            <p className="hero-fase">
              {faseNome} — <b>vote agora!</b> O perdedor vai direto pro cemitério dos caídos.
            </p>

            <div className="hero-crono">
              <span className="hero-crono-rot mono">a votação encerra em</span>
              <Countdown />
            </div>

            <div className="hero-actions">
              <a className="btn btn--primary btn--pulse" href="#ringue">
                ir para o ringue
              </a>
              {principal ? (
                <Link className="btn btn--glass" href={`/torneio/${principal.id}`}>
                  ver o chaveamento completo
                </Link>
              ) : null}
            </div>

            <p className="hero-numeros mono">
              {vivos} memes na disputa · {stats.totalConfrontos} confrontos · {mortos.length} já
              caíram · 1 taça
            </p>
          </div>
        </div>
      </section>

      {/* ── marquee do elenco ───────────────────────────────────────────── */}
      <div className="marquee-band" aria-hidden>
        <div className="marquee-track">
          {[...elenco, ...elenco].map((m, i) => (
            <span key={`${m.id}-${i}`}>
              {m.nome}
              <span className="marquee-sep">·</span>
            </span>
          ))}
        </div>
      </div>

      {/* ── O RINGUE ────────────────────────────────────────────────────── */}
      <section className="home-section" id="ringue">
        <div className="wrap">
          <header className="section-head home-rise">
            <div>
              <span className="kicker">o ringue</span>
              <h2 className="section-title">{faseNome}: dois entram, um avança</h2>
            </div>
            <p className="section-note">
              Vote na arquibancada e veja a torcida comentando ao vivo. Cada voto mexe no placar
              em tempo real — e quem perde sai carimbado.
            </p>
          </header>

          {destaque && destaquesA && destaquesB ? (
            <div className="home-rise">
              <RingueDuelo
                matchId={destaque.id}
                fase={faseNome}
                confronto={destaque.posicao + 1}
                a={{ id: destaquesA.id, nome: destaquesA.nome, epiteto: epiteto(destaquesA), votos: destaque.votos_a }}
                b={{ id: destaquesB.id, nome: destaquesB.nome, epiteto: epiteto(destaquesB), votos: destaque.votos_b }}
                tiktok={destaque.tiktok_url}
                instagram={destaque.instagram_url}
                youtube={destaque.youtube_url}
              />
            </div>
          ) : (
            <div className="empty-box">
              Nenhum confronto ao vivo. Rode <code>python -m app.cli reset_estado</code> e refaça o
              build.
            </div>
          )}

          {laterais.length > 0 ? (
            <div className="ringue-lista home-rise">
              <h3 className="ringue-lista-titulo mono">
                <span className="dot" aria-hidden /> também na {faseNome.toLowerCase()}
              </h3>
              <div className="ringue-lista-grid">
                {laterais.map((m) => {
                  const a = meme(m.meme_a_id);
                  const b = meme(m.meme_b_id);
                  const p = placar(m);
                  return (
                    <article className="mini-duelo home-scale" key={m.id}>
                      <header className="mini-duelo-topo mono">
                        ao vivo · confronto #{m.posicao + 1}
                      </header>
                      <div className="mini-duelo-corpo">
                        <div className="mini-lado">
                          <span className="avatar avatar--sm" style={hueStyle(a?.id ?? 0)} aria-hidden>
                            {iniciais(a?.nome ?? "?")}
                          </span>
                          <b>{a?.nome ?? "—"}</b>
                          <span className="mono mini-pct">{p.pctA}%</span>
                        </div>
                        <span className="mini-vs2" aria-hidden>
                          VS
                        </span>
                        <div className="mini-lado is-right">
                          <span className="mono mini-pct">{p.pctB}%</span>
                          <b>{b?.nome ?? "—"}</b>
                          <span className="avatar avatar--sm" style={hueStyle(b?.id ?? 0)} aria-hidden>
                            {iniciais(b?.nome ?? "?")}
                          </span>
                        </div>
                      </div>
                      <div className="mini-barras">
                        <span className="mini-barra mini-barra--a">
                          <i style={{ width: `${p.pctA}%` }} />
                        </span>
                        <span className="mini-barra mini-barra--b">
                          <i style={{ width: `${p.pctB}%` }} />
                        </span>
                      </div>
                      <div className="mini-duelo-rodape mono">
                        <span>{votosTexto(p.total)} votos na urna</span>
                        <VideoLinks {...linksDoMatch(m)} variante="icons" />
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
          ) : null}

          {salasEspera.map(({ torneio, vagas, reservados }) => (
            <article className="room-card ringue-card home-scale" key={torneio.id}>
              <div className="room-num" aria-hidden>
                {reservados.length}
                <span className="room-total">/{vagas}</span>
              </div>
              <div className="room-body">
                <h3>{torneio.nome} · sala de espera</h3>
                <p>
                  Enquanto a taça não sai, novos oponentes já reservam lugar na próxima edição. A
                  votação da temporada atual corre primeiro.
                </p>
                <div className="room-chips">
                  {reservados.slice(0, 8).map((m) => (
                    <Link key={m.id} className="chip" href={`/meme/${m.id}`}>
                      {m.nome}
                    </Link>
                  ))}
                  {reservados.length > 8 ? (
                    <span className="chip chip--more mono">+{reservados.length - 8}</span>
                  ) : null}
                </div>
              </div>
              <Link className="btn btn--sm" href={`/torneio/${torneio.id}`}>
                ver a fila de espera →
              </Link>
            </article>
          ))}
        </div>
      </section>

      {/* ── CEMITÉRIO DOS CAÍDOS ────────────────────────────────────────── */}
      <section className="home-section cemiterio" id="cemiterio">
        <div className="wrap">
          <header className="section-head home-rise">
            <div>
              <span className="kicker">cemitério dos caídos</span>
              <h2 className="section-title">Quem já foi pra lápide</h2>
            </div>
            <p className="section-note">
              {mortos.length} memes já caíram nesta temporada — todos em preto e branco, carimbados
              e pra sempre lembrados.
            </p>
          </header>

          {vitrine.length > 0 ? (
            <div className="cem-grid">
              {vitrine.map((e) => (
                <Link
                  className="cem-card home-scale"
                  href={`/meme/${e.meme.id}`}
                  style={hueStyle(e.meme.id)}
                  key={e.meme.id}
                  title={`Abrir o card de ${e.meme.nome}`}
                >
                  <span className="avatar avatar--lg" aria-hidden>
                    {iniciais(e.meme.nome)}
                  </span>
                  <b className="cem-nome">{e.meme.nome}</b>
                  <span className="cem-fase mono">caiu na {e.fase}</span>
                  <span className="cem-stamp" aria-hidden>
                    eliminado
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <div className="empty-box">Ninguém caiu ainda. A temporada está só começando.</div>
          )}

          <p className="cem-rodape mono">
            🪦 {mortos.length} caídos · {Math.max(vivos - mortos.length, 0)} seguem na briga pela
            taça
            {principal ? (
              <>
                {" · "}
                <Link href={`/torneio/${principal.id}`}>ver a chave completa →</Link>
              </>
            ) : null}
          </p>
        </div>
      </section>

      {/* ── A CHAVE ─────────────────────────────────────────────────────── */}
      {rodadas.length > 0 ? (
        <section className="home-section" id="chave">
          <div className="wrap">
            <header className="section-head home-rise">
              <div>
                <span className="kicker">chaveamento</span>
                <h2 className="section-title">A trilha até a taça</h2>
              </div>
              {principal ? (
                <Link className="btn btn--sm" href={`/torneio/${principal.id}`}>
                  chave completa →
                </Link>
              ) : null}
            </header>

            <div className="home-rise">
              <ChaveGlimpse rodadas={rodadas} memes={porId} />
            </div>
          </div>
        </section>
      ) : null}
    </HomeMotion>
  );
}
