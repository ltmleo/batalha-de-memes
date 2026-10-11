import Link from "next/link";

import { hueStyle } from "@/components/MemeAvatar";
import type { Meme, TournamentDetail } from "@/lib/types";

/**
 * Torneio que ainda aguarda oponentes: os memes reservados ficam numa lista
 * separada, com o contador `n/total` de vagas preenchidas.
 */
export function AguardandoView({
  torneio,
  competidores,
}: {
  torneio: TournamentDetail;
  competidores: Meme[];
}) {
  const total = torneio.tamanho;
  const naEspera = competidores.length;
  const faltam = Math.max(total - naEspera, 0);

  return (
    <section className="aguardando" aria-labelledby="aguardando-titulo">
      <header className="aguardando-head">
        <h2 id="aguardando-titulo" className="aguardando-title">
          Aguardando novos memes
        </h2>
        <span className="aguardando-tag">temporada {torneio.temporada}</span>
        <span className="aguardando-count">
          {naEspera}/{total}
        </span>
      </header>
      <p className="aguardando-note">
        Estes {naEspera} memes já estão reservados e aguardam o resto dos oponentes para
        completar as {total} vagas — faltam {faltam}. Assim que a chave fechar, os confrontos
        aparecem automaticamente.
      </p>
      <ul className="aguardando-list">
        {competidores.map((m) => (
          <li key={m.id} className="aguardando-row">
            <Link
              href={`/meme/${m.id}`}
              className="aguardando-link"
              style={hueStyle(m.id)}
              title={`Abrir o card de ${m.nome}`}
            >
              {m.nome}
            </Link>
            <span className="aguardando-status">na espera</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
