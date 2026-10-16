from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..config import (
    ABERTURA_PATH,
    CLIPS_DIR,
    ENCERRAMENTO_PATH,
    MOLDURA_PATH,
)
from ..layout import Layout, carregar_layout
from .. import titulo
from .downloader import preparar_clip, resolver_ffmpeg

if TYPE_CHECKING:  # só para tips; evita import cíclico
    from ..store import Estado

LARGURA = 1080
ALTURA = 1920
FPS = 30

# Área da moldura e preenchimento vêm de data/layout.json (editável no editor);
# os valores abaixo são o padrão histórico, mantidos por referência/compatibilidade.
_LAYOUT_PADRAO = Layout()
MEME_X = _LAYOUT_PADRAO.px_x()
MEME_Y = _LAYOUT_PADRAO.px_y()
MEME_L = _LAYOUT_PADRAO.px_l()
MEME_A = _LAYOUT_PADRAO.px_a()


class AssembleError(RuntimeError):
    """Erro ao montar o vídeo do confronto."""


def _escalar(indice: int, label: str, largura: int, altura: int, modo: str = "cover") -> str:
    """Preenche o quadro reservado pelo clipe, conforme o modo.

    ``cover``: ``force_original_aspect_ratio=increase`` aumenta o vídeo até
    cobrir toda a área e ``crop`` remove o excesso no centro — ocupa 100% do
    espaço, mesmo cortando as bordas, sem fundo desfocado nem barras.
    ``contain``: ``decrease`` reduz até caber e ``pad`` completa com barras
    pretas centralizadas (nenhuma parte do vídeo é cortada).
    ``flags=lanczos`` evita o aspecto desfocado/borrado do reescalão.
    """
    if modo == "contain":
        preenchimento = (
            f"scale={largura}:{altura}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={largura}:{altura}:(ow-iw)/2:(oh-ih)/2:color=black"
        )
    else:
        preenchimento = (
            f"scale={largura}:{altura}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={largura}:{altura}"
        )
    return (
        f"[{indice}:v]{preenchimento},fps={FPS},format=yuv420p,setsar=1[{label}]"
    )


def _escalar_meme(indice: int, label: str, layout: Layout) -> str:
    return _escalar(indice, label, layout.px_l(), layout.px_a(), layout.preenchimento)


def _audio(indice: int, label: str) -> str:
    return (
        f"[{indice}:a]aformat=sample_fmts=fltp:sample_rates=48000:"
        f"channel_layouts=stereo[{label}]"
    )


