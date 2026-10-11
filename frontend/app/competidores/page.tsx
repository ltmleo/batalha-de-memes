import Link from "next/link";

import { CompetidoresGrid } from "@/components/CompetidoresGrid";
import { Reveal } from "@/components/Reveal";
import { listarMemes } from "@/lib/estado";

export const metadata = {
  title: "Competidores — Batalha de Memes",
  description: "Todos os memes que disputam a Batalha de Memes, com história e vídeo original.",
};

export default function CompetidoresPage() {
  const memes = listarMemes();

  return (
    <div className="wrap" style={{ paddingTop: 40 }}>
      <Reveal>
        <Link href="/" className="breadcrumb">
          ← início
        </Link>
        <span className="eyebrow">Elenco completo</span>
        <h1 className="display" style={{ fontSize: "clamp(1.9rem, 4.5vw, 3rem)" }}>
          Competidores
        </h1>
        <p className="sub">
          {memes.length} memes prontos para entrar na arena. Busque, filtre por tag e
          abra o card para ver a história e o vídeo original.
        </p>
      </Reveal>

      <div style={{ marginTop: 26 }}>
        <CompetidoresGrid memes={memes} />
      </div>
    </div>
  );
}
