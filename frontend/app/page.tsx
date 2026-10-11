import Link from "next/link";

import { listarTorneios } from "@/lib/estado";

export default function Home() {
  const torneios = listarTorneios();

  return (
    <main>
      <h1>Batalha de Memes</h1>
      <p className="sub">Chaveamento e acompanhamento das temporadas</p>

      {torneios.length === 0 && (
        <div className="erro">
          Nenhuma temporada ainda. Rode `python -m app.cli seed` e depois
          `python -m app.cli torneio --nome &quot;Temporada 1&quot;` e refaça o build.
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
