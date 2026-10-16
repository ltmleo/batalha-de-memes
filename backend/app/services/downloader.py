from __future__ import annotations

import hashlib
import logging
import os
import shutil
import subprocess
from pathlib import Path

from typing import Any, Callable

from ..config import CLIPS_DIR, MEDIA_DIR, RAW_DIR

logger = logging.getLogger("batalha.downloader")

FORMATO = "bv*[height<=1080]+ba/b[height<=1080]/b"

# Callback de progresso: recebe a fração concluída (0.0 a 1.0) de um download.
Progresso = Callable[[float], None]


class DownloadError(RuntimeError):
    """Erro ao baixar/recortar/normalizar um trecho."""


def _reportar(progresso: Progresso | None, fracao: float) -> None:
    """Chama o callback de progresso sem deixar uma falha dele quebrar o download."""
    if progresso is None:
        return
    try:
        progresso(max(0.0, min(1.0, fracao)))
    except Exception:  # noqa: BLE001 — a UI nunca deve derrubar o download
        logger.debug("callback de progresso falhou", exc_info=True)


def _assinatura(meme: dict[str, Any]) -> str:
    """Assinatura do trecho: muda quando link/inicio/fim mudam (invalida o cache)."""
    bruto = "|".join(str(meme.get(k)) for k in ("youtube_url", "inicio", "fim"))
    return hashlib.sha1(bruto.encode("utf-8")).hexdigest()


def _arquivo_assinatura(pasta: Path, meme_id: Any) -> Path:
    return pasta / f"meme_{meme_id}.assinatura"


def _assinatura_salva(pasta: Path, meme_id: Any) -> str | None:
    arq = _arquivo_assinatura(pasta, meme_id)
    if not arq.exists():
        return None
    try:
        return arq.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _guardar_assinatura(pasta: Path, meme_id: Any, assinatura: str) -> None:
    try:
        _arquivo_assinatura(pasta, meme_id).write_text(assinatura, encoding="utf-8")
    except OSError:
        logger.debug("não consegui gravar a assinatura do meme %s", meme_id, exc_info=True)



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


