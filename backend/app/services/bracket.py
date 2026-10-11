import random
from typing import Any

from ..store import Estado, agora


def _ordem_sementes(tamanho: int) -> list[int]:
    """Ordem padrão de sementes para chave eliminatória (ex.: 8 -> 1,8,4,5,2,7,3,6)."""
    ordem = [1]
    while len(ordem) < tamanho:
        n = len(ordem) * 2
        nova: list[int] = []
        for x in ordem:
            nova.append(x)
            nova.append(n + 1 - x)
        ordem = nova
    return ordem


def definir_vencedor(estado: Estado, match: dict[str, Any], winner_id: int) -> None:
    """Marca o vencedor e o propaga para a próxima rodada (slot A/B pela paridade)."""
    match["winner_id"] = winner_id
    match["status"] = "finalizado"

    proximo = next(
        (
            m
            for m in estado.matches
            if m["tournament_id"] == match["tournament_id"]
            and m["round"] == match["round"] + 1
            and m["posicao"] == match["posicao"] // 2
        ),
        None,
    )
    if proximo is None:
        return
    if match["posicao"] % 2 == 0:
        proximo["meme_a_id"] = winner_id
    else:
        proximo["meme_b_id"] = winner_id


def gerar_torneio(
    estado: Estado,
    nome: str,
    meme_ids: list[int],
    seed: int,
    temporada: str = "1",
) -> dict[str, Any]:
    n = len(meme_ids)
    if n < 2:
        raise ValueError("São necessários ao menos 2 memes.")

    tamanho = 1
    while tamanho < n:
        tamanho *= 2
    rodadas = tamanho.bit_length() - 1

    rng = random.Random(seed)
    embaralhado = list(meme_ids)
    rng.shuffle(embaralhado)
    # byes vão para as melhores sementes, evitando confrontos "None vs None"
    slots: list[int | None] = [embaralhado[s - 1] if s <= n else None for s in _ordem_sementes(tamanho)]

    torneio = estado.adicionar(
        estado.tournaments,
        {
            "nome": nome,
            "temporada": temporada,
            "seed": seed,
            "tamanho": tamanho,
            "status": "em_andamento",
            "criado_em": agora(),
        },
    )

    matches: dict[tuple[int, int], dict[str, Any]] = {}
    for r in range(1, rodadas + 1):
        for p in range(tamanho >> r):
            match = estado.adicionar(
                estado.matches,
                {
                    "tournament_id": torneio["id"],
                    "round": r,
                    "posicao": p,
                    "meme_a_id": None,
                    "meme_b_id": None,
                    "winner_id": None,
                    "video_path": None,
                    "tiktok_url": None,
                    "publicado_em": None,
                    "deadline": None,
                    "status": "pendente",
                    "votos_a": 0,
                    "votos_b": 0,
                },
            )
            matches[(r, p)] = match

    for p in range(tamanho // 2):
        match = matches[(1, p)]
        match["meme_a_id"] = slots[2 * p]
        match["meme_b_id"] = slots[2 * p + 1]

    for p in range(tamanho // 2):
        match = matches[(1, p)]
        if match["meme_a_id"] is None and match["meme_b_id"] is None:
            match["status"] = "cancelado"
        elif match["meme_b_id"] is None:
            definir_vencedor(estado, match, match["meme_a_id"])
        elif match["meme_a_id"] is None:
            definir_vencedor(estado, match, match["meme_b_id"])

    return torneio


def criar_torneio_aguardando(
    estado: Estado,
    nome: str,
    meme_ids: list[int],
    tamanho: int,
    temporada: str = "2",
) -> dict[str, Any]:
    """Cria um torneio **incompleto** que aguarda o resto dos oponentes.

    Os memes já ficam reservados (``participantes``) e a chave só é sorteada
    quando o número de participantes alcançar ``tamanho``. Enquanto isso o
    torneio fica com ``status = "aguardando"`` e sem confrontos.
    """
    if tamanho < len(meme_ids):
        raise ValueError("tamanho não pode ser menor que o nº de memes.")

    return estado.adicionar(
        estado.tournaments,
        {
            "nome": nome,
            "temporada": temporada,
            "seed": None,
            "tamanho": tamanho,
            "status": "aguardando",
            "participantes": list(meme_ids),
            "criado_em": agora(),
        },
    )