def montar_video(
    clip_a: Path,
    clip_b: Path,
    texto_a: str = "A",
    texto_b: str = "B",
    abertura: Path | None = None,
    encerramento: Path | None = None,
    moldura: Path | None = None,
    destino: Path | None = None,
    layout: Layout | None = None,
) -> Path:
    """Mostra o clipe A e depois o clipe B dentro da moldura, com o título no topo.

    ``layout`` (padrão: ``data/layout.json``) define a área do clipe na moldura
    e o preenchimento (``cover``/``contain``).
    """
    ffmpeg = resolver_ffmpeg()
    if ffmpeg is None:
        raise AssembleError("ffmpeg não encontrado")

    layout = (layout or carregar_layout()).normalizar()
    destino = destino or (CLIPS_DIR / "batalha.mp4")
    destino.parent.mkdir(parents=True, exist_ok=True)

    moldura = MOLDURA_PATH if moldura is None else moldura
    usar_moldura = moldura is not None and Path(moldura).exists()
    usar_abertura = abertura is not None and Path(abertura).exists()
    usar_encerramento = encerramento is not None and Path(encerramento).exists()

    entradas: list[Path] = []
    idx_frame = idx_abertura = None
    if usar_moldura:
        idx_frame = len(entradas)
        entradas.append(moldura)
    if usar_abertura:
        idx_abertura = len(entradas)
        entradas.append(abertura)
    idx_a = len(entradas)
    entradas.append(clip_a)
    idx_b = len(entradas)
    entradas.append(clip_b)
    idx_enc = None
    if usar_encerramento:
        idx_enc = len(entradas)
        entradas.append(encerramento)

    filtros: list[str] = []
    segmentos: list[tuple[str, str]] = []

    base_moldura = {"va": "fr_a", "vb": "fr_b"}
    if usar_moldura:
        filtros.append(
            f"[{idx_frame}:v]scale={LARGURA}:{ALTURA}:flags=lanczos,setsar=1,"
            f"format=yuv420p,loop=loop=-1:size=1:start=0,fps={FPS}[framebase]"
        )
        filtros.append("[framebase]split=2[fr_a][fr_b]")

    if usar_abertura:
        filtros.append(_escalar(idx_abertura, "iv", LARGURA, ALTURA))
        filtros.append(_audio(idx_abertura, "ia"))
        segmentos.append(("iv", "ia"))

    trechos = ((idx_a, "va", "aa", texto_a), (idx_b, "vb", "ab", texto_b))
    for indice, vtag, atag, texto in trechos:
        if usar_moldura:
            filtros.append(_escalar_meme(indice, f"{vtag}m", layout))
            filtros.append(
                f"[{base_moldura[vtag]}][{vtag}m]overlay={layout.px_x()}:{layout.px_y()}:"
                f"shortest=1[{vtag}b]"
            )
        else:
            filtros.append(_escalar(indice, f"{vtag}b", LARGURA, ALTURA))
        vbase = f"{vtag}b"

        if texto:
            caminho_titulo = titulo.caminho_png(texto, layout)
            idx_titulo = len(entradas)
            entradas.append(caminho_titulo)
            filtros.append(f"[{idx_titulo}:v]format=rgba[tit_{vtag}]")
            filtros.append(f"[{vbase}][tit_{vtag}]overlay=0:0:eof_action=repeat[{vtag}]")
            vbase = vtag

        filtros.append(_audio(indice, atag))
        segmentos.append((vbase, atag))

    if usar_encerramento:
        filtros.append(_escalar(idx_enc, "ev", LARGURA, ALTURA))
        filtros.append(_audio(idx_enc, "ea"))
        segmentos.append(("ev", "ea"))

    entrada_concat = "".join(f"[{v}][{a}]" for v, a in segmentos)
    filtros.append(f"{entrada_concat}concat=n={len(segmentos)}:v=1:a=1[outv][outa]")

    cmd = [ffmpeg, "-y"]
    for entrada in entradas:
        cmd += ["-i", str(entrada)]
    cmd += ["-filter_complex", ";".join(filtros), "-map", "[outv]", "-map", "[outa]"]
    cmd += [
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        str(destino),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssembleError(f"ffmpeg falhou ({proc.returncode}): {proc.stderr[-800:]}")
    return destino


def montar_match(
    estado: "Estado",
    match: dict[str, Any],
    layout: Layout | None = None,
    forcar: bool = False,
    destino: Path | None = None,
) -> Path:
    """Baixa os clipes do confronto e monta o vídeo com o layout atual.

    O título de cada lado é ``titulo_a``/``titulo_b`` do confronto (override
    feito no editor) ou, na ausência, o nome do meme. Grava ``video_path`` e
    marca o confronto como ``pronto`` (persistir o estado é com o chamador).
    """
    meme_a = estado.buscar_meme(match["meme_a_id"])
    meme_b = estado.buscar_meme(match["meme_b_id"])
    if meme_a is None or meme_b is None:
        raise AssembleError(f"confronto {match.get('id')}: meme A ou B não encontrado")

    clip_a = preparar_clip(meme_a, forcar=forcar)
    clip_b = preparar_clip(meme_b, forcar=forcar)

    destino = destino or CLIPS_DIR / f"match_{match['id']}.mp4"
    saida = montar_video(
        clip_a,
        clip_b,
        texto_a=match.get("titulo_a") or meme_a["nome"],
        texto_b=match.get("titulo_b") or meme_b["nome"],
        abertura=ABERTURA_PATH,
        encerramento=ENCERRAMENTO_PATH,
        layout=layout,
        destino=destino,
    )
    match["video_path"] = str(saida)
    match["status"] = "pronto"
    return saida


def _cli() -> None:
    import argparse
    import logging

    from ..config import TMP_DIR
    from ..store import Estado

    parser = argparse.ArgumentParser(description="Monta a batalha de dois memes com abertura")
    parser.add_argument("--a", type=int, required=True, help="id do meme A")
    parser.add_argument("--b", type=int, required=True, help="id do meme B")
    parser.add_argument("--sem-abertura", action="store_true")
    parser.add_argument("--sem-moldura", action="store_true")
    parser.add_argument("--sem-encerramento", action="store_true")
    parser.add_argument("--forcar", action="store_true", help="ignora o cache de download")
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    estado = Estado.carregar()
    meme_a = estado.buscar_meme(args.a)
    meme_b = estado.buscar_meme(args.b)
    if meme_a is None or meme_b is None:
        raise SystemExit("meme A ou B não encontrado")

    clip_a = preparar_clip(meme_a, forcar=args.forcar, dir_saida=TMP_DIR)
    clip_b = preparar_clip(meme_b, forcar=args.forcar, dir_saida=TMP_DIR)

    abertura = None if args.sem_abertura else ABERTURA_PATH
    encerramento = None if args.sem_encerramento else ENCERRAMENTO_PATH
    moldura = None if args.sem_moldura else MOLDURA_PATH
    destino = Path(args.saida) if args.saida else TMP_DIR / f"batalha_{meme_a['id']}_{meme_b['id']}.mp4"
    saida = montar_video(
        clip_a,
        clip_b,
        texto_a=meme_a["nome"],
        texto_b=meme_b["nome"],
        abertura=abertura,
        encerramento=encerramento,
        moldura=moldura,
        destino=destino,
    )
    print(saida)


if __name__ == "__main__":
    _cli()
