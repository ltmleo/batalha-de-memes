"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { hueStyle } from "@/components/MemeAvatar";
import { FotoMeme } from "@/components/FotoMeme";
import { VideoLinks } from "@/components/VideoLinks";
import { iniciais } from "@/lib/format";
import { votosTexto } from "@/lib/home";

export type LadoDuelo = {
  id: number;
  nome: string;
  epiteto: string;
  votos: number;
  /** URL do vídeo original — de onde sai a foto do meme. */
  youtube?: string | null;
};

type Comentario = { autor: string; texto: string };
type Lado = "a" | "b";

const TORCIDA: Comentario[] = [
  { autor: "@memelord_92", texto: "esse meme é patrimônio histórico 🏛️" },
  { autor: "@dona.xepa", texto: "votei três vezes, me processem" },
  { autor: "@ze_do_baque", texto: "clássico é clássico, chefe" },
  { autor: "@edit_no_capricho", texto: "o replay em slow motion me quebrou" },
  { autor: "@tia.do.pave", texto: "minha filha me ensinou a votar, agora tô viciada" },
  { autor: "@nerdao_42", texto: "tecnicamente esse aqui tem mais camadas" },
  { autor: "@futebol_e_memes", texto: "VAR, revisa esse placar 🎥" },
  { autor: "@claudia.do.grau", texto: "tô rindo desde ontem kkkkk" },
  { autor: "@anonimo_do_tiktok", texto: "o outro é bom, mas esse é atemporal" },
  { autor: "@girl_da_meme", texto: "ISSO É BRASIL 🇧🇷🔥" },
  { autor: "@tiozinho_gamer", texto: "a arena tá pegando fogo, gente" },
  { autor: "@mestre_do_edit", texto: "quem chega aqui já é campeão" },
  { autor: "@saudades_do_vhs", texto: "qualidade de VHS e ainda assim perfeito" },
  { autor: "@memes_do_zap", texto: "encaminhei no grupo da família ✅" },
  { autor: "@mesa_de_debate", texto: "esse debate tá uma porra (no bom sentido)" },
  { autor: "@lenda_viva", texto: "impossível escolher, mas escolhi" },
];

const VOTO_PROPRIO: Comentario = {
  autor: "@você",
  texto: "voto registrado direto da arquibancada 🎟️",
};

const CORES_BURST = ["#ffd93d", "#ff4757", "#2f7bff", "#7c3aed", "#ffffff"];

/** Comentários iniciais determinísticos (iguais no servidor e no cliente). */
function feedInicial(semente: number): Record<Lado, Comentario[]> {
  const n = TORCIDA.length;
  const pega = (i: number) => TORCIDA[((i % n) + n) % n];
  return {
    a: [pega(semente * 3 + 1), pega(semente * 3 + 6)],
    b: [pega(semente * 3 + 3), pega(semente * 3 + 9)],
  };
}

function hueDoAutor(autor: string): number {
  let h = 0;
  for (let i = 0; i < autor.length; i++) h = (h * 31 + autor.charCodeAt(i)) % 360;
  return h;
}

type Burst = { lado: Lado; id: number; partes: { dx: number; dy: number; rot: number; atraso: number; cor: string; tam: number }[] };

