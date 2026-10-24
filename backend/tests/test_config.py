from app.layout import Layout
from app.roteiro import Roteiro
from app.services.validacao import Relatorio, validar_meme


def test_layout_normaliza_e_pixels_pares():
    layout = Layout(x=-1, y=0.5, l=2, a=0.333, preenchimento="x").normalizar()
    assert layout.x == 0 and layout.l == 1.0 and layout.preenchimento == "cover"
    assert layout.px_a() % 2 == 0


def test_layout_ida_e_volta():
    layout = Layout(x=0.2, titulo_fonte=80)
    assert Layout.de_dict(layout.para_dict()) == layout.normalizar()


def test_roteiro_filtra_invalidos():
    r = Roteiro.de_dict({"sequencia": ["gancho", "xyz", "a"], "transicao": "nada",
                         "encerramento": {"vs": [1, 2, 3]}})
    assert r.sequencia == ["gancho", "a"]
    assert r.transicao == "fade"
    assert r.encerramento.vs == (1, 2, 3)


def test_validar_meme():
    rel = Relatorio()
    validar_meme({"nome": "x", "youtube_url": "https://youtu.be/abcdefg", "inicio": 5, "fim": 2},
                 "t", rel)
    validar_meme({"nome": "y", "youtube_url": "https://www.youtube.com/results?search_query=y",
                  "inicio": 0, "fim": 5}, "t", rel)
    assert len(rel.erros) == 1 and "trecho inválido" in rel.erros[0]
    assert len(rel.avisos) == 1 and "busca" in rel.avisos[0]
