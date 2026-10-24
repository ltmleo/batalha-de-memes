from app.services.bracket import _ordem_sementes, definir_vencedor, gerar_torneio
from app.store import Estado


def _torneio(n: int, seed: int = 7) -> tuple[Estado, dict]:
    estado = Estado({"memes": [{"id": i, "nome": f"m{i}"} for i in range(1, n + 1)]})
    torneio = gerar_torneio(estado, "T", list(range(1, n + 1)), seed)
    return estado, torneio


def _pares(estado: Estado) -> list[tuple]:
    return [(m["meme_a_id"], m["meme_b_id"]) for m in estado.matches]


def test_ordem_sementes_8():
    assert _ordem_sementes(8) == [1, 8, 4, 5, 2, 7, 3, 6]


def test_sorteio_reprodutivel():
    a, _ = _torneio(8, seed=42)
    b, _ = _torneio(8, seed=42)
    assert _pares(a) == _pares(b)


def test_estrutura_completa():
    estado, torneio = _torneio(8)
    assert torneio["tamanho"] == 8
    assert [m["round"] for m in estado.matches].count(1) == 4
    assert len(estado.matches) == 7  # 4 + 2 + 1


def test_bye_avanca_automaticamente():
    estado, _ = _torneio(6)
    r1 = [m for m in estado.matches if m["round"] == 1]
    byes = [m for m in r1 if m["meme_b_id"] is None or m["meme_a_id"] is None]
    assert len(byes) == 2
    assert all(m["status"] == "finalizado" and m["winner_id"] for m in byes)
    r2 = {m[k] for m in estado.matches if m["round"] == 2 for k in ("meme_a_id", "meme_b_id")}
    assert {m["winner_id"] for m in byes} <= r2


def test_propagacao_e_final_encerra_torneio():
    estado, torneio = _torneio(4)
    r1 = sorted((m for m in estado.matches if m["round"] == 1), key=lambda m: m["posicao"])
    definir_vencedor(estado, r1[0], r1[0]["meme_a_id"])
    definir_vencedor(estado, r1[1], r1[1]["meme_b_id"])
    final = next(m for m in estado.matches if m["round"] == 2)
    assert (final["meme_a_id"], final["meme_b_id"]) == (r1[0]["meme_a_id"], r1[1]["meme_b_id"])
    definir_vencedor(estado, final, final["meme_a_id"])
    assert torneio["status"] == "finalizado"
