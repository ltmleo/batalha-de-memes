import Link from "next/link";

import { SuggestForm } from "@/components/SuggestForm";
import type { Tournament } from "@/lib/types";

export function SiteFooter({ torneios }: { torneios: Tournament[] }) {
  const principal =
    torneios.find((t) => t.status !== "aguardando") ?? torneios[0];
  const t2 = torneios.find((t) => t.status === "aguardando");

  return (
    <footer className="footer">
      <div className="wrap">
        <div className="footer-grid">
          <div className="footer-col footer-brand">
            <Link href="/" className="brand" aria-label="Batalha de Memes — início">
              <span className="logo" aria-hidden>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                  <path d="M12 3v18" />
                  <path d="M4 7h8" />
                  <path d="M4 17h8" />
                  <path d="M12 12h8" />
                  <path d="M20 9.5v5" />
                </svg>
              </span>
              <b>Batalha de Memes</b>
            </Link>
            <p>
              A Copa do Mundo da internet: dois clipes entram, o público vota e só
              um meme leva a taça.
            </p>
            <nav className="footer-links" aria-label="Navegação do rodapé">
              {principal ? (
                <Link href={`/torneio/${principal.id}`}>Chaveamento</Link>
              ) : null}
              <Link href="/competidores">Competidores</Link>
              {t2 ? <Link href={`/torneio/${t2.id}`}>Fila de espera</Link> : null}
            </nav>
          </div>

          <div className="footer-col">
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
          <span>Batalha de Memes · site estático gerado a partir de backend/data/estado.json</span>
          <span className="mono">
            {torneios.length} temporadas ·{" "}
            {torneios.reduce((s, t) => s + (t.participantes?.length ?? 0), 0)} reservas
          </span>
        </div>
      </div>
    </footer>
  );
}