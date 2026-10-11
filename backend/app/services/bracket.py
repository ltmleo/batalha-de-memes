import random

from sqlalchemy.orm import Session

from .. import models


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


def definir_vencedor(db: Session, match: models.Match, winner_id: int) -> None:
    """Marca o vencedor e o propaga para a próxima rodada (slot A/B pela paridade)."""
    match.winner_id = winner_id
    match.status = "finalizado"

    proximo = (
        db.query(models.Match)
        .filter_by(
            tournament_id=match.tournament_id,
            round=match.round + 1,
            posicao=match.posicao // 2,
        )
        .first()
    )
    if proximo is None:
        return
    if match.posicao % 2 == 0:
        proximo.meme_a_id = winner_id
    else:
        proximo.meme_b_id = winner_id


def gerar_torneio(
    db: Session,
    nome: str,
    meme_ids: list[int],
    seed: int,
    temporada: str = "1",
) -> models.Tournament:
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

    torneio = models.Tournament(
        nome=nome, temporada=temporada, seed=seed, tamanho=tamanho, status="em_andamento"
    )
    db.add(torneio)
    db.flush()

    matches: dict[tuple[int, int], models.Match] = {}
    for r in range(1, rodadas + 1):
        for p in range(tamanho >> r):
            match = models.Match(tournament_id=torneio.id, round=r, posicao=p, status="pendente")
            db.add(match)
            matches[(r, p)] = match
    db.flush()

    for p in range(tamanho // 2):
        match = matches[(1, p)]
        match.meme_a_id = slots[2 * p]
        match.meme_b_id = slots[2 * p + 1]
    db.flush()

    for p in range(tamanho // 2):
        match = matches[(1, p)]
        if match.meme_a_id is None and match.meme_b_id is None:
            match.status = "cancelado"
        elif match.meme_b_id is None:
            definir_vencedor(db, match, match.meme_a_id)
        elif match.meme_a_id is None:
            definir_vencedor(db, match, match.meme_b_id)

    db.commit()
    db.refresh(torneio)
    return torneio
