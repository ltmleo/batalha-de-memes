"""Estado da aplicação persistido em JSON.

``data/estado.json`` é a **fonte única da verdade**: guarda memes, temporadas,
confrontos e votos. Não há banco de dados nem API — o pipeline lê e grava este
arquivo, e o site estático consome o mesmo JSON em tempo de build.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import CAMINHO_ESTADO

Colecao = list[dict[str, Any]]


class Estado:
    """Coleções de memes, temporadas, confrontos e votos."""

    def __init__(self, dados: dict[str, Any] | None = None) -> None:
        dados = dados or {}
        self.memes: Colecao = list(dados.get("memes", []))
        self.tournaments: Colecao = list(dados.get("tournaments", []))
        self.matches: Colecao = list(dados.get("matches", []))
        self.votes: Colecao = list(dados.get("votes", []))

    # -- persistência ---------------------------------------------------
    @classmethod
    def carregar(cls, caminho: Path | None = None) -> "Estado":
        caminho = Path(caminho or CAMINHO_ESTADO)
        if not caminho.exists():
            return cls()
        return cls(json.loads(caminho.read_text(encoding="utf-8")))

    def para_dict(self) -> dict[str, Any]:
        return {
            "memes": self.memes,
            "tournaments": self.tournaments,
            "matches": self.matches,
            "votes": self.votes,
        }

    def salvar(self, caminho: Path | None = None) -> Path:
        caminho = Path(caminho or CAMINHO_ESTADO)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(self.para_dict(), ensure_ascii=False, indent=2)
        caminho.write_text(texto + "\n", encoding="utf-8")
        return caminho

    # -- utilidades -----------------------------------------------------
    @staticmethod
    def proximo_id(colecao: Colecao) -> int:
        return max((item["id"] for item in colecao), default=0) + 1

    def adicionar(self, colecao: Colecao, registro: dict[str, Any]) -> dict[str, Any]:
        registro.setdefault("id", self.proximo_id(colecao))
        colecao.append(registro)
        return registro

    def buscar_meme(self, meme_id: int) -> dict[str, Any] | None:
        return next((m for m in self.memes if m["id"] == meme_id), None)

    def buscar_torneio(self, torneio_id: int) -> dict[str, Any] | None:
        return next((t for t in self.tournaments if t["id"] == torneio_id), None)

    def buscar_match(self, match_id: int) -> dict[str, Any] | None:
        return next((m for m in self.matches if m["id"] == match_id), None)

    def matches_do_torneio(self, torneio_id: int) -> list[dict[str, Any]]:
        return sorted(
            (m for m in self.matches if m["tournament_id"] == torneio_id),
            key=lambda m: (m["round"], m["posicao"]),
        )


def agora() -> str:
    """Timestamp ISO-8601 em UTC (ex.: ``2026-10-11T14:00:00Z``)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
