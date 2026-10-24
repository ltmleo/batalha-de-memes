"""Pacote de publicação: legenda, manifest e cópia dos arquivos da rodada.

A publicação ainda é **assistida** (upload manual no TikTok/Reels/Shorts): o
pipeline deixa tudo pronto em ``media/publicar/torneio_T_rodada_R/`` — vídeo,
capa e legenda por confronto + ``manifest.json`` — e depois
``app.cli publicar`` grava o link e abre o prazo de votação.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..config import PUBLICAR_DIR, REPO_DIR
from ..store import Estado, agora, gravar_json_atomico
from .kit import confronto_do_match

SITE_URL = "https://ltmleo.github.io/batalha-de-memes/"
HASHTAGS = ["#batalhadememes", "#memes", "#memesbr", "#humor", "#fyp"]

LEGENDA = """{rodada}{jogo}: {nome_a} 🅰️ vs 🅱️ {nome_b}

Quem vence? Comenta A ou B! 👇
Um voto por pessoa, vale até {prazo}.

Chaveamento completo: {site}

{hashtags}"""


def _tag(nome: str) -> str:
    from .vote_parser import normalizar

    return "#" + "".join(p for p in normalizar(nome).split() if p.isalnum())


def legenda(estado: Estado, match: dict[str, Any], horas_votacao: int = 48) -> str:
    conf = confronto_do_match(estado, match)
    prazo = match.get("deadline")
    if prazo:
        quando = datetime.fromisoformat(prazo.replace("Z", "+00:00"))
    else:
        quando = datetime.now(timezone.utc) + timedelta(hours=horas_votacao)
    tags = HASHTAGS + [_tag(conf.nome_a), _tag(conf.nome_b)]
    return LEGENDA.format(
        rodada=conf.rodada.capitalize(),
        jogo=f" ({conf.jogo})" if conf.jogo else "",
        nome_a=conf.nome_a,
        nome_b=conf.nome_b,
        prazo=quando.astimezone().strftime("%d/%m às %Hh"),
        site=f"{SITE_URL}match/{match['id']}/",
        hashtags=" ".join(dict.fromkeys(tags)),
    )


def absoluto(caminho: str | None) -> Path | None:
    """Caminho gravado no estado (relativo ao repo ou absoluto) -> Path."""
    if not caminho:
        return None
    p = Path(caminho)
    return p if p.is_absolute() else REPO_DIR / p


def empacotar(estado: Estado, matches: list[dict[str, Any]], torneio_id: int,
              rodada: int) -> Path:
    """Copia vídeo/capa/legenda de cada confronto pronto e grava o manifest."""
    pasta = PUBLICAR_DIR / f"torneio_{torneio_id}_rodada_{rodada}"
    pasta.mkdir(parents=True, exist_ok=True)
    itens = []
    for match in matches:
        video = absoluto(match.get("video_path"))
        if video is None or not video.exists():
            continue
        base = f"match_{match['id']}"
        shutil.copyfile(video, pasta / f"{base}.mp4")
        capa = absoluto(match.get("capa_path"))
        if capa is not None and capa.exists():
            shutil.copyfile(capa, pasta / f"{base}_capa.png")
        texto = legenda(estado, match)
        (pasta / f"{base}_legenda.txt").write_text(texto + "\n", encoding="utf-8")
        conf = confronto_do_match(estado, match)
        itens.append({
            "match_id": match["id"],
            "titulo": f"{conf.nome_a} vs {conf.nome_b}",
            "video": f"{base}.mp4",
            "capa": f"{base}_capa.png" if capa is not None and capa.exists() else None,
            "legenda": texto,
            "duracao": match.get("duracao"),
            "publicar_cmd": f"python -m app.cli publicar --match {match['id']} --tiktok URL",
        })
    gravar_json_atomico(pasta / "manifest.json", {
        "torneio_id": torneio_id, "rodada": rodada, "gerado_em": agora(), "itens": itens,
    })
    return pasta
