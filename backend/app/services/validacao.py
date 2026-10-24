"""Validação do catálogo (``data/memes/*.json``) e do estado.

Usada por ``app.cli validar`` (e no CI): erros quebram o pipeline, avisos só
informam.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import CATALOGO_DIR
from ..store import Estado

_YOUTUBE = re.compile(
    r"^https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)[\w-]{6,}"
)
DURACAO_MAX_TRECHO = 60.0


@dataclass
class Relatorio:
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.erros


def validar_meme(meme: dict[str, Any], onde: str, rel: Relatorio) -> None:
    nome = meme.get("nome")
    if not nome or not str(nome).strip():
        rel.erros.append(f"{onde}: meme sem nome")
        return
    url = str(meme.get("youtube_url") or "")
    if not url:
        rel.erros.append(f"{onde} '{nome}': sem youtube_url")
    elif "results?search_query=" in url:
        rel.avisos.append(f"{onde} '{nome}': link é uma busca, não um vídeo (não dá para baixar)")
    elif not _YOUTUBE.match(url):
        rel.avisos.append(f"{onde} '{nome}': youtube_url fora do padrão ({url})")
    try:
        inicio, fim = float(meme.get("inicio", 0)), float(meme.get("fim", 0))
    except (TypeError, ValueError):
        rel.erros.append(f"{onde} '{nome}': inicio/fim não numéricos")
        return
    if inicio < 0 or fim <= inicio:
        rel.erros.append(f"{onde} '{nome}': trecho inválido ({inicio}–{fim})")
    elif fim - inicio > DURACAO_MAX_TRECHO:
        rel.avisos.append(f"{onde} '{nome}': trecho de {fim - inicio:.0f}s (longo para o vídeo)")


def validar_catalogo(pasta: Path = CATALOGO_DIR) -> Relatorio:
    rel = Relatorio()
    nomes: dict[str, str] = {}
    trechos: dict[tuple, str] = {}
    for caminho in sorted(Path(pasta).glob("*.json")):
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            rel.erros.append(f"{caminho.name}: JSON inválido ({exc})")
            continue
        if not isinstance(dados.get("temporada"), int):
            rel.avisos.append(f"{caminho.name}: campo 'temporada' ausente ou não inteiro")
        for i, meme in enumerate(dados.get("memes", [])):
            onde = f"{caminho.name}#{i}"
            validar_meme(meme, onde, rel)
            chave = str(meme.get("nome", "")).strip().lower()
            if chave in nomes:
                rel.erros.append(f"{onde}: nome duplicado '{meme.get('nome')}' (também em {nomes[chave]})")
            nomes.setdefault(chave, onde)
            trecho = (meme.get("youtube_url"), meme.get("inicio"), meme.get("fim"))
            if trecho[0] and "results?" not in str(trecho[0]):
                if trecho in trechos:
                    rel.avisos.append(f"{onde}: mesmo vídeo/trecho de {trechos[trecho]}")
                trechos.setdefault(trecho, onde)
    return rel


def validar_estado(estado: Estado) -> Relatorio:
    rel = Relatorio()
    ids_memes = {m["id"] for m in estado.memes}
    ids_torneios = {t["id"] for t in estado.tournaments}
    for colecao, nome in ((estado.memes, "meme"), (estado.tournaments, "torneio"),
                          (estado.matches, "confronto")):
        ids = [item.get("id") for item in colecao]
        if len(ids) != len(set(ids)):
            rel.erros.append(f"ids de {nome} duplicados")
    for m in estado.matches:
        if m["tournament_id"] not in ids_torneios:
            rel.erros.append(f"confronto {m['id']}: torneio {m['tournament_id']} inexistente")
        for lado in ("meme_a_id", "meme_b_id", "winner_id"):
            if m.get(lado) is not None and m[lado] not in ids_memes:
                rel.erros.append(f"confronto {m['id']}: {lado}={m[lado]} inexistente")
        if m.get("winner_id") is not None and m["winner_id"] not in (m["meme_a_id"], m["meme_b_id"]):
            rel.erros.append(f"confronto {m['id']}: vencedor não está no confronto")
    return rel
