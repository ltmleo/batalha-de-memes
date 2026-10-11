import Link from "next/link";

import { listarTorneios } from "@/lib/api";
import type { Tournament } from "@/lib/types";

export default async function Home() {
  let torneios: Tournament[] = [];
  let erro = false;
  try {
    torneios = await listarTorneios();
  } catch {
    erro = true;
  }

  return (
    <main>
      <h1>Batalha de Memes</h1>
      <p className="sub">Chaveamento e acompanhamento das temporadas</p>

      {erro && (
        <div className="erro">
          Não foi possível falar com a API. Suba o backend (`uvicorn app.main:app --reload`)
          em http://localhost:8000.
        </div>
      )}

      {!erro && torneios.length === 0 && (
        <div className="erro">
          Nenhuma temporada ainda. Rode `POST /memes/seed` e depois `POST /tournaments`.
        </div>
      )}

      <div className="cards">
        {torneios.map((t) => (
          <Link key={t.id} className="card" href={`/torneio/${t.id}`}>
            <strong>{t.nome}</strong>
            <div style={{ marginTop: 8 }}>
              <span className="badge">temp. {t.temporada}</span>{" "}
              <span className="badge">{t.tamanho} memes</span>
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}
