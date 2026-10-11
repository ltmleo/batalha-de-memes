import Link from "next/link";
import { notFound } from "next/navigation";

import { Bracket } from "@/components/Bracket";
import { listarTorneios, obterTorneio } from "@/lib/estado";

// Export estático: pré-gera uma página por temporada existente em estado.json.
export function generateStaticParams() {
  return listarTorneios().map((t) => ({ id: String(t.id) }));
}

export default async function TorneioPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const torneio = obterTorneio(Number(id));
  if (!torneio) notFound();

  return (
    <main>
      <p>
        <Link href="/" style={{ color: "#9a9aa8" }}>
          &larr; temporadas
        </Link>
      </p>
      <h1>{torneio.nome}</h1>
      <p className="sub">
        temporada {torneio.temporada} · {torneio.tamanho} memes · seed {torneio.seed}
      </p>

      <Bracket detail={torneio} />
    </main>
  );
}
