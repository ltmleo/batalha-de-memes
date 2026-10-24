"""Grafo do ffmpeg montado pelo assembler — sem renderizar nada."""

from pathlib import Path

import pytest

from app.layout import Layout
from app.roteiro import Roteiro
from app.services import assembler


@pytest.fixture
def capturar(monkeypatch, tmp_path):
    duracoes = {"g.mp4": 1.6, "a.mp4": 10.0, "vs.mp4": 2.0, "b.mp4": 8.0}
    for nome in duracoes:
        (tmp_path / nome).write_bytes(b"")
    monkeypatch.setattr(assembler, "resolver_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(assembler, "_duracao", lambda p, *_: duracoes[Path(p).name])
    monkeypatch.setattr(assembler, "_tem_audio", lambda p, *_: Path(p).name != "vs.mp4")
    monkeypatch.setattr(assembler.titulo, "caminho_png", lambda *a, **k: tmp_path / "t.png")
    chamadas = []

    class _Proc:
        returncode, stderr = 0, ""

    monkeypatch.setattr(assembler.subprocess, "run",
                        lambda cmd, **kw: chamadas.append(cmd) or _Proc())
    return tmp_path, chamadas


def _grafo(cmd):
    return cmd[cmd.index("-filter_complex") + 1]


def test_xfade_offsets_e_duracao_total(capturar):
    pasta, chamadas = capturar
    segs = [assembler.Segmento(pasta / "g.mp4"),
            assembler.Segmento(pasta / "a.mp4", "meme", titulo="A", normalizar_audio=True),
            assembler.Segmento(pasta / "vs.mp4"),
            assembler.Segmento(pasta / "b.mp4", "meme", titulo="B", normalizar_audio=True)]
    assembler.montar_video(segs, pasta / "out.mp4", Layout(), Roteiro(transicao_duracao=0.25),
                           moldura=None)
    cmd = chamadas[0]
    grafo = _grafo(cmd)
    assert "offset=1.350" in grafo            # 1.6 - 0.25
    assert "offset=11.100" in grafo           # 1.6 + 10 - 2*0.25
    assert "offset=12.850" in grafo
    saida = cmd[cmd.index("-map"):]           # opções de saída (as de entrada vêm antes)
    assert saida[saida.index("-t") + 1] == "20.850"  # 21.6 - 3*0.25
    assert grafo.count("loudnorm") == 2       # só os memes
    assert "anullsrc" in grafo                # versus sem áudio vira silêncio


def test_corte_seco_usa_concat(capturar):
    pasta, chamadas = capturar
    segs = [assembler.Segmento(pasta / "a.mp4"), assembler.Segmento(pasta / "b.mp4")]
    assembler.montar_video(segs, pasta / "out.mp4", Layout(),
                           Roteiro(transicao="corte", barra_progresso=False), moldura=None)
    grafo = _grafo(chamadas[0])
    assert "concat=n=2" in grafo and "xfade" not in grafo


def test_cta_nos_ultimos_segundos(capturar):
    pasta, chamadas = capturar
    cta = assembler.Sobreposicao(pasta / "cta.png", inicio=-3)
    segs = [assembler.Segmento(pasta / "a.mp4", "meme", sobreposicoes=[cta])]
    assembler.montar_video(segs, pasta / "out.mp4", Layout(), Roteiro(), moldura=None)
    assert "between(t,7.000,10.000)" in _grafo(chamadas[0])


def test_sequencia_pula_arquivos_ausentes(tmp_path):
    a, b = tmp_path / "a.mp4", tmp_path / "b.mp4"
    segs = assembler.segmentos_do_roteiro(
        Roteiro(sequencia=["gancho", "abertura", "a", "versus", "b"]), a, b, "A", "B", None,
        abertura=tmp_path / "nao.mp4", versus=None,
    )
    assert [s.fonte for s in segs] == [a, b]
