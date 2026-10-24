"""Layout da montagem — geometria dentro da moldura (``data/layout.json``).

Os valores são **frações** de 1080x1920 (0.0–1.0), então continuam válidos
qualquer que seja a resolução de saída. O editor desktop grava este arquivo e o
``assembler`` lê como padrão: sem arquivo, os valores são os históricos
(área do "telão" 11%–89% × 25%–81%, preenchimento por recorte central).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from .config import CAMINHO_LAYOUT

LARGURA = 1080
ALTURA = 1920


def _par(valor: int) -> int:
    """Arredonda para baixo em pixels pares (exigência do yuv420p/h264)."""
    return max(2, valor - (valor % 2))


@dataclass
class Layout:
    """Geometria da área do clipe dentro da moldura.

    ``x``/``y`` são a borda superior-esquerda da área; ``l``/``a`` a largura e a
    altura. ``preenchimento`` controla como o clipe ocupa a área: ``cover``
    (aumenta e recorta o centro — sem barras) ou ``contain`` (reduz até caber e
    completa com barras pretas).

    O enquadramento do título: ``titulo_y`` é o centro vertical da faixa (fração
    da altura), ``titulo_largura`` a largura máxima do texto (fração da largura,
    usada pelo ajuste automático) e ``titulo_fonte`` o tamanho fixo em px
    (``0`` = automático: encolhe até caber na faixa).
    """

    x: float = 0.11
    y: float = 0.25
    l: float = 0.78
    a: float = 0.56
    preenchimento: str = "cover"
    titulo_y: float = 0.18
    titulo_largura: float = 0.72
    titulo_fonte: int = 0

    # -- fração -> pixels ------------------------------------------------
    def px_x(self) -> int:
        return round(self.x * LARGURA)

    def px_y(self) -> int:
        return round(self.y * ALTURA)

    def px_l(self) -> int:
        return _par(round(self.l * LARGURA))

    def px_a(self) -> int:
        return _par(round(self.a * ALTURA))

    def px_titulo_y(self) -> int:
        return round(self.titulo_y * ALTURA)

    def px_titulo_largura(self) -> int:
        return round(self.titulo_largura * LARGURA)

    # -- validação -------------------------------------------------------
    def normalizar(self) -> "Layout":
        """Ajusta os valores para dentro do quadro (clamp; sem exceções)."""
        self.x = min(max(float(self.x), 0.0), 0.98)
        self.y = min(max(float(self.y), 0.0), 0.98)
        self.l = min(max(float(self.l), 0.02), 1.0 - self.x)
        self.a = min(max(float(self.a), 0.02), 1.0 - self.y)
        if self.preenchimento not in ("cover", "contain"):
            self.preenchimento = "cover"
        self.titulo_y = min(max(float(self.titulo_y), 0.02), 0.98)
        self.titulo_largura = min(max(float(self.titulo_largura), 0.1), 1.0)
        self.titulo_fonte = int(min(max(int(self.titulo_fonte), 0), 400))
        return self

    # -- (de)serialização ------------------------------------------------
    def para_dict(self) -> dict[str, Any]:
        return {
            "moldura": {"x": self.x, "y": self.y, "l": self.l, "a": self.a},
            "preenchimento": self.preenchimento,
            "titulo": {
                "y": self.titulo_y,
                "largura": self.titulo_largura,
                "fonte": self.titulo_fonte,
            },
        }

    @classmethod
    def de_dict(cls, dados: dict[str, Any] | None) -> "Layout":
        dados = dados or {}
        titulo = dados.get("titulo") or {}
        bruto = {
            **(dados.get("moldura") or {}),
            "preenchimento": dados.get("preenchimento"),
            "titulo_y": titulo.get("y"),
            "titulo_largura": titulo.get("largura"),
            "titulo_fonte": titulo.get("fonte"),
        }
        validos = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in bruto.items() if k in validos and v is not None}
        return cls(**kwargs).normalizar()


def carregar_layout(caminho: Path | None = None) -> Layout:
    """Lê ``data/layout.json``; arquivo ausente/inválido vira o padrão."""
    caminho = Path(caminho or CAMINHO_LAYOUT)
    if not caminho.exists():
        return Layout()
    try:
        return Layout.de_dict(json.loads(caminho.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, TypeError, ValueError):
        return Layout()


def salvar_layout(layout: Layout, caminho: Path | None = None) -> Path:
    from .store import gravar_json_atomico

    caminho = Path(caminho or CAMINHO_LAYOUT)
    gravar_json_atomico(caminho, layout.normalizar().para_dict())
    return caminho
