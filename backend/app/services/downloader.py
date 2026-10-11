from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from .. import models
from ..config import CLIPS_DIR, MEDIA_DIR, RAW_DIR

logger = logging.getLogger("batalha.downloader")

FORMATO = "bv*[height<=1080]+ba/b[height<=1080]/b"


class DownloadError(RuntimeError):
    """Erro ao baixar/recortar/normalizar um trecho."""


def resolver_ffmpeg() -> str | None:
    """Retorna o caminho do ffmpeg: PATH ou binário embutido do imageio-ffmpeg."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def verificar_dependencias() -> dict[str, str | None]:
    """Diagnóstico rápido do ambiente de download."""
    try:
        import yt_dlp  # noqa: F401

        yt_dlp_versao: str | None = __import__("yt_dlp.version", fromlist=["__version__"]).__version__
    except Exception:
        yt_dlp_versao = None
    return {"ffmpeg": resolver_ffmpeg(), "yt_dlp": yt_dlp_versao}


def _hhmmss(segundos: float) -> str:
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _ffmpeg_location() -> str | None:
    return resolver_ffmpeg()


def _garantir_ffmpeg_no_path() -> None:
    """O yt-dlp só detecta ffmpeg no PATH; expõe o binário do imageio-ffmpeg."""
    if shutil.which("ffmpeg"):
        return
    exe = resolver_ffmpeg()
    if exe is None:
        return

    tools = MEDIA_DIR / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    alvo = tools / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if not alvo.exists():
        try:
            os.link(exe, alvo)
        except OSError:
            shutil.copy2(exe, alvo)
    os.environ["PATH"] = str(tools) + os.pathsep + os.environ.get("PATH", "")


def baixar_trecho(meme: models.Meme, forcar: bool = False, dir_saida: Path | None = None) -> Path:
    """Baixa apenas o trecho [inicio, fim] (em segundos) e remuxa para mp4."""
    pasta = dir_saida or RAW_DIR
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"meme_{meme.id}.mp4"
    if destino.exists() and not forcar:
        logger.info("cache hit: %s", destino.name)
        return destino

    if not meme.youtube_url:
        raise DownloadError(f"meme {meme.id} sem youtube_url")

    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover
        raise DownloadError("yt-dlp não instalado (pip install yt-dlp)") from exc

    if resolver_ffmpeg() is None:
        raise DownloadError("ffmpeg não encontrado (instale no PATH ou 'imageio-ffmpeg')")

    _garantir_ffmpeg_no_path()

    inicio = float(meme.inicio or 0)
    fim = float(meme.fim or 0)
    if fim <= inicio:
        raise DownloadError(f"trecho inválido: {_hhmmss(inicio)}-{_hhmmss(fim)}")

    def _ranges(_info: dict, _ydl: object) -> list[dict[str, float]]:
        return [{"start_time": inicio, "end_time": fim}]

    opts = {
        "format": FORMATO,
        "outtmpl": str(pasta / f"meme_{meme.id}.%(ext)s"),
        "merge_output_format": "mp4",
        "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}],
        "download_ranges": _ranges,
        "force_keyframes_at_cuts": True,
        "ffmpeg_location": _ffmpeg_location(),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "overwrites": True,
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 30,
        "noplaylist": True,
    }

    logger.info("baixando meme %s [%s-%s]", meme.id, _hhmmss(inicio), _hhmmss(fim))
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([meme.youtube_url])
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(f"falha ao baixar meme {meme.id}: {exc}") from exc

    if not destino.exists():
        raise DownloadError(f"yt-dlp não produziu {destino}")
    logger.info("baixado: %s", destino.name)
    return destino


def _executar(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise DownloadError(f"ffmpeg falhou ({proc.returncode}): {proc.stderr[-600:]}")


def normalizar_vertical(
    origem: Path,
    destino: Path | None = None,
    forcar: bool = False,
    dir_saida: Path | None = None,
) -> Path:
    """Normaliza para 1080x1920 (9:16) com fundo desfocado."""
    destino = destino or ((dir_saida or CLIPS_DIR) / f"clip_{origem.stem}.mp4")
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and not forcar:
        return destino

    ffmpeg = resolver_ffmpeg()
    if ffmpeg is None:
        raise DownloadError("ffmpeg não encontrado (instale no PATH ou 'imageio-ffmpeg')")

    filtro = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920:exact=1,setsar=1[v]"
    )
    cmd = [
        ffmpeg, "-y",
        "-i", str(origem),
        "-filter_complex", filtro,
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac",
        str(destino),
    ]
    logger.info("normalizando -> %s", destino.name)
    _executar(cmd)
    return destino


def preparar_clip(meme: models.Meme, forcar: bool = False, dir_saida: Path | None = None) -> Path:
    """Baixa o trecho e devolve o clipe já normalizado em 9:16."""
    bruto = baixar_trecho(meme, forcar=forcar, dir_saida=dir_saida)
    return normalizar_vertical(bruto, forcar=forcar, dir_saida=dir_saida)


def _cli() -> None:
    import argparse

    from ..db import SessionLocal

    parser = argparse.ArgumentParser(description="Baixa e normaliza o trecho de um meme")
    parser.add_argument("--id", type=int, required=True, help="id do meme no banco")
    parser.add_argument("--forcar", action="store_true", help="ignora cache")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    deps = verificar_dependencias()
    if deps["yt_dlp"] is None:
        raise SystemExit("yt-dlp não instalado (pip install yt-dlp)")
    if deps["ffmpeg"] is None:
        raise SystemExit("ffmpeg não encontrado")

    db = SessionLocal()
    try:
        meme = db.get(models.Meme, args.id)
        if meme is None:
            raise SystemExit(f"meme {args.id} não encontrado")
        print(preparar_clip(meme, forcar=args.forcar))
    finally:
        db.close()


if __name__ == "__main__":
    _cli()
