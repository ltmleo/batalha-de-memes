import Link from "next/link";

import { Bracket } from "@/components/Bracket";
import { obterTorneio } from "@/lib/api";

export default async function TorneioPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const torneio = await obterTorneio(Number(id));

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
