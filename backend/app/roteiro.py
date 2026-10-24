"""Roteiro do vídeo — ordem dos segmentos, transições, áudio e encode.

Fica em ``data/roteiro.json`` (separado do ``layout.json``, que o editor
regrava). Sem o arquivo valem os padrões abaixo. Segmentos possíveis em
``sequencia``:

- ``gancho``       — cartela gerada pelo kit (A vs B, rodada, "quem vence?");
- ``abertura``     — ``videos/abertura.mp4`` (vinheta da marca);
- ``a`` / ``b``    — os memes dentro da moldura, com título, selo e CTA;
- ``versus``       — ``videos/versus.mp4``;
- ``encerramento`` — ``videos/encerramento.mp4`` com os memes do confronto
  sobrepostos nos painéis "MEME 1 / MEME 2".

Segmentos cujo arquivo não existe são pulados.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from .config import CAMINHO_ROTEIRO

SEGMENTOS = ("gancho", "abertura", "a", "versus", "b", "encerramento")
TRANSICOES = (
    "corte", "fade", "fadeblack", "fadewhite", "wipeleft", "wiperight", "slideleft",
    "slideright", "circleopen", "circleclose", "pixelize", "radial", "zoomin",
)


@dataclass
class PaineisEncerramento:
    """Geometria (px em 1080x1920) dos painéis do ``encerramento.mp4``.

    Medida no vídeo atual; se o encerramento mudar, ajuste aqui. ``painel`` =
    interior onde vai a foto do meme, ``rotulo`` = caixa "MEME 1/2" coberta
    pelo nome, ``vs`` = círculo central (cx, cy, raio) que fica livre.
    """

    painel_a: tuple[int, int, int, int] = (176, 714, 306, 690)
    painel_b: tuple[int, int, int, int] = (598, 714, 306, 690)
    rotulo_a: tuple[int, int, int, int] = (196, 604, 286, 82)
    rotulo_b: tuple[int, int, int, int] = (604, 604, 286, 82)
    vs: tuple[int, int, int] = (540, 1000, 118)


@dataclass
class Roteiro:
    sequencia: list[str] = field(
        default_factory=lambda: ["gancho", "a", "versus", "b", "encerramento"]
    )
    # transição entre segmentos (xfade); "corte" = concat seco
    transicao: str = "fade"
    transicao_duracao: float = 0.25
    gancho_duracao: float = 1.6
    # áudio dos memes normalizado (EBU R128) — evita um meme estourar e o outro sumir
    loudnorm: bool = True
    lufs: float = -14.0
    # sobreposições durante os memes
    selo: bool = True              # badge "A"/"B" no canto do telão
    cta_segundos: float = 3.0      # "COMENTE A/B" nos últimos N s de cada meme (0 = off)
    barra_progresso: bool = True
    # aviso quando o vídeo passa do limite (não bloqueia)
    duracao_max: float = 60.0
    # encode
    crf: int = 18
    preset: str = "medium"
    audio_kbps: int = 192
    encerramento: PaineisEncerramento = field(default_factory=PaineisEncerramento)

    def normalizar(self) -> "Roteiro":
        self.sequencia = [s for s in self.sequencia if s in SEGMENTOS] or ["a", "b"]
        if self.transicao not in TRANSICOES:
            self.transicao = "fade"
        self.transicao_duracao = min(max(float(self.transicao_duracao), 0.0), 1.0)
        self.gancho_duracao = min(max(float(self.gancho_duracao), 0.8), 5.0)
        self.cta_segundos = max(float(self.cta_segundos), 0.0)
        self.crf = int(min(max(int(self.crf), 0), 51))
        return self

    def para_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def de_dict(cls, dados: dict[str, Any] | None) -> "Roteiro":
        dados = dict(dados or {})
        validos = {f.name for f in fields(cls)}
        paineis = dados.pop("encerramento", None) or {}
        kwargs = {k: v for k, v in dados.items() if k in validos}
        validos_p = {f.name for f in fields(PaineisEncerramento)}
        kwargs["encerramento"] = PaineisEncerramento(
            **{k: tuple(v) for k, v in paineis.items() if k in validos_p}
        )
        return cls(**kwargs).normalizar()


def carregar_roteiro(caminho: Path | None = None) -> Roteiro:
    """Lê ``data/roteiro.json``; ausente/inválido vira o padrão."""
    caminho = Path(caminho or CAMINHO_ROTEIRO)
    if not caminho.exists():
        return Roteiro()
    try:
        return Roteiro.de_dict(json.loads(caminho.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, TypeError, ValueError):
        return Roteiro()
