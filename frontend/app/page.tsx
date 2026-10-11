import Link from "next/link";
import type { CSSProperties } from "react";

import { HomeMotion } from "@/components/HomeMotion";
import { hueStyle } from "@/components/MemeAvatar";
import { agruparRodadas } from "@/lib/bracket";
import { estatisticas, listarMemes, listarTorneios, obterTorneio } from "@/lib/estado";
import { hueForId, iniciais } from "@/lib/format";
import type { Match, Meme } from "@/lib/types";

/** Nome ou vaga a exibir num slot do chaveamento (rodadas futuras não têm vencedores). */
function nomeDoSlot(meme: Meme | null, match: Match, ehSegundo: boolean): string {
  if (meme) return meme.nome;
  const k = match.posicao + 1; // posicao é 0-based; a vaga herda o confronto da rodada anterior
  return `venc. do confronto ${ehSegundo ? k * 2 : k * 2 - 1}`;
}

/** Um dos lados de um duelo do "ringue". */
function Lado({ meme, direita = false }: { meme: Meme | null; direita?: boolean }) {
  if (!meme) {
    return (
      <div className={`r-lado r-vaga ${direita ? "is-right" : ""}`}>
        <span className="mono">vaga em aberto</span>
      </div>
    );
  }
  return (
    <div className={`r-lado ${direita ? "is-right" : ""}`} style={hueStyle(meme.id)}>
      <span className="avatar avatar--xl" aria-hidden>
        {iniciais(meme.nome)}
      </span>
      <b className="r-nome">{meme.nome}</b>
      <Link className="r-sel mono" href={`/meme/${meme.id}`}>
        abrir card ↗
      </Link>
      <span className="r-bar">
        <span className="track">
          <span
            className="fill"
            style={{ background: `hsl(${hueForId(meme.id)} 52% 58%)` }}
          />
        </span>
        <span className="r-alt mono">votação em aberto</span>
      </span>
    </div>
  );
}

