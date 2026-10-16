"""Preview do editor: composição rápida em PIL e frame exato via ffmpeg.

O preview PIL se atualiza a cada ajuste (instantâneo); o "frame exato" usa o
mesmo filter-graph do ``assembler`` para conferir o resultado real (fonte,
contorno, recorte) antes de gerar o vídeo.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from PIL import Image, ImageOps

from .. import titulo
from ..config import MOLDURA_PATH, TMP_DIR
from ..layout import ALTURA, LARGURA, Layout
from ..services.assembler import FPS, _escalar
from ..services.downloader import resolver_ffmpeg

FRAME_DIR = TMP_DIR / "editor"


def _carregar_moldura() -> Image.Image | None:
    if not MOLDURA_PATH.exists():
        return None
    return Image.open(MOLDURA_PATH).convert("RGBA")


def extrair_frame(clip: Path | None, tempo: float = 1.0) -> Image.Image | None:
    """Um quadro do clipe para o preview (cacheado em ``tmp/editor/``)."""
    if not clip or not Path(clip).exists():
        return None
    ffmpeg = resolver_ffmpeg()
    if ffmpeg is None:
        return None
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    destino = FRAME_DIR / f"{Path(clip).stem}_{tempo:g}.png"
    if not destino.exists():
        cmd = [ffmpeg, "-y", "-ss", str(tempo), "-i", str(clip), "-frames:v", "1", str(destino)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not destino.exists():
            return None
    try:
        return Image.open(destino).convert("RGB")
    except OSError:
        return None


def compor_preview(
    layout: Layout,
    texto: str,
    conteudo: Image.Image | None,
    escala: float = 1 / 3,
    moldura: Image.Image | None = None,
) -> Image.Image:
    """Compõe moldura + clipe + título em PIL, com a mesma geometria do ffmpeg.

    ``escala`` 1/3 produz 360x640; o título vem do mesmo renderizador do vídeo
    final (``app.titulo``), então o preview bate com o arquivo gerado.
    """
    largura, altura = round(LARGURA * escala), round(ALTURA * escala)
    quadro = Image.new("RGBA", (largura, altura), (0, 0, 0, 255))

    base = moldura if moldura is not None else _carregar_moldura()
    if base is not None:
        quadro.alpha_composite(base.resize((largura, altura), Image.LANCZOS))

    x, y = round(layout.x * largura), round(layout.y * altura)
    l, a = round(layout.l * largura), round(layout.a * altura)
    if conteudo is not None and l > 0 and a > 0:
        miolo = conteudo.convert("RGB")
        if layout.preenchimento == "contain":
            miolo.thumbnail((l, a), Image.LANCZOS)
            caixa = Image.new("RGBA", (l, a), (0, 0, 0, 255))
            caixa.paste(miolo, ((l - miolo.width) // 2, (a - miolo.height) // 2))
        else:
            caixa = ImageOps.fit(miolo, (l, a), method=Image.LANCZOS).convert("RGBA")
        quadro.alpha_composite(caixa, (x, y))

    if texto:
        camada = titulo.imagem(texto, layout).resize((largura, altura), Image.LANCZOS)
        quadro.alpha_composite(camada)

    return quadro.convert("RGB")


def renderizar_frame_exato(
    clip: Path,
    layout: Layout,
    texto: str,
    tempo: float = 1.0,
) -> Path | None:
    """Renderiza um quadro 1080x1920 com o ffmpeg real (idêntico ao vídeo final)."""
    ffmpeg = resolver_ffmpeg()
    if ffmpeg is None or not clip or not Path(clip).exists() or not MOLDURA_PATH.exists():
        return None

    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    caminho_titulo = titulo.caminho_png(texto, layout) if texto else None
    chave = hashlib.md5(
        f"{clip}|{texto}|{layout.para_dict()}|{caminho_titulo}".encode()
    ).hexdigest()[:10]
    destino = FRAME_DIR / f"exato_{chave}.png"
    if destino.exists():
        return destino

    filtros = [
        f"[1:v]scale={LARGURA}:{ALTURA}:flags=lanczos,setsar=1,format=yuv420p,"
        f"loop=loop=-1:size=1:start=0,fps={FPS}[base]",
        _escalar(0, "vm", layout.px_l(), layout.px_a(), layout.preenchimento),
        f"[base][vm]overlay={layout.px_x()}:{layout.px_y()}:shortest=1[v0]",
    ]

    cmd = [ffmpeg, "-y", "-ss", str(tempo), "-i", str(clip), "-i", str(MOLDURA_PATH)]
    if caminho_titulo is not None:
        cmd += ["-i", str(caminho_titulo)]
        filtros.append("[2:v]format=rgba[tit]")
        filtros.append("[v0][tit]overlay=0:0:eof_action=repeat[v]")
    else:
        filtros.append("[v0]null[v]")

    cmd += ["-filter_complex", ";".join(filtros), "-map", "[v]", "-frames:v", "1", str(destino)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not destino.exists():
        return None
    return destino
