import Link from "next/link";

import { MemeCard } from "@/components/MemeCard";
import { Reveal } from "@/components/Reveal";
import { estatisticas, listarMemes, listarTorneios } from "@/lib/estado";

export default function Home() {
  const torneios = listarTorneios();
  const memes = listarMemes();
  const stats = estatisticas();
  const destaque = memes.slice(0, 8);
  const principal = torneios[0];

  return (
    <div className="wrap">
      <section className="hero">
        <Reveal>
          <span className="eyebrow">Chaveamento ao vivo</span>
        </Reveal>
        <Reveal delay={0.06}>
          <h1 className="display">
            Batalha de <span className="grad">Memes</span>
          </h1>
        </Reveal>
        <Reveal delay={0.12}>
          <p className="sub">
            Dois clipes de meme se enfrentam, o público vota e o vencedor avança.
            Aqui você acompanha o chaveamento completo, conhece a história de cada
            competidor e vai direto ao vídeo original.
          </p>
        </Reveal>
        <Reveal delay={0.18}>
          <div className="hero-actions">
            {principal ? (
              <Link className="btn btn--primary" href={`/torneio/${principal.id}`}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
                  <path d="M4 6h7v12H4" />
                  <path d="M13 9h7v6h-7" />
                  <path d="M11 12h2" />
                </svg>
                Ver o chaveamento
              </Link>
            ) : null}
            <Link className="btn" href="/competidores">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
                <rect x="3" y="3" width="7" height="7" rx="1.5" />
                <rect x="14" y="3" width="7" height="7" rx="1.5" />
                <rect x="3" y="14" width="7" height="7" rx="1.5" />
                <rect x="14" y="14" width="7" height="7" rx="1.5" />
              </svg>
              Todos os competidores
            </Link>
          </div>
        </Reveal>

        <div className="stats">
          {[
            { n: stats.totalMemes, l: "competidores" },
            { n: stats.totalTorneios, l: "temporadas" },
            { n: stats.totalConfrontos, l: "confrontos" },
            { n: stats.decididos, l: "decididos" },
          ].map((s, i) => (
            <Reveal key={s.l} delay={0.22 + i * 0.05}>
              <div className="stat glass">
                <div className="n">{s.n}</div>
                <div className="l">{s.l}</div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {torneios.length > 0 ? (
        <section className="section">
          <div className="row-between">
            <div>
              <span className="eyebrow">Temporadas</span>
              <h2 className="section-title">Torneios</h2>
            </div>
          </div>
          <div className="grid">
            {torneios.map((t, i) => (
              <Reveal key={t.id} delay={i * 0.05}>
                <Link className="glass tcard" href={`/torneio/${t.id}`}>
                  <span className="arrow" aria-hidden>
                    ↗
                  </span>
                  <div className="tname">{t.nome}</div>
                  <div className="tmeta">
                    <span className="badge">temporada {t.temporada}</span>
                    <span className="badge">{t.tamanho} vagas</span>
                    <span className="badge">{t.status.replace("_", " ")}</span>
                  </div>
                </Link>
              </Reveal>
            ))}
          </div>
        </section>
      ) : (
        <section className="section">
          <div className="empty-box">
            Nenhuma temporada ainda. Rode <code>python -m app.cli seed</code> e depois{" "}
            <code>python -m app.cli torneio --nome &quot;Temporada 1&quot;</code> e refaça
            o build.
          </div>
        </section>
      )}

      <section className="section">
        <div className="row-between">
          <div>
            <span className="eyebrow">Conheça o elenco</span>
            <h2 className="section-title">Competidores em destaque</h2>
          </div>
          <Link className="btn btn--sm" href="/competidores">
            Ver todos os {stats.totalMemes} →
          </Link>
        </div>
        <Reveal>
          <div className="grid">
            {destaque.map((m) => (
              <MemeCard key={m.id} meme={m} />
            ))}
          </div>
        </Reveal>
      </section>
    </div>
  );
}