export default function Home() {
  const torneios = listarTorneios();
  const memes = listarMemes();
  const stats = estatisticas();

  const porId = new Map(memes.map((m) => [m.id, m]));
  const meme = (id: number | null | undefined): Meme | null => (id ? porId.get(id) ?? null : null);

  const principal = torneios.find((t) => t.status !== "aguardando") ?? torneios[0];
  const t2 = torneios.find((t) => t.status === "aguardando");
  const t1Detail = principal ? obterTorneio(principal.id) : null;
  const t2Detail = t2 ? obterTorneio(t2.id) : null;

  const rodadas = t1Detail ? agruparRodadas(t1Detail.matches) : [];
  const faseAtual = rodadas[0] ?? null;
  const duelos = (faseAtual?.matches ?? []).filter((m) => m.meme_a_id && m.meme_b_id);
  const emAmostra = duelos.slice(0, 3);

  const t2memes = (t2Detail?.participantes ?? [])
    .map((id) => meme(id))
    .filter((m): m is Meme => Boolean(m));
  const t2vagas = t2?.tamanho ?? 64;

  return (
    <HomeMotion>
      {/* ── Attention: hero cinematográfico central ─────────────────────── */}
      <section className="home-hero">
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
                rodada em disputa
              </span>
              <span className="mono">temporada 1 · fase de 64</span>
            </span>
            <h1 className="hero-h1">
              A Copa do Mundo da internet — <em>quem leva a taça?</em>
            </h1>
            <p className="hero-sub">
              Os {duelos.length} confrontos da fase de 64 já estão armados. Conheça a
              história de cada competidor, veja quem espera na fila e acompanhe o
              caminho até a final.
            </p>
            <div className="hero-actions">
              <a className="btn btn--primary btn--pulse" href="#ringue">
                Ir para o ringue
              </a>
              {principal ? (
                <Link className="btn btn--glass" href={`/torneio/${principal.id}`}>
                  Ver o chaveamento completo
                </Link>
              ) : null}
            </div>

            <div className="stats placar">
              <div className="stat glass stat--lead">
                <div className="n">{duelos.length}</div>
                <div className="l">confrontos da fase de 64</div>
              </div>
              <div className="stat glass">
                <div className="n">{stats.decididos}</div>
                <div className="l">duelos decididos</div>
              </div>
              <div className="stat glass">
                <div className="n">
                  {t2memes.length}
                  <span className="stat-slash">/{t2vagas}</span>
                </div>
                <div className="l">aguardando na temporada 2</div>
              </div>
              <div className="stat glass">
                <div className="n">{stats.totalMemes}</div>
                <div className="l">competidores na liga</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── marquee do elenco ───────────────────────────────────────────── */}
      <div className="marquee-band" aria-hidden>
        <div className="marquee-track">
          {[...memes, ...memes].map((m, i) => (
            <span key={`${m.id}-${i}`}>
              {m.nome}
              <span className="marquee-sep">·</span>
            </span>
          ))}
        </div>
      </div>

      {/* ── Interest: o ringue ──────────────────────────────────────────── */}
      <section className="home-section" id="ringue">
        <div className="wrap">
          <header className="section-head home-rise">
            <div>
              <span className="kicker">O ringue</span>
              <h2 className="section-title">Batalhas da fase de 64</h2>
            </div>
            {emAmostra.length > 0 ? (
              <p className="section-note">
                Três confrontos em destaque — todos os {duelos.length} duelos estão na
                chave. Votação abre quando o público entrar na arena.
              </p>
            ) : (
              <p className="section-note">Os confrontos da fase de 64 ainda estão sendo montados.</p>
            )}
          </header>

          {emAmostra.length > 0 ? (
            <div className="ringue-grid home-rise">
              {(() => {
                const m = emAmostra[0];
                const a = meme(m.meme_a_id);
                const b = meme(m.meme_b_id);
                return (
                  <article className="ringue-card vs-featured home-scale">
                    <header className="ringue-head">
                      <span className="badge badge--live">
                        <span className="dot" aria-hidden /> fase de 64
                      </span>
                      <span className="mono ringue-n">confronto #{m.posicao + 1}</span>
                    </header>
                    <div className="ringue-field">
                      <Lado meme={a} />
                      <span className="r-vs" aria-hidden>
                        <span className="vs-badge">VS</span>
                      </span>
                      <Lado meme={b} direita />
                    </div>
                    <footer className="ringue-foot">
                      <span className="mono">a votação acontece na arena</span>
                      {principal ? (
                        <Link className="btn btn--sm" href={`/torneio/${principal.id}`}>
                          acompanhar no chaveamento →
                        </Link>
                      ) : null}
                    </footer>
                  </article>
                );
              })()}

              {emAmostra.slice(1).map((m) => {
                const a = meme(m.meme_a_id);
                const b = meme(m.meme_b_id);
                return (
                  <article className="ringue-card vs-side home-scale" key={m.id}>
                    <div className="vs-mini">
                      <div className="mini-lane">
                        <span className="avatar avatar--md" style={hueStyle(a?.id ?? 0)} aria-hidden>
                          {iniciais(a?.nome ?? "?")}
                        </span>
                        <b>{a?.nome ?? "—"}</b>
                      </div>
                      <span className="mini-vs" aria-hidden>
                        VS
                      </span>
                      <div className="mini-lane is-right">
                        <b>{b?.nome ?? "—"}</b>
                        <span className="avatar avatar--md" style={hueStyle(b?.id ?? 0)} aria-hidden>
                          {iniciais(b?.nome ?? "?")}
                        </span>
                      </div>
                    </div>
                    <div className="mini-foot mono">fase de 64 · confronto #{m.posicao + 1}</div>
                  </article>
                );
              })}

              <article className="ringue-card room-card home-scale">
                <div className="room-num" aria-hidden>
                  {t2memes.length}
                  <span className="room-total">/{t2vagas}</span>
                </div>
                <div className="room-body">
                  <h3>{t2 ? t2.nome : "Temporada 2"}</h3>
                  <p>
                    Na fila de espera, novos oponentes aguardam para completar a chave da
                    próxima edição. A votação da temporada atual corre primeiro.
                  </p>
                  <div className="room-chips">
                    {t2memes.slice(0, 8).map((m) => (
                      <Link key={m.id} className="chip" href={`/meme/${m.id}`}>
                        {m.nome}
                      </Link>
                    ))}
                    {t2memes.length > 8 ? (
                      <span className="chip chip--more mono">+{t2memes.length - 8}</span>
                    ) : null}
                  </div>
                </div>
                {t2 ? (
                  <Link className="btn btn--sm" href={`/torneio/${t2.id}`}>
                    ver fila de espera →
                  </Link>
                ) : null}
              </article>
            </div>
          ) : (
            <div className="empty-box">
              Nenhum confronto gerado ainda. Rode <code>python -m app.cli reset_estado</code> e
              refaça o build.
            </div>
          )}
        </div>
      </section>

      {/* ── Desire: a chave em faixa horizontal ─────────────────────────── */}
      {rodadas.length > 0 ? (
        <section className="home-section">
          <div className="wrap">
            <header className="section-head home-rise">
              <div>
                <span className="kicker">A chave</span>
                <h2 className="section-title">A trilha até a taça</h2>
              </div>
              {principal ? (
                <Link className="btn btn--sm" href={`/torneio/${principal.id}`}>
                  chave completa →
                </Link>
              ) : null}
            </header>

            <div className="chave-wrap home-rise">
              <div className="chave-overflow">
                <div className="chave-track">
                  {rodadas.map((r) => (
                    <div className="chave-col" key={r.round}>
                      <div className="chave-col-head">
                        <b>{r.titulo}</b>
                        <span className="mono chave-count">{r.matches.length}</span>
                      </div>
                      {r.matches.map((m) => {
                        const a = meme(m.meme_a_id);
                        const b = meme(m.meme_b_id);
                        return (
                          <div
                            className="chave-row"
                            key={m.id}
                            style={{ "--hue": hueForId((a ?? b)?.id ?? 0) } as CSSProperties}
                          >
                            <span className="nm">
                              {a ? a.nome : nomeDoSlot(null, m, false)}
                            </span>
                            <span className="nm nm--b">
                              {b ? b.nome : nomeDoSlot(null, m, true)}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>
              <div className="chave-hint mono">
                role para o lado · os vencedores da fase de 64 avançam para a fase de 32
              </div>
            </div>
          </div>
        </section>
      ) : null}
    </HomeMotion>
  );
}