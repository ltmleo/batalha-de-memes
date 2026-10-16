import Link from "next/link";

import { SuggestForm } from "@/components/SuggestForm";
import type { Tournament } from "@/lib/types";

export function SiteFooter({ torneios }: { torneios: Tournament[] }) {
  const t2 = torneios.find((t) => t.status === "aguardando");

  return (
    <footer className="footer">
      <div className="wrap">
        <div className="footer-grid">
          <div className="footer-col footer-brand">
            <Link href="/" className="brand" aria-label="Copa do Meme — início">
              <span className="logo" aria-hidden>
                <svg viewBox="0 0 48 48" fill="none">
                  <defs>
                    <linearGradient id="trofeu-ouro-rodape" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0" stopColor="#fff2b0" />
                      <stop offset="0.55" stopColor="#ffd93d" />
                      <stop offset="1" stopColor="#e09a00" />
                    </linearGradient>
                  </defs>
                  <path d="M12 8.5h24v9.5a12 12 0 0 1-24 0z" fill="url(#trofeu-ouro-rodape)" stroke="#8a5a00" strokeWidth="2" />
                  <circle cx="20" cy="16.4" r="1.9" fill="#4a2c00" />
                  <circle cx="28" cy="16.4" r="1.9" fill="#4a2c00" />
                  <path d="M20.4 20.6c1.7 2.1 5.5 2.1 7.2 0" stroke="#4a2c00" strokeWidth="1.8" strokeLinecap="round" />
                  <path d="M24 30v6M18 36.5h12l-1.4 5h-9.2z" stroke="#8a5a00" strokeWidth="2" strokeLinejoin="round" />
                </svg>
              </span>
              <b className="brand-nome">
                copa do <em>meme</em>
              </b>
            </Link>
            <p>
              A Copa do Mundo da internet: dois clipes entram, o público vota e só
              um meme leva a taça.
            </p>
            <nav className="footer-links" aria-label="Navegação do rodapé">
              <Link href="/#ringue">Batalhas</Link>
              <Link href="/#chave">Chaveamento</Link>
              <Link href="/#cemiterio">Cemitério dos caídos</Link>
              <Link href="/competidores">Competidores</Link>
              {t2 ? <Link href={`/torneio/${t2.id}`}>Fila de espera</Link> : null}
            </nav>
          </div>

          <div className="footer-col" id="var">
            <h3>O VAR da internet</h3>
            <ul className="rules">
              <li>Uso de bots resulta em desclassificação sumária e cancelamento no Twitter.</li>
              <li>Devolver o gol de mão do meme é regra; roubar crédito do autor é falta grave.</li>
              <li>Empate técnico? Prorrogação de memes até a cultura decidir.</li>
              <li>Vídeo com qualidade de VHS vale ouro; thumbnail roubada vale amarelo.</li>
            </ul>
          </div>

          <div className="footer-col">
            <h3>Envie seu candidato</h3>
            <p className="footer-note">
              Sugira um meme para a próxima edição. A votação da temporada atual
              corre primeiro.
            </p>
            <SuggestForm />
          </div>
        </div>

        <div className="footer-bottom">
          <span>Copa do Meme · site estático gerado a partir de backend/data/estado.json</span>
          <span className="mono">
            {torneios.length} temporadas ·{" "}
            {torneios.reduce((s, t) => s + (t.participantes?.length ?? 0), 0)} reservas
          </span>
        </div>
      </div>
    </footer>
  );
}