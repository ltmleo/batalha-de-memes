import pytest

from app.services import vote_parser as vp

A = vp.aliases("Luiza Marilac")
B = vp.aliases("E Ai Gay")


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("A", "A"), ("b!!", "B"), ("🅰️", "A"), ("voto no B", "B"), ("time a", "A"),
        ("meme 1", "A"), ("2", "B"), ("vai B", "B"), ("marilac demais", "A"),
        ("A ou B?", None), ("acho que a", None), ("kkkkk", None),
        ("Luiza > e ai gay", None),
    ],
)
def test_extrair_escolha(texto, esperado):
    assert vp.extrair_escolha(texto, A, B) == esperado


def _c(usuario, texto, quando=None):
    return vp.Comentario(usuario, texto, quando)


def test_um_voto_por_usuario_primeiro_valido():
    res = vp.apurar([
        _c("ana", "kkkk", "2026-10-01T10:00:00Z"),
        _c("ana", "A", "2026-10-01T10:01:00Z"),
        _c("ana", "B", "2026-10-01T10:02:00Z"),
        _c("bia", "b", "2026-10-01T10:03:00Z"),
    ])
    assert (res.votos_a, res.votos_b, res.duplicados, res.invalidos) == (1, 1, 1, 1)


def test_fora_do_prazo():
    res = vp.apurar(
        [_c("ana", "A", "2026-10-01T09:00:00Z"), _c("bia", "A", "2026-10-01T11:00:00Z"),
         _c("caio", "B", "2026-10-03T11:00:00Z")],
        publicado_em="2026-10-01T10:00:00Z", deadline="2026-10-02T10:00:00Z",
    )
    assert (res.votos_a, res.votos_b, res.fora_do_prazo) == (1, 0, 2)


def test_empate_desfeito_pelo_seed_e_reprodutivel():
    res = vp.apurar([_c("ana", "A"), _c("bia", "B")])
    match = {"id": 9, "meme_a_id": 1, "meme_b_id": 2}
    primeiro = vp.vencedor(res, match, 42)
    assert primeiro in (1, 2)
    assert all(vp.vencedor(res, match, 42) == primeiro for _ in range(5))


def test_ler_txt(tmp_path):
    arq = tmp_path / "c.txt"
    arq.write_text("ana: A\nbia\tvoto no b\nb\n", encoding="utf-8")
    comentarios = vp.ler_comentarios(arq)
    assert [c.usuario for c in comentarios] == ["ana", "bia", "linha-3"]
    assert vp.apurar(comentarios).votos_b == 2


def test_ler_json_epoch(tmp_path):
    arq = tmp_path / "c.json"
    arq.write_text('[{"user": "x", "text": "a", "create_time": 1760000000}]', encoding="utf-8")
    (c,) = vp.ler_comentarios(arq)
    assert c.criado_em.startswith("2025-10-09") and c.texto == "a"
