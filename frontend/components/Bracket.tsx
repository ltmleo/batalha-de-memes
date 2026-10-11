import type { Match, TournamentDetail } from "@/lib/types";

function Slot({
  nome,
  votos,
  vencedor,
  bye,
}: {
  nome: string | null;
  votos: number;
  vencedor: boolean;
  bye: boolean;
}) {
  if (!nome) {
    return (
      <div className="slot">
        <span className="empty">{bye ? "bye" : "a definir"}</span>
      </div>
    );
  }
  return (
    <div className={`slot${vencedor ? " win" : ""}`}>
      <span>{nome}</span>
      <span className="score">{votos}</span>
    </div>
  );
}

function MatchCard({ match, nomes }: { match: Match; nomes: Map<number, string> }) {
  const nomeA = match.meme_a_id ? nomes.get(match.meme_a_id) ?? "?" : null;
  const nomeB = match.meme_b_id ? nomes.get(match.meme_b_id) ?? "?" : null;
  const bye = match.status === "finalizado" && (nomeA === null || nomeB === null);

  return (
    <div className="match">
      <Slot
        nome={nomeA}
        votos={match.votos_a}
        vencedor={match.winner_id !== null && match.winner_id === match.meme_a_id}
        bye={bye}
      />
      <Slot
        nome={nomeB}
        votos={match.votos_b}
        vencedor={match.winner_id !== null && match.winner_id === match.meme_b_id}
        bye={bye}
      />
    </div>
  );
}

export function Bracket({ detail }: { detail: TournamentDetail }) {
  const nomes = new Map(detail.memes.map((m) => [m.id, m.nome]));
  const rodadas = [...new Set(detail.matches.map((m) => m.round))].sort((a, b) => a - b);
  const totalRodadas = rodadas.length;

  return (
    <div className="bracket">
      {rodadas.map((r) => {
        const doRound = detail.matches
          .filter((m) => m.round === r)
          .sort((a, b) => a.posicao - b.posicao);
        const titulo =
          r === totalRodadas ? "Final" : r === totalRodadas - 1 ? "Semifinal" : `Rodada ${r}`;
        return (
          <div className="round" key={r}>
            <div className="round-title">{titulo}</div>
            {doRound.map((m) => (
              <MatchCard key={m.id} match={m} nomes={nomes} />
            ))}
          </div>
        );
      })}
    </div>
  );
}