export function RingueDuelo({
  matchId,
  fase,
  confronto,
  a,
  b,
  tiktok,
  instagram,
  youtube,
}: {
  matchId: number;
  fase: string;
  confronto: number;
  a: LadoDuelo;
  b: LadoDuelo;
  tiktok?: string | null;
  instagram?: string | null;
  youtube?: string | null;
}) {
  const [votos, setVotos] = useState({ a: a.votos, b: b.votos });
  const [voto, setVoto] = useState<Lado | null>(null);
  const [feed, setFeed] = useState(() => feedInicial(matchId));
  const [burst, setBurst] = useState<Burst | null>(null);
  const burstTimer = useRef<number | null>(null);

  // Torcida "ao vivo": novas mensagens entram enquanto o duelo está aberto.
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = window.setInterval(() => {
      setFeed((atual) => {
        const lado: Lado = Math.random() < 0.5 ? "a" : "b";
        const novo = TORCIDA[Math.floor(Math.random() * TORCIDA.length)];
        return { ...atual, [lado]: [...atual[lado], novo].slice(-4) };
      });
    }, 3400);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    return () => {
      if (burstTimer.current) window.clearTimeout(burstTimer.current);
    };
  }, []);

  const total = votos.a + votos.b;
  const pctA = total > 0 ? Math.round((votos.a / total) * 100) : 50;
  const pct: Record<Lado, number> = { a: pctA, b: 100 - pctA };

  function votar(lado: Lado) {
    if (voto) return;
    setVoto(lado);
    setVotos((v) => ({ ...v, [lado]: v[lado] + 1 }));
    setFeed((f) => ({ ...f, [lado]: [...f[lado], VOTO_PROPRIO].slice(-4) }));
    const partes = Array.from({ length: 14 }, (_, i) => ({
      dx: (Math.random() * 2 - 1) * 84,
      dy: -(24 + Math.random() * 96),
      rot: Math.random() * 540,
      atraso: Math.random() * 0.09,
      cor: CORES_BURST[i % CORES_BURST.length],
      tam: 5 + (i % 3) * 3,
    }));
    setBurst({ lado, id: Date.now(), partes });
    if (burstTimer.current) window.clearTimeout(burstTimer.current);
    burstTimer.current = window.setTimeout(() => setBurst(null), 1100);
  }

  const lados: { lado: Lado; dado: LadoDuelo }[] = [
    { lado: "a", dado: a },
    { lado: "b", dado: b },
  ];

  const renderLado = ({ lado, dado }: { lado: Lado; dado: LadoDuelo }) => (
    <div
      key={lado}
      className={`duelo-lado duelo-lado--${lado}${voto === lado ? " is-votado" : ""}`}
      style={hueStyle(dado.id)}
    >
      <Link
        className="duelo-id"
        href={`/meme/${dado.id}`}
        title={`Abrir o card de ${dado.nome}`}
      >
        <FotoMeme
          id={dado.id}
          nome={dado.nome}
          youtube={dado.youtube}
          className="avatar--xl"
          decorativo
        />
        <h3 className="duelo-nome">{dado.nome}</h3>
        <span className="duelo-epiteto mono">({dado.epiteto})</span>
      </Link>

      <div
        className="voto-barra"
        role="img"
        aria-label={`${pct[lado]}% dos votos para ${dado.nome}`}
      >
        <span className="voto-track">
          <span className="voto-fill" style={{ width: `${pct[lado]}%` }} />
        </span>
        <span className="voto-placar">
          <b>{pct[lado]}%</b>
          <span className="mono">{votosTexto(votos[lado])} votos</span>
        </span>
      </div>

      <div className="voto-acao">
        <button
          type="button"
          className="btn-votar"
          disabled={voto !== null}
          onClick={() => votar(lado)}
        >
          {voto === lado ? "voto registrado ✓" : "votar"}
        </button>
        {burst && burst.lado === lado ? (
          <span className="confete-burst" key={burst.id} aria-hidden>
            {burst.partes.map((p, i) => (
              <i
                key={i}
                style={
                  {
                    "--dx": `${p.dx}px`,
                    "--dy": `${p.dy}px`,
                    "--rot": `${p.rot}deg`,
                    "--atraso": `${p.atraso}s`,
                    "--cor": p.cor,
                    "--tam": `${p.tam}px`,
                  } as React.CSSProperties
                }
              />
            ))}
          </span>
        ) : null}
      </div>

      <div className="torcida">
        <div className="torcida-titulo mono">
          <span className="dot" aria-hidden /> torcida ao vivo
        </div>
        <ul className="torcida-feed">
          {feed[lado].map((c, i) => (
            <li className="cmt" key={`${i}-${c.autor}`}>
              <span
                className="cmt-av"
                style={{ "--hue": hueDoAutor(c.autor) } as React.CSSProperties}
                aria-hidden
              >
                {iniciais(c.autor.replace("@", ""))}
              </span>
              <span className="cmt-corpo">
                <b>{c.autor}</b>
                <span>{c.texto}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>

      <Link className="duelo-card-link mono" href={`/meme/${dado.id}`}>
        abrir card ↗
      </Link>
    </div>
  );

  return (
    <article className="duelo home-scale">
      <header className="duelo-topo">
        <span className="badge badge--live">
          <span className="dot" aria-hidden /> ao vivo
        </span>
        <span className="mono duelo-fase">{fase}</span>
        <span className="mono duelo-conf">confronto #{confronto}</span>
        <span className="mono duelo-total">{votosTexto(total)} votos na urna</span>
      </header>

      <div className="duelo-palco">
        <div className="arena-luzes" aria-hidden>
          <i />
          <i />
          <i />
        </div>
        <div className="emoji-campo" aria-hidden>
          <span style={{ "--x": "6%", "--dur": "9s", "--atraso": "0s" } as React.CSSProperties}>😂</span>
          <span style={{ "--x": "18%", "--dur": "11s", "--atraso": "1.4s" } as React.CSSProperties}>🏆</span>
          <span style={{ "--x": "31%", "--dur": "8s", "--atraso": "2.6s" } as React.CSSProperties}>🔥</span>
          <span style={{ "--x": "47%", "--dur": "12s", "--atraso": "0.8s" } as React.CSSProperties}>😍</span>
          <span style={{ "--x": "63%", "--dur": "10s", "--atraso": "3.2s" } as React.CSSProperties}>🎉</span>
          <span style={{ "--x": "78%", "--dur": "9.5s", "--atraso": "1.9s" } as React.CSSProperties}>😂</span>
          <span style={{ "--x": "90%", "--dur": "13s", "--atraso": "2.2s" } as React.CSSProperties}>❤️</span>
        </div>

        <div className="duelo-lados">
          {renderLado(lados[0])}
          <span className="duelo-vs" aria-hidden>
            <span className="vs-chama" />
            <span className="vs-txt">VS</span>
          </span>
          {renderLado(lados[1])}
        </div>
      </div>

      <div className="duelo-videos">
        <span className="duelo-videos-rot mono">assista e vote nas redes</span>
        <VideoLinks
          tiktok={tiktok}
          instagram={instagram}
          youtube={youtube}
          msgVazio="vídeos em breve"
        />
      </div>

      <footer className="duelo-rodape mono">
        <span>votação na arena · fecha domingo às 23h59</span>
        <span>o perdedor vai direto pro cemitério dos caídos 🪦</span>
      </footer>
    </article>
  );
}
