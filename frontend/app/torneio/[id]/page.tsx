import Link from "next/link";
import { notFound } from "next/navigation";

import { AguardandoView } from "@/components/AguardandoView";
import { Reveal } from "@/components/Reveal";
import { TorneioExplorer } from "@/components/TorneioExplorer";
import {
  estatisticas,
  estaAguardando,
  listarTorneios,
  memesDoTorneio,
  obterTorneio,
} from "@/lib/estado";

// Export estático: pré-gera uma página por temporada existente em estado.json.
export function generateStaticParams() {
  return listarTorneios().map((t) => ({ id: String(t.id) }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const torneio = obterTorneio(Number(id));
  if (!torneio) return { title: "Torneio não encontrado — Batalha de Memes" };
  return {
    title: `${torneio.nome} — Batalha de Memes`,
    description: `Chaveamento completo da ${torneio.nome}: ${torneio.tamanho} vagas, todas as rodadas e o caminho de cada competidor.`,
  };
}

export default async function TorneioPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const torneio = obterTorneio(Number(id));
  if (!torneio) notFound();

  const aguardando = estaAguardando(torneio);
  const competidores = memesDoTorneio(torneio);
  const stats = estatisticas(torneio);

  const cartoes = aguardando
    ? [
        { n: competidores.length, l: "na espera" },
        { n: Math.max(torneio.tamanho - competidores.length, 0), l: "vagas abertas" },
        { n: torneio.tamanho, l: "vagas" },
      ]
    : [
        { n: stats.totalMemes, l: "competidores" },
        { n: stats.totalConfrontos, l: "confrontos" },
        { n: stats.decididos, l: "decididos" },
        { n: torneio.tamanho, l: "vagas" },
      ];

  return (
    <div className="wrap" style={{ paddingTop: 40 }}>
      <Reveal>
        <Link href="/" className="breadcrumb">
          ← temporadas
        </Link>
        <span className="eyebrow">Temporada {torneio.temporada}</span>
        <h1 className="display" style={{ fontSize: "clamp(1.9rem, 4.5vw, 3rem)" }}>
          {torneio.nome}
        </h1>
        <p className="sub">
          {aguardando
            ? `${competidores.length} competidores reservados aguardando o resto dos oponentes para completar a chave de ${torneio.tamanho} vagas.`
            : `Chaveamento de ${torneio.tamanho} vagas com ${stats.totalMemes} competidores. Clique em qualquer meme para destacar o caminho dele até a final — ou abra os cards para ver a história e o vídeo original.`}
        </p>
      </Reveal>

      <Reveal delay={0.06}>
        <div className="stats" style={{ marginTop: 26 }}>
          {cartoes.map((s, i) => (
            <div key={`${s.l}-${i}`} className="stat glass">
              <div className="n">{s.n}</div>
              <div className="l">{s.l}</div>
            </div>
          ))}
        </div>
      </Reveal>

      <div style={{ marginTop: 30 }}>
        {aguardando ? (
          <AguardandoView torneio={torneio} competidores={competidores} />
        ) : (
          <TorneioExplorer detail={torneio} competidores={competidores} />
        )}
      </div>
    </div>
  );
}
