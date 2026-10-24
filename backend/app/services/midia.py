"""Utilitários de mídia (ffmpeg) compartilhados por assembler, kit e editor.

Só depende do binário ``ffmpeg`` (o ``imageio-ffmpeg`` não traz ``ffprobe``),
então duração/áudio são lidos do log do ``ffmpeg -i``.
"""

from __future__ import annotations

import re
import subprocess
from io import BytesIO
from pathlib import Path

from PIL import Image

from .downloader import resolver_ffmpeg


class MidiaError(RuntimeError):
    """Falha ao inspecionar/extrair mídia com o ffmpeg."""


def _ffmpeg() -> str:
    exe = resolver_ffmpeg()
    if exe is None:
        raise MidiaError("ffmpeg não encontrado (instale no PATH ou 'imageio-ffmpeg')")
    return exe


def _info(caminho: Path, ffmpeg: str | None = None) -> str:
    proc = subprocess.run(
        [ffmpeg or _ffmpeg(), "-hide_banner", "-i", str(caminho)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.stderr or ""


def duracao(caminho: Path, ffmpeg: str | None = None) -> float:
    """Duração em segundos (0.0 se não der para ler)."""
    try:
        achado = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", _info(caminho, ffmpeg))
    except Exception:  # noqa: BLE001 — sem duração, o chamador decide o fallback
        return 0.0
    if achado is None:
        return 0.0
    horas, minutos, segundos = achado.groups()
    return int(horas) * 3600 + int(minutos) * 60 + float(segundos)


def tem_audio(caminho: Path, ffmpeg: str | None = None) -> bool:
    """True se o arquivo tem trilha de áudio."""
    try:
        return "Audio:" in _info(caminho, ffmpeg)
    except Exception:  # noqa: BLE001 — sem log não dá pra afirmar: trata como "sem áudio"
        return False


def quadro(caminho: Path, segundo: float) -> Image.Image:
    """Extrai um quadro do vídeo no instante ``segundo`` como imagem RGB."""
    proc = subprocess.run(
        [
            _ffmpeg(), "-v", "error", "-ss", f"{max(segundo, 0):.3f}", "-i", str(caminho),
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-",
        ],
        capture_output=True,
    )
    if proc.returncode != 0 or not proc.stdout:
        raise MidiaError(f"não consegui extrair quadro de {caminho.name}")
    return Image.open(BytesIO(proc.stdout)).convert("RGB")