def baixar_trecho(
    meme: dict[str, Any],
    forcar: bool = False,
    dir_saida: Path | None = None,
    progresso: Progresso | None = None,
) -> Path:
    """Baixa apenas o trecho [inicio, fim] (em segundos) e remuxa para mp4.

    ``progresso`` (opcional) recebe a fração baixada (0.0 a 1.0) para a barra da
    interface.
    """
    meme_id = meme["id"]
    pasta = dir_saida or RAW_DIR
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"meme_{meme_id}.mp4"
    assinatura = _assinatura(meme)
    if destino.exists() and not forcar:
        salva = _assinatura_salva(pasta, meme_id)
        if salva is None:
            # cache anterior à assinatura: adota como válido (não rebaixa sem motivo)
            _guardar_assinatura(pasta, meme_id, assinatura)
            salva = assinatura
        if salva == assinatura:
            logger.info("cache hit: %s", destino.name)
            _reportar(progresso, 1.0)
            return destino
        logger.info("trecho mudou (link/inicio/fim): rebaixando %s", destino.name)

    if not meme.get("youtube_url"):
        raise DownloadError(f"meme {meme_id} sem youtube_url")

    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover
        raise DownloadError("yt-dlp não instalado (pip install yt-dlp)") from exc

    if resolver_ffmpeg() is None:
        raise DownloadError("ffmpeg não encontrado (instale no PATH ou 'imageio-ffmpeg')")

    _garantir_ffmpeg_no_path()

    inicio = float(meme.get("inicio") or 0)
    fim = float(meme.get("fim") or 0)
    if fim <= inicio:
        raise DownloadError(f"trecho inválido: {_hhmmss(inicio)}-{_hhmmss(fim)}")

    def _ranges(_info: dict, _ydl: object) -> list[dict[str, float]]:
        return [{"start_time": inicio, "end_time": fim}]

    def _progresso_ytdlp(d: dict[str, Any]) -> None:
        status = d.get("status")
        if status == "finished":
            _reportar(progresso, 1.0)
        elif status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            baixado = d.get("downloaded_bytes") or 0
            if total:
                _reportar(progresso, baixado / total)
            elif d.get("fragment_index") and d.get("fragment_count"):
                _reportar(progresso, d["fragment_index"] / d["fragment_count"])

    opts = {
        "format": FORMATO,
        "outtmpl": str(pasta / f"meme_{meme_id}.%(ext)s"),
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
        "progress_hooks": [_progresso_ytdlp],
    }

    logger.info("baixando meme %s [%s-%s]", meme_id, _hhmmss(inicio), _hhmmss(fim))
    _reportar(progresso, 0.0)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([meme["youtube_url"]])
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(f"falha ao baixar meme {meme_id}: {exc}") from exc

    if not destino.exists():
        raise DownloadError(f"yt-dlp não produziu {destino}")
    logger.info("baixado: %s", destino.name)
    _guardar_assinatura(pasta, meme_id, assinatura)
    _reportar(progresso, 1.0)
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
    progresso: Progresso | None = None,
) -> Path:
    """Normaliza para 1080x1920 (9:16) preenchendo todo o quadro.

    Usa escala com ``force_original_aspect_ratio=increase`` seguida de recorte
    central: o vídeo ocupa a área inteira, mesmo que corte as bordas — sem
    fundo desfocado nem barras (letterbox). ``flags=lanczos`` mantém a nitidez
    para evitar o aspecto "borrado" do reescalonamento.
    """
    destino = destino or ((dir_saida or CLIPS_DIR) / f"clip_{origem.stem}.mp4")
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and not forcar:
        # clipe mais novo que o bruto => cache válido; se o bruto foi rebaixado
        # (trecho mudou), ele fica mais novo e a normalização roda de novo.
        if not origem.exists() or destino.stat().st_mtime >= origem.stat().st_mtime:
            _reportar(progresso, 1.0)
            return destino

    ffmpeg = resolver_ffmpeg()
    if ffmpeg is None:
        raise DownloadError("ffmpeg não encontrado (instale no PATH ou 'imageio-ffmpeg')")

    filtro = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
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
    _reportar(progresso, 0.0)
    _executar(cmd)
    _reportar(progresso, 1.0)
    return destino


def preparar_clip(
    meme: dict[str, Any],
    forcar: bool = False,
    dir_saida: Path | None = None,
    progresso: Progresso | None = None,
) -> Path:
    """Baixa o trecho e devolve o clipe já normalizado em 9:16.

    O progresso reportado (0.0 a 1.0) reserva ~85% para o download e ~15% para
    a normalização.
    """

    def _download(fracao: float) -> None:
        _reportar(progresso, fracao * 0.85)

    def _normalizar(fracao: float) -> None:
        _reportar(progresso, 0.85 + fracao * 0.15)

    bruto = baixar_trecho(meme, forcar=forcar, dir_saida=dir_saida, progresso=_download)
    return normalizar_vertical(bruto, forcar=forcar, dir_saida=dir_saida, progresso=_normalizar)


def _cli() -> None:
    import argparse

    from ..store import Estado

    parser = argparse.ArgumentParser(description="Baixa e normaliza o trecho de um meme")
    parser.add_argument("--id", type=int, required=True, help="id do meme no estado")
    parser.add_argument("--forcar", action="store_true", help="ignora cache")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    deps = verificar_dependencias()
    if deps["yt_dlp"] is None:
        raise SystemExit("yt-dlp não instalado (pip install yt-dlp)")
    if deps["ffmpeg"] is None:
        raise SystemExit("ffmpeg não encontrado")

    estado = Estado.carregar()
    meme = estado.buscar_meme(args.id)
    if meme is None:
        raise SystemExit(f"meme {args.id} não encontrado")
    print(preparar_clip(meme, forcar=args.forcar))


if __name__ == "__main__":
    _cli()
