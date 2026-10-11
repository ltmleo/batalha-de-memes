from __future__ import annotations

import subprocess
from pathlib import Path

from ..config import (
    ABERTURA_PATH,
    CLIPS_DIR,
    ENCERRAMENTO_PATH,
    FONTE_PATH,
    FONTE_TITULO_PATH,
    MOLDURA_PATH,
)
from .downloader import resolver_ffmpeg

LARGURA = 1080
ALTURA = 1920
FPS = 30

# Áreas da moldura (assets/modulra.png), em fração de 1080x1920
MEME_X = round(0.11 * LARGURA)
MEME_Y = round(0.25 * ALTURA)
MEME_L = round(0.89 * LARGURA) - MEME_X
MEME_A = round(0.81 * ALTURA) - MEME_Y
TITULO_CENTRO_Y = round(0.18 * ALTURA)
TITULO_LARGURA = round((0.86 - 0.14) * LARGURA)
TITULO_ALTURA = round((0.23 - 0.13) * ALTURA)
TITULO_FONTE_MIN = 56
TITULO_FONTE_MAX = 150

# Avanço médio dos glifos da Arial Bold (em milésimos de em)
_AVANCO_ARIAL_BOLD = {
    **{c: 556 for c in "0123456789"},
    **dict.fromkeys("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 722),
    " ": 278, "A": 722, "B": 722, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778,
    "H": 722, "I": 278, "J": 556, "K": 722, "L": 611, "M": 833, "N": 722, "O": 778,
    "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722, "V": 667, "W": 944,
    "X": 667, "Y": 667, "Z": 611,
    "a": 556, "b": 611, "c": 556, "d": 611, "e": 556, "f": 333, "g": 611, "h": 611,
    "i": 278, "j": 278, "k": 556, "l": 278, "m": 889, "n": 611, "o": 611, "p": 611,
    "q": 611, "r": 389, "s": 556, "t": 333, "u": 611, "v": 556, "w": 778, "x": 556,
    "y": 556, "z": 500, "!": 333, "?": 611, ",": 278, ".": 278, "'": 238, "-": 333,
    ":": 333, ";": 333, "&": 722, "+": 584, "=": 584, "@": 975, "#": 556, "%": 889,
}


class AssembleError(RuntimeError):
    """Erro ao montar o vídeo do confronto."""


def _escalar(indice: int, label: str, largura: int, altura: int) -> str:
    return (
        f"[{indice}:v]scale={largura}:{altura}:force_original_aspect_ratio=increase,"
        f"crop={largura}:{altura},fps={FPS},format=yuv420p,setsar=1[{label}]"
    )


def _escalar_meme(indice: int, label: str) -> str:
    return _escalar(indice, label, MEME_L, MEME_A)


def _audio(indice: int, label: str) -> str:
    return (
        f"[{indice}:a]aformat=sample_fmts=fltp:sample_rates=48000:"
        f"channel_layouts=stereo[{label}]"
    )


def _escapar(texto: str) -> str:
    return (
        str(texto)
        .replace("\\", "\\\\")
        .replace("'", r"\'")
        .replace(":", r"\:")
        .replace("%", r"\%")
    )


def _tamanho_titulo(texto: str) -> int:
    """Maior fonte (Arial Bold) que cabe na área do título, limitada pela altura."""
    em = sum(_AVANCO_ARIAL_BOLD.get(c, 556) for c in texto) / 1000 or 1.0
    por_largura = 0.98 * TITULO_LARGURA / em
    limite = min(TITULO_FONTE_MAX, 0.95 * TITULO_ALTURA / 1.05)
    return int(max(TITULO_FONTE_MIN, min(por_largura, limite)))


def _titulo(texto: str, fonte: str) -> str:
    return (
        f"drawtext=fontfile='{fonte}':text='{_escapar(texto)}':"
        f"x=(w-text_w)/2:y={TITULO_CENTRO_Y}-text_h/2:"
        f"fontcolor=white:fontsize={_tamanho_titulo(texto)}:"
        "shadowcolor=black@0.8:shadowx=3:shadowy=3"
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
    fonte: Path | None = None,
    fonte_titulo: Path | None = None,
) -> Path:
    """Mostra o clipe A e depois o clipe B dentro da moldura, com o título no topo."""
    ffmpeg = resolver_ffmpeg()
    if ffmpeg is None:
        raise AssembleError("ffmpeg não encontrado")

    fonte_titulo = fonte_titulo or FONTE_TITULO_PATH
    if not Path(fonte_titulo).exists():
        fonte_titulo = fonte or FONTE_PATH
    fonte_titulo_ff = str(fonte_titulo).replace("\\", "/").replace(":", r"\:")
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
            filtros.append(_escalar_meme(indice, f"{vtag}m"))
            filtros.append(
                f"[{base_moldura[vtag]}][{vtag}m]overlay={MEME_X}:{MEME_Y}:shortest=1[{vtag}b]"
            )
        else:
            filtros.append(_escalar(indice, f"{vtag}b", LARGURA, ALTURA))
        vbase = f"{vtag}b"

        if texto:
            filtros.append(f"[{vbase}]{_titulo(texto, fonte_titulo_ff)}[{vtag}]")
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


def _cli() -> None:
    import argparse
    import logging

    from .. import models
    from ..config import TMP_DIR
    from ..db import SessionLocal
    from .downloader import preparar_clip

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

    db = SessionLocal()
    try:
        meme_a = db.get(models.Meme, args.a)
        meme_b = db.get(models.Meme, args.b)
        if meme_a is None or meme_b is None:
            raise SystemExit("meme A ou B não encontrado")

        clip_a = preparar_clip(meme_a, forcar=args.forcar, dir_saida=TMP_DIR)
        clip_b = preparar_clip(meme_b, forcar=args.forcar, dir_saida=TMP_DIR)

        abertura = None if args.sem_abertura else ABERTURA_PATH
        encerramento = None if args.sem_encerramento else ENCERRAMENTO_PATH
        moldura = None if args.sem_moldura else MOLDURA_PATH
        destino = Path(args.saida) if args.saida else TMP_DIR / f"batalha_{meme_a.id}_{meme_b.id}.mp4"
        saida = montar_video(
            clip_a,
            clip_b,
            texto_a=meme_a.nome,
            texto_b=meme_b.nome,
            abertura=abertura,
            encerramento=encerramento,
            moldura=moldura,
            destino=destino,
        )
        print(saida)
    finally:
        db.close()


if __name__ == "__main__":
    _cli()
