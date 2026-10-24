"""Montagem do vídeo do confronto (ffmpeg).

O vídeo é uma lista de **segmentos** (ver ``data/roteiro.json``)::

    gancho → meme A → versus → meme B → encerramento

- segmentos ``tela`` (gancho, abertura, versus, encerramento) ocupam o quadro
  inteiro;
- segmentos ``meme`` passam pela moldura (``assets/moldura2.png``), com título,
  selo A/B e a faixa "COMENTE A/B" no fim;
- cada segmento é cortado/estendido para a duração exata do arquivo, então as
  transições (``xfade``/``acrossfade``) caem no ponto certo;
- o áudio dos memes é normalizado (``loudnorm``) e uma barra de progresso corre
  no topo do vídeo inteiro.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from .. import titulo
from ..config import (
    ABERTURA_PATH,
    CAPAS_SITE_DIR,
    CLIPS_DIR,
    ENCERRAMENTO_PATH,
    MOLDURA_PATH,
    REPO_DIR,
    VERSUS_PATH,
)
from ..layout import Layout, carregar_layout
from ..roteiro import Roteiro, carregar_roteiro
from . import kit as kit_video
from .downloader import preparar_clip, resolver_ffmpeg
from .midia import duracao as _duracao
from .midia import tem_audio as _tem_audio

if TYPE_CHECKING:  # só para tips; evita import cíclico
    from ..store import Estado

logger = logging.getLogger("batalha.assembler")

LARGURA = 1080
ALTURA = 1920
FPS = 30
COR_BARRA = "0xFFB018"
ALTURA_BARRA = 10


class AssembleError(RuntimeError):
    """Erro ao montar o vídeo do confronto."""


@dataclass
class Sobreposicao:
    """PNG 1080x1920 sobre um segmento.

    ``inicio`` negativo conta a partir do fim do segmento (ex.: ``-3`` = últimos
    3 s); ``fim`` ``None`` = até o fim; ``fade_in`` em segundos.
    """

    png: Path
    inicio: float = 0.0
    fim: float | None = None
    fade_in: float = 0.0


@dataclass
class Segmento:
    fonte: Path
    tipo: str = "tela"  # "tela" (quadro cheio) | "meme" (dentro da moldura)
    titulo: str | None = None
    sobreposicoes: list[Sobreposicao] = field(default_factory=list)
    normalizar_audio: bool = False


# --------------------------------------------------------------------------
# filtros
# --------------------------------------------------------------------------
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


_FORMATO_AUDIO = "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"


def _moldura_tem_alpha(caminho: Path) -> bool:
    """True se a moldura tem janela transparente (canal alfa).

    Nesse caso o clipe é composto **atrás** da moldura e aparece pela janela;
    caso contrário mantém-se o comportamento histórico (clipe sobre a moldura).
    """
    try:
        from PIL import Image

        with Image.open(caminho) as imagem:
            return imagem.mode in ("RGBA", "LA") or "transparency" in imagem.info
    except Exception:  # moldura ilegível/sem PIL: trata como opaca
        return False


def _executar_com_progresso(
    cmd: list[str],
    progresso: Callable[[float], None],
    duracao_total: float,
) -> tuple[int, str]:
    """Roda o ffmpeg lendo ``-progress pipe:1`` e reportando a fração (0..1)."""
    with tempfile.TemporaryFile() as arquivo_erro:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=arquivo_erro,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.stdout is not None
        for linha in proc.stdout:
            campo, _, valor = linha.strip().partition("=")
            if campo in ("out_time_us", "out_time_ms") and valor.strip("-").isdigit():
                segundos = int(valor) / 1_000_000
                if duracao_total > 0:
                    progresso(max(0.0, min(1.0, segundos / duracao_total)))
        proc.wait()
        arquivo_erro.seek(0)
        erro = arquivo_erro.read().decode("utf-8", "replace")
    return proc.returncode, erro


class _Grafo:
    """Acumula entradas (``-i``) e filtros do ``filter_complex``."""

    def __init__(self) -> None:
        self.entradas: list[list[str]] = []
        self.filtros: list[str] = []

    def entrada(self, *args: str) -> int:
        self.entradas.append(list(args))
        return len(self.entradas) - 1

    def __iadd__(self, filtro: str) -> "_Grafo":
        self.filtros.append(filtro)
        return self


def montar_video(
    segmentos: list[Segmento],
    destino: Path | None = None,
    layout: Layout | None = None,
    roteiro: Roteiro | None = None,
    moldura: Path | None = MOLDURA_PATH,
    progresso: Callable[[float], None] | None = None,
) -> Path:
    """Renderiza os segmentos em sequência num único mp4 1080x1920@30.

    ``moldura=None`` desliga a moldura (memes em tela cheia). ``progresso``
    recebe a fração renderizada (0.0 a 1.0).
    """
    ffmpeg = resolver_ffmpeg()
    if ffmpeg is None:
        raise AssembleError("ffmpeg não encontrado")
    if not segmentos:
        raise AssembleError("nenhum segmento para montar")

    layout = (layout or carregar_layout()).normalizar()
    roteiro = (roteiro or carregar_roteiro()).normalizar()
    destino = destino or (CLIPS_DIR / "batalha.mp4")
    destino.parent.mkdir(parents=True, exist_ok=True)

    g = _Grafo()
    duracoes = []
    for seg in segmentos:
        d = _duracao(seg.fonte, ffmpeg)
        if d <= 0:
            raise AssembleError(f"não consegui ler a duração de {seg.fonte}")
        duracoes.append(d)

    # moldura: uma entrada, dividida entre os segmentos de meme
    n_memes = sum(1 for s in segmentos if s.tipo == "meme")
    usar_moldura = moldura is not None and Path(moldura).exists() and n_memes > 0
    transparente = usar_moldura and _moldura_tem_alpha(Path(moldura))
    molduras: list[str] = []
    if usar_moldura:
        i = g.entrada("-i", str(moldura))
        comum = f"[{i}:v]scale={LARGURA}:{ALTURA}:flags=lanczos,setsar=1"
        if transparente:
            # moldura vai POR CIMA: 1 quadro basta (overlay repete o último)
            base = f"{comum},format=rgba"
        else:
            # moldura é o FUNDO: precisa durar todo o clipe
            base = f"{comum},format=yuv420p,loop=loop=-1:size=1:start=0,fps={FPS}"
        molduras = [f"mold{k}" for k in range(n_memes)]
        g += f"{base},split={n_memes}" + "".join(f"[{m}]" for m in molduras)

    rotulos: list[tuple[str, str]] = []
    for k, (seg, dur) in enumerate(zip(segmentos, duracoes)):
        idx = g.entrada("-i", str(seg.fonte))
        atual = f"s{k}e"
        if seg.tipo == "meme" and usar_moldura:
            g += _escalar_meme(idx, f"s{k}m", layout)
            fr = molduras.pop(0)
            if transparente:
                x = max(0, min(layout.px_x(), LARGURA - layout.px_l()))
                y = max(0, min(layout.px_y(), ALTURA - layout.px_a()))
                g += f"[s{k}m]format=rgba,pad={LARGURA}:{ALTURA}:{x}:{y}:color=black[s{k}p]"
                g += f"[s{k}p][{fr}]overlay=0:0:eof_action=repeat[{atual}]"
            else:
                g += (f"[{fr}][s{k}m]overlay={layout.px_x()}:{layout.px_y()}:"
                      f"shortest=1[{atual}]")
        else:
            g += _escalar(idx, atual, LARGURA, ALTURA)

        camadas = list(seg.sobreposicoes)
        if seg.titulo:
            camadas.insert(0, Sobreposicao(titulo.caminho_png(seg.titulo, layout)))
        for j, ov in enumerate(camadas):
            i_ov = g.entrada("-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}",
                             "-i", str(ov.png))
            ini = ov.inicio if ov.inicio >= 0 else max(dur + ov.inicio, 0.0)
            fim = dur if ov.fim is None else ov.fim
            fade = f",fade=t=in:st={ini:.3f}:d={ov.fade_in:.3f}:alpha=1" if ov.fade_in else ""
            g += f"[{i_ov}:v]format=rgba{fade}[s{k}o{j}]"
            proximo = f"s{k}c{j}"
            g += (f"[{atual}][s{k}o{j}]overlay=0:0:eof_action=repeat:"
                  f"enable='between(t,{ini:.3f},{fim:.3f})'[{proximo}]")
            atual = proximo

        # duração exata: congela o último quadro se faltar, corta se sobrar
        g += (f"[{atual}]format=yuv420p,tpad=stop_mode=clone:stop_duration=2,"
              f"trim=duration={dur:.3f},setpts=PTS-STARTPTS,settb=AVTB,fps={FPS}[s{k}v]")
        if _tem_audio(seg.fonte, ffmpeg):
            norm = (f"loudnorm=I={roteiro.lufs}:TP=-1.5:LRA=11,"
                    if seg.normalizar_audio and roteiro.loudnorm else "")
            g += (f"[{idx}:a]{norm}aresample=48000,{_FORMATO_AUDIO},apad,"
                  f"atrim=duration={dur:.3f},asetpts=PTS-STARTPTS[s{k}a]")
        else:
            g += (f"anullsrc=channel_layout=stereo:sample_rate=48000,"
                  f"atrim=duration={dur:.3f},{_FORMATO_AUDIO}[s{k}a]")
        rotulos.append((f"s{k}v", f"s{k}a"))

    # junção: xfade/acrossfade ou concat seco
    trans = 0.0 if roteiro.transicao == "corte" else roteiro.transicao_duracao
    trans = min(trans, min(duracoes) / 3)
    if len(rotulos) == 1:
        v_fim, a_fim = rotulos[0]
        total = duracoes[0]
    elif trans < 0.04:
        g += "".join(f"[{v}][{a}]" for v, a in rotulos) + \
            f"concat=n={len(rotulos)}:v=1:a=1[jv][ja]"
        v_fim, a_fim = "jv", "ja"
        total = sum(duracoes)
    else:
        v_fim, a_fim = rotulos[0]
        acumulado = duracoes[0]
        for k in range(1, len(rotulos)):
            v, a = rotulos[k]
            offset = acumulado - trans
            g += (f"[{v_fim}][{v}]xfade=transition={roteiro.transicao}:"
                  f"duration={trans:.3f}:offset={offset:.3f}[x{k}]")
            g += f"[{a_fim}][{a}]acrossfade=d={trans:.3f}:c1=tri:c2=tri[y{k}]"
            v_fim, a_fim = f"x{k}", f"y{k}"
            acumulado += duracoes[k] - trans
        total = acumulado

    if roteiro.barra_progresso:
        g += (f"color=c={COR_BARRA}:s={LARGURA}x{ALTURA_BARRA}:r={FPS}:"
              f"d={total:.3f}[barra]")
        g += (f"[{v_fim}][barra]overlay=x='-w+w*t/{total:.3f}':y=0:eval=frame,"
              f"format=yuv420p[saida_v]")
        v_fim = "saida_v"

    cmd = [ffmpeg, "-y"]
    for entrada in g.entradas:
        cmd += entrada
    cmd += ["-filter_complex", ";".join(g.filtros), "-map", f"[{v_fim}]", "-map", f"[{a_fim}]"]
    cmd += [
        "-c:v", "libx264", "-preset", roteiro.preset, "-crf", str(roteiro.crf),
        "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", str(FPS * 2),
        "-c:a", "aac", "-b:a", f"{roteiro.audio_kbps}k", "-ar", "48000",
        "-t", f"{total:.3f}",
        "-movflags", "+faststart",
    ]
    if progresso is not None:
        cmd += ["-progress", "pipe:1", "-nostats"]
    cmd += [str(destino)]

    if progresso is None:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
        codigo, erro = proc.returncode, proc.stderr
    else:
        codigo, erro = _executar_com_progresso(cmd, progresso, total)

    if codigo != 0:
        raise AssembleError(f"ffmpeg falhou ({codigo}): {_resumo_erro(erro)}")
    return destino


def _resumo_erro(erro: str | None) -> str:
    """Primeiras linhas de erro do ffmpeg (a causa) + o final do log."""
    linhas = (erro or "").splitlines()
    causa = [l for l in linhas if "rror" in l or "nvalid" in l or "No such" in l][:6]
    return "\n".join(causa + ["..."] + linhas[-4:])


# --------------------------------------------------------------------------
# roteiro -> segmentos
# --------------------------------------------------------------------------
def segmentos_do_roteiro(
    roteiro: Roteiro,
    clip_a: Path,
    clip_b: Path,
    texto_a: str | None,
    texto_b: str | None,
    kit: kit_video.Kit | None,
    abertura: Path | None = ABERTURA_PATH,
    versus: Path | None = VERSUS_PATH,
    encerramento: Path | None = ENCERRAMENTO_PATH,
) -> list[Segmento]:
    """Traduz ``roteiro.sequencia`` em segmentos (arquivos ausentes são pulados)."""

    def _existe(p: Path | None) -> bool:
        return p is not None and Path(p).exists()

    def _meme(clip: Path, texto: str | None, lado: str) -> Segmento:
        sobre: list[Sobreposicao] = []
        if kit is not None and roteiro.selo:
            sobre.append(Sobreposicao(kit.selo[lado]))
        if kit is not None and roteiro.cta_segundos > 0:
            sobre.append(Sobreposicao(kit.cta[lado], inicio=-roteiro.cta_segundos,
                                      fade_in=0.2))
        return Segmento(clip, "meme", titulo=texto, sobreposicoes=sobre,
                        normalizar_audio=True)

    segmentos: list[Segmento] = []
    for nome in roteiro.sequencia:
        if nome == "gancho" and kit is not None and _existe(kit.gancho):
            segmentos.append(Segmento(kit.gancho))
        elif nome == "abertura" and _existe(abertura):
            segmentos.append(Segmento(Path(abertura)))
        elif nome == "versus" and _existe(versus):
            segmentos.append(Segmento(Path(versus)))
        elif nome == "encerramento" and _existe(encerramento):
            sobre = []
            if kit is not None and _existe(kit.encerramento):
                sobre.append(Sobreposicao(kit.encerramento, inicio=0.3, fade_in=0.4))
            segmentos.append(Segmento(Path(encerramento), sobreposicoes=sobre))
        elif nome == "a":
            segmentos.append(_meme(clip_a, texto_a, "a"))
        elif nome == "b":
            segmentos.append(_meme(clip_b, texto_b, "b"))
    return segmentos


def publicar_capa_no_site(capa: Path, match_id: int) -> Path:
    """Copia a capa (JPEG leve, 540x960) para ``frontend/public/capas``.

    A página ``/match/[id]`` e o ``og:image`` usam essa imagem.
    """
    from PIL import Image

    CAPAS_SITE_DIR.mkdir(parents=True, exist_ok=True)
    destino = CAPAS_SITE_DIR / f"match_{match_id}.jpg"
    with Image.open(capa) as img:
        img.convert("RGB").resize((540, 960), Image.LANCZOS).save(
            destino, "JPEG", quality=82, optimize=True, progressive=True
        )
    return destino


def _caminho_relativo(caminho: Path) -> str:
    """Caminho relativo ao repositório (portável entre máquinas) quando possível."""
    try:
        return Path(caminho).resolve().relative_to(REPO_DIR).as_posix()
    except ValueError:
        return str(caminho)


def montar_match(
    estado: "Estado",
    match: dict[str, Any],
    layout: Layout | None = None,
    forcar: bool = False,
    destino: Path | None = None,
    progresso_download: Callable[[float], None] | None = None,
    ao_montar: Callable[[], None] | None = None,
    progresso_montagem: Callable[[float], None] | None = None,
    roteiro: Roteiro | None = None,
) -> Path:
    """Baixa os clipes do confronto, gera o kit e monta o vídeo.

    O título de cada lado é ``titulo_a``/``titulo_b`` do confronto (override
    feito no editor) ou, na ausência, o nome do meme. Grava ``video_path``,
    ``capa_path``, ``duracao`` e marca o confronto como ``pronto`` (persistir o
    estado é com o chamador). A capa é salva ao lado do vídeo
    (``match_N_capa.png``).

    ``progresso_download`` recebe a fração baixada (0.0 a 1.0) somando os dois
    clipes; ``ao_montar`` é chamado quando os downloads terminam e a montagem
    começa; ``progresso_montagem`` recebe a fração da renderização (0.0 a 1.0).
    """
    meme_a = estado.buscar_meme(match["meme_a_id"])
    meme_b = estado.buscar_meme(match["meme_b_id"])
    if meme_a is None or meme_b is None:
        raise AssembleError(f"confronto {match.get('id')}: meme A ou B não encontrado")

    memes = (meme_a, meme_b)
    clips: list[Path] = []
    for indice, meme in enumerate(memes):
        def _callback(fracao: float, _i: int = indice) -> None:
            if progresso_download is not None:
                progresso_download((_i + fracao) / len(memes))

        clips.append(preparar_clip(meme, forcar=forcar, progresso=_callback))
    clip_a, clip_b = clips

    if ao_montar is not None:
        ao_montar()

    layout = (layout or carregar_layout()).normalizar()
    roteiro = (roteiro or carregar_roteiro()).normalizar()
    conf = kit_video.confronto_do_match(estado, match)
    kit = kit_video.gerar_kit(clip_a, clip_b, conf, layout, roteiro)

    destino = destino or CLIPS_DIR / f"match_{match['id']}.mp4"
    segmentos = segmentos_do_roteiro(roteiro, clip_a, clip_b, conf.nome_a, conf.nome_b, kit)
    saida = montar_video(segmentos, destino=destino, layout=layout, roteiro=roteiro,
                         progresso=progresso_montagem)

    capa = saida.with_name(f"{saida.stem}_capa.png")
    shutil.copyfile(kit.capa, capa)
    publicar_capa_no_site(kit.capa, match["id"])
    total = round(_duracao(saida), 2)
    if total > roteiro.duracao_max:
        logger.warning("confronto %s: vídeo com %.1fs (limite sugerido %.0fs)",
                       match.get("id"), total, roteiro.duracao_max)

    match["video_path"] = _caminho_relativo(saida)
    match["capa_path"] = _caminho_relativo(capa)
    match["duracao"] = total
    match["status"] = "pronto"
    return saida


def _cli() -> None:
    import argparse

    from ..config import TMP_DIR
    from ..store import Estado

    parser = argparse.ArgumentParser(description="Monta a batalha de dois memes (avulsa)")
    parser.add_argument("--a", type=int, required=True, help="id do meme A")
    parser.add_argument("--b", type=int, required=True, help="id do meme B")
    parser.add_argument("--sequencia", nargs="*", default=None,
                        help="sobrescreve roteiro.sequencia (ex.: gancho a versus b)")
    parser.add_argument("--sem-gancho", action="store_true")
    parser.add_argument("--sem-abertura", action="store_true")
    parser.add_argument("--sem-moldura", action="store_true")
    parser.add_argument("--sem-encerramento", action="store_true")
    parser.add_argument("--sem-versus", action="store_true")
    parser.add_argument("--forcar", action="store_true", help="ignora o cache de download")
    parser.add_argument("--saida", type=str, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    estado = Estado.carregar()
    meme_a = estado.buscar_meme(args.a)
    meme_b = estado.buscar_meme(args.b)
    if meme_a is None or meme_b is None:
        raise SystemExit("meme A ou B não encontrado")

    clip_a = preparar_clip(meme_a, forcar=args.forcar)
    clip_b = preparar_clip(meme_b, forcar=args.forcar)

    roteiro = carregar_roteiro()
    if args.sequencia:
        roteiro.sequencia = args.sequencia
    for flag, nome in (("sem_gancho", "gancho"), ("sem_abertura", "abertura"),
                       ("sem_encerramento", "encerramento"), ("sem_versus", "versus")):
        if getattr(args, flag):
            roteiro.sequencia = [s for s in roteiro.sequencia if s != nome]
    roteiro.normalizar()

    layout = carregar_layout()
    conf = kit_video.Confronto(meme_a["nome"], meme_b["nome"])
    kit = kit_video.gerar_kit(clip_a, clip_b, conf, layout, roteiro)
    destino = Path(args.saida) if args.saida else TMP_DIR / f"batalha_{meme_a['id']}_{meme_b['id']}.mp4"
    segmentos = segmentos_do_roteiro(roteiro, clip_a, clip_b, meme_a["nome"], meme_b["nome"], kit)
    saida = montar_video(segmentos, destino=destino, layout=layout, roteiro=roteiro,
                         moldura=None if args.sem_moldura else MOLDURA_PATH)
    print(saida)


if __name__ == "__main__":
    _cli()
