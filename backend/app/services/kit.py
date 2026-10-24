"""Kit de vídeo procedural — assets gerados por código (PIL + ffmpeg), sem IA.

Para cada confronto o kit produz:

- **gancho** (``gancho.mp4``, ~1,6 s): os dois memes entram pelos lados, o "VS"
  bate no centro com flash/tremida e som sintetizado (whoosh + impacto), com a
  rodada no topo e "QUEM VENCE? / COMENTE A OU B" embaixo;
- **capa** (``capa.png``): o último quadro do gancho — capa do TikTok/Reels e
  imagem de compartilhamento;
- **selo** A/B (``selo_a.png``/``selo_b.png``): badge no canto do telão;
- **CTA** (``cta_a.png``/``cta_b.png``): faixa "COMENTE A/B" para o fim de cada meme;
- **encerramento** (``encerramento.png``): fotos e nomes dos memes encaixados
  nos painéis "MEME 1 / MEME 2" do ``videos/encerramento.mp4``.

Tudo é cacheado em ``tmp/kit/<hash>/`` — o hash muda quando nomes, clipes,
layout ou o próprio kit (``KIT_VERSAO``) mudam.

CLI (gera só o kit, para conferir o visual sem renderizar o vídeo)::

    python -m app.services.kit --match 1
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from .. import titulo
from ..config import KIT_DIR
from ..layout import ALTURA, LARGURA, Layout
from ..roteiro import PaineisEncerramento, Roteiro
from .midia import _ffmpeg, duracao, quadro

KIT_VERSAO = 1
FPS = 30

AZUL = (56, 189, 255)
LARANJA = (255, 128, 36)
BRANCO = (255, 255, 255)
CREME = (255, 247, 199)
FUNDO = (9, 11, 20)
CORES_LADO = {"a": AZUL, "b": LARANJA}

# Geometria do gancho (px em 1080x1920)
PAINEL_L, PAINEL_A = 450, 760
PAINEL_Y = 560
PAINEL_CX = {"a": 290, "b": 790}


@dataclass
class Confronto:
    """Textos que o kit precisa (independente do estado.json)."""

    nome_a: str
    nome_b: str
    rodada: str = "BATALHA DE MEMES"
    jogo: str = ""


@dataclass
class Kit:
    pasta: Path
    gancho: Path
    capa: Path
    selo: dict[str, Path]
    cta: dict[str, Path]
    encerramento: Path


# --------------------------------------------------------------------------
# contexto do confronto
# --------------------------------------------------------------------------
def rotulo_rodada(vagas: int) -> str:
    """Nome da fase pelo nº de competidores que entram nela."""
    nomes = {2: "FINAL", 4: "SEMIFINAL", 8: "QUARTAS DE FINAL", 16: "OITAVAS DE FINAL"}
    return nomes.get(vagas, f"{vagas // 2} AVOS DE FINAL")


# --------------------------------------------------------------------------
# primitivas de desenho
# --------------------------------------------------------------------------
def _ease(x: float) -> float:
    """Ease-out cúbico em [0, 1]."""
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def _camada() -> Image.Image:
    return Image.new("RGBA", (LARGURA, ALTURA), (0, 0, 0, 0))


def _recortar(camada: Image.Image) -> tuple[Image.Image, tuple[int, int]]:
    """Recorta a camada no conteúdo; devolve (imagem, posição no quadro)."""
    caixa = camada.getbbox() or (0, 0, 1, 1)
    return camada.crop(caixa), (caixa[0], caixa[1])


def _texto(
    camada: Image.Image,
    texto: str,
    centro: tuple[float, float],
    largura_max: float,
    teto: int,
    topo: tuple = CREME,
    base: tuple = titulo.COR_BASE,
    linhas_max: int = 2,
    contorno: int = 8,
) -> None:
    linhas, tamanho = titulo.encaixar(texto, largura_max, teto, linhas_max)
    titulo.pintar(camada, linhas, tamanho, centro, topo=topo, base=base,
                  contorno=contorno, sombra=(4, 5))


def _alpha(img: Image.Image, fator: float) -> Image.Image:
    if fator >= 1:
        return img
    copia = img.copy()
    copia.putalpha(img.getchannel("A").point(lambda v: round(v * max(fator, 0.0))))
    return copia


def _brilho(tamanho: tuple[int, int], caixa: tuple[int, int, int, int], cor: tuple,
            raio: int, espessura: int, desfoque: int) -> Image.Image:
    """Contorno neon: traço desfocado (halo) + traço nítido por cima."""
    halo = Image.new("RGBA", tamanho, (0, 0, 0, 0))
    ImageDraw.Draw(halo).rounded_rectangle(caixa, raio, outline=cor + (255,),
                                           width=espessura * 3)
    halo = halo.filter(ImageFilter.GaussianBlur(desfoque))
    nitido = Image.new("RGBA", tamanho, (0, 0, 0, 0))
    ImageDraw.Draw(nitido).rounded_rectangle(caixa, raio, outline=cor + (255,),
                                             width=espessura)
    halo.alpha_composite(halo)  # reforça o halo
    halo.alpha_composite(nitido)
    return halo


def _foto(img: Image.Image, largura: int, altura: int, raio: int) -> Image.Image:
    """Foto em ``cover`` com cantos arredondados (RGBA)."""
    foto = ImageOps.fit(img, (largura, altura), Image.LANCZOS).convert("RGBA")
    mascara = Image.new("L", (largura, altura), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, largura - 1, altura - 1), raio, fill=255)
    foto.putalpha(mascara)
    return foto


def _cartao(img: Image.Image, lado: str, largura: int = PAINEL_L,
            altura: int = PAINEL_A) -> Image.Image:
    """Foto do meme com moldura neon da cor do lado (com margem para o halo)."""
    margem = 40
    total = (largura + 2 * margem, altura + 2 * margem)
    cartao = Image.new("RGBA", total, (0, 0, 0, 0))
    caixa = (margem, margem, margem + largura - 1, margem + altura - 1)
    cartao.alpha_composite(_foto(img, largura, altura, 34), (margem, margem))
    # escurece a base da foto para o badge/nome ficarem legíveis
    sombra = Image.new("RGBA", (largura, altura // 3), (0, 0, 0, 0))
    for y in range(sombra.height):
        ImageDraw.Draw(sombra).line([(0, y), (largura, y)],
                                    fill=(0, 0, 0, round(170 * y / sombra.height)))
    base = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    base.alpha_composite(sombra, (0, altura - sombra.height))
    mascara = _foto(img, largura, altura, 34).getchannel("A")
    base.putalpha(ImageChops.multiply(base.getchannel("A"), mascara))
    cartao.alpha_composite(base, (margem, margem))
    cartao.alpha_composite(_brilho(total, caixa, CORES_LADO[lado], 34, 7, 14))
    return cartao


def _badge(camada: Image.Image, letra: str, centro: tuple[int, int], raio: int,
           cor: tuple) -> None:
    """Círculo da cor do lado com a letra A/B."""
    x, y = centro
    desenho = ImageDraw.Draw(camada)
    desenho.ellipse((x - raio - 6, y - raio - 6, x + raio + 6, y + raio + 6),
                    fill=(12, 12, 14, 255))
    desenho.ellipse((x - raio, y - raio, x + raio, y + raio), fill=cor + (255,),
                    outline=BRANCO + (255,), width=max(3, raio // 10))
    titulo.pintar(camada, [letra.lower()], round(raio * 1.25), (x, y + raio * 0.04),
                  topo=BRANCO, base=BRANCO, contorno=max(4, raio // 9), sombra=(0, 0))


def _fundo() -> Image.Image:
    """Fundo escuro com metade azul (A) e metade laranja (B) + vinheta."""
    img = Image.new("RGB", (LARGURA, ALTURA), FUNDO)
    brilho = Image.new("RGBA", (LARGURA, ALTURA), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(brilho)
    desenho.ellipse((-500, 300, 640, 1600), fill=AZUL + (70,))
    desenho.ellipse((440, 300, 1580, 1600), fill=LARANJA + (70,))
    brilho = brilho.filter(ImageFilter.GaussianBlur(160))
    img = img.convert("RGBA")
    img.alpha_composite(brilho)
    # listras diagonais sutis (textura de "arena")
    listras = Image.new("RGBA", (LARGURA, ALTURA), (0, 0, 0, 0))
    d = ImageDraw.Draw(listras)
    for x in range(-ALTURA, LARGURA, 46):
        d.line([(x, ALTURA), (x + ALTURA, 0)], fill=(255, 255, 255, 9), width=10)
    img.alpha_composite(listras)
    return img


# --------------------------------------------------------------------------
# gancho (animação quadro a quadro, enviada crua para o ffmpeg)
# --------------------------------------------------------------------------
class _Gancho:
    def __init__(self, foto_a: Image.Image, foto_b: Image.Image, conf: Confronto,
                 duracao_s: float) -> None:
        self.duracao = duracao_s
        self.fundo = _fundo()

        topo = _camada()
        _texto(topo, conf.rodada, (540, 230), 980, 100, linhas_max=1)
        if conf.jogo:
            _texto(topo, conf.jogo, (540, 340), 900, 54, topo=BRANCO, base=(200, 210, 230),
                   linhas_max=1, contorno=6)
        self.topo = _recortar(topo)

        self.paineis = {}
        for lado, foto, nome in (("a", foto_a, conf.nome_a), ("b", foto_b, conf.nome_b)):
            camada = _camada()
            cx = PAINEL_CX[lado]
            cartao = _cartao(foto, lado)
            camada.alpha_composite(cartao, (cx - cartao.width // 2, PAINEL_Y - 40))
            _texto(camada, nome, (cx, PAINEL_Y - 70), PAINEL_L + 50, 76,
                   topo=BRANCO, base=CORES_LADO[lado])
            _badge(camada, lado, (cx, PAINEL_Y + PAINEL_A - 10), 66, CORES_LADO[lado])
            self.paineis[lado] = _recortar(camada)

        vs = _camada()
        _texto(vs, "vs", (540, 940), 600, 250, linhas_max=1, contorno=14)
        self.vs = _recortar(vs)

        baixo = _camada()
        _texto(baixo, "quem vence?", (540, 1530), 1000, 128, linhas_max=1)
        _texto(baixo, "comente a ou b", (540, 1665), 900, 70, topo=BRANCO,
               base=(210, 220, 235), linhas_max=1, contorno=6)
        self.baixo = _recortar(baixo)

    def quadro(self, t: float) -> Image.Image:
        img = self.fundo.copy()

        # topo: fade-in
        img.alpha_composite(_alpha(self.topo[0], t / 0.3), self.topo[1])

        # painéis entram pelos lados
        deslocamento = (1 - _ease(t / 0.35)) * 760
        for lado, sinal in (("a", -1), ("b", 1)):
            camada, (x, y) = self.paineis[lado]
            # paste aceita posição fora do quadro (alpha_composite não)
            img.paste(camada, (round(x + sinal * deslocamento), y), camada)

        # VS bate no centro (escala 3x -> 1x)
        if t >= 0.3:
            s = (t - 0.3) / 0.18
            escala = 1 + 2.2 * (1 - _ease(s))
            camada, (x, y) = self.vs
            if escala != 1:
                nova = (round(camada.width * escala), round(camada.height * escala))
                cx, cy = x + camada.width / 2, y + camada.height / 2
                camada = camada.resize(nova, Image.BILINEAR)
                x, y = round(cx - nova[0] / 2), round(cy - nova[1] / 2)
            img.paste(_alpha(camada, s * 2), (x, y), _alpha(camada, s * 2))

        # textos de baixo
        img.alpha_composite(_alpha(self.baixo[0], (t - 0.55) / 0.3), self.baixo[1])

        # flash + tremida no impacto
        if 0.48 <= t < 0.72:
            forca = 1 - (t - 0.48) / 0.24
            branco = Image.new("RGBA", img.size, (255, 255, 255, round(150 * forca)))
            img.alpha_composite(branco)
        if 0.48 <= t < 0.8:
            amp = 16 * (1 - (t - 0.48) / 0.32)
            img = ImageChops.offset(img, round(amp * math.sin(t * 95)),
                                    round(amp * math.cos(t * 77)))
        return img.convert("RGB")


# whoosh enquanto os painéis entram + impacto (grave + ruído) quando o VS bate
_AUDIO_GANCHO = (
    "anoisesrc=d=0.42:c=pink:r=48000:a=0.45,highpass=f=350,lowpass=f=5000,"
    "afade=t=in:d=0.3,afade=t=out:st=0.3:d=0.12[wh];"
    "sine=frequency=52:duration=1.1:sample_rate=48000,volume=2.4,"
    "afade=t=out:st=0.04:d=1.0[bo];"
    "anoisesrc=d=0.35:c=brown:r=48000:a=0.9,lowpass=f=1400,afade=t=out:d=0.35[cr];"
    "[bo][cr]amix=inputs=2:normalize=0,adelay=470:all=1[im];"
    "[wh][im]amix=inputs=2:normalize=0:duration=longest,volume=0.8,"
    "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
    "apad,atrim=duration={dur:.3f}[aout]"
)


def _renderizar_gancho(gancho: _Gancho, destino: Path) -> None:
    total = round(gancho.duracao * FPS)
    cmd = [
        _ffmpeg(), "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{LARGURA}x{ALTURA}",
        "-r", str(FPS), "-i", "-",
        "-filter_complex", _AUDIO_GANCHO.format(dur=gancho.duracao),
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", f"{gancho.duracao:.3f}",
        str(destino),
    ]
    with tempfile.TemporaryFile() as erro:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=erro)
        assert proc.stdin is not None
        try:
            for i in range(total):
                proc.stdin.write(gancho.quadro(i / FPS).tobytes())
        except BrokenPipeError:
            pass
        finally:
            proc.stdin.close()
        proc.wait()
        if proc.returncode != 0:
            erro.seek(0)
            raise RuntimeError(f"ffmpeg (gancho) falhou: {erro.read().decode('utf-8', 'replace')[-600:]}")


# --------------------------------------------------------------------------
# sobreposições estáticas (PNG 1080x1920)
# --------------------------------------------------------------------------
def _selo(lado: str, layout: Layout) -> Image.Image:
    camada = _camada()
    raio = 58
    _badge(camada, lado, (layout.px_x() + raio + 26, layout.px_y() + raio + 26), raio,
           CORES_LADO[lado])
    return camada


def _cta(lado: str, layout: Layout) -> Image.Image:
    """Faixa "COMENTE [A]" na base do telão."""
    camada = _camada()
    largura = min(layout.px_l() - 60, 780)
    altura = 124
    cx = layout.px_x() + layout.px_l() // 2
    y1 = layout.px_y() + layout.px_a() - 36
    caixa = (cx - largura // 2, y1 - altura, cx + largura // 2, y1)
    ImageDraw.Draw(camada).rounded_rectangle(caixa, 30, fill=(10, 12, 20, 230))
    camada.alpha_composite(_brilho(camada.size, caixa, CORES_LADO[lado], 30, 5, 10))

    fonte = 70
    texto = "comente"
    largura_txt = titulo._medir_prep(texto, fonte)
    raio = 46
    espaco = 26
    x0 = cx - (largura_txt + espaco + 2 * raio) / 2
    ym = (caixa[1] + caixa[3]) / 2
    titulo.pintar(camada, [texto], fonte, (x0 + largura_txt / 2, ym), topo=BRANCO,
                  base=(215, 222, 235), contorno=6, sombra=(3, 4))
    _badge(camada, lado, (round(x0 + largura_txt + espaco + raio), round(ym)), raio,
           CORES_LADO[lado])
    return camada


def _encerramento(foto_a: Image.Image, foto_b: Image.Image, conf: Confronto,
                  paineis: PaineisEncerramento) -> Image.Image:
    """Fotos e nomes nos painéis "MEME 1/2" do encerramento, sem cobrir o VS."""
    camada = _camada()
    cx_vs, cy_vs, r_vs = paineis.vs
    for lado, foto, nome, painel, rotulo in (
        ("a", foto_a, conf.nome_a, paineis.painel_a, paineis.rotulo_a),
        ("b", foto_b, conf.nome_b, paineis.painel_b, paineis.rotulo_b),
    ):
        x, y, l, a = painel
        img = _foto(foto, l, a, 20)
        # abre um "buraco" para o círculo do VS continuar visível
        buraco = Image.new("L", (l, a), 255)
        ImageDraw.Draw(buraco).ellipse(
            (cx_vs - r_vs - x, cy_vs - r_vs - y, cx_vs + r_vs - x, cy_vs + r_vs - y), fill=0
        )
        img.putalpha(ImageChops.multiply(img.getchannel("A"), buraco))
        camada.alpha_composite(img, (x, y))
        _badge(camada, lado, (x + l // 2, y + a - 70), 52, CORES_LADO[lado])

        rx, ry, rl, ra = rotulo
        ImageDraw.Draw(camada).rounded_rectangle(
            (rx, ry, rx + rl, ry + ra), 14, fill=(12, 14, 24, 255),
            outline=CORES_LADO[lado] + (255,), width=4,
        )
        _texto(camada, nome, (rx + rl / 2, ry + ra / 2), rl - 24, 54, topo=BRANCO,
               base=CORES_LADO[lado], contorno=5)
    return camada


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
def _instante_foto(clip: Path) -> float:
    """Quadro representativo: 40% do clipe (evita tela preta do início)."""
    return max(duracao(clip) * 0.4, 0.0)


def _chave(clip_a: Path, clip_b: Path, conf: Confronto, layout: Layout,
           roteiro: Roteiro) -> str:
    dados = {
        "v": KIT_VERSAO,
        "conf": asdict(conf),
        "clips": [str(c) for c in (clip_a, clip_b)],
        "mtimes": [c.stat().st_mtime if c.exists() else 0 for c in (clip_a, clip_b)],
        "layout": layout.para_dict(),
        "gancho": roteiro.gancho_duracao,
        "paineis": asdict(roteiro.encerramento),
    }
    return hashlib.sha1(json.dumps(dados, sort_keys=True).encode()).hexdigest()[:12]


def gerar_kit(clip_a: Path, clip_b: Path, conf: Confronto, layout: Layout,
              roteiro: Roteiro, pasta: Path | None = None) -> Kit:
    """Gera (ou reaproveita do cache) todos os assets do confronto."""
    pasta = pasta or KIT_DIR / _chave(clip_a, clip_b, conf, layout, roteiro)
    kit = Kit(
        pasta=pasta,
        gancho=pasta / "gancho.mp4",
        capa=pasta / "capa.png",
        selo={l: pasta / f"selo_{l}.png" for l in "ab"},
        cta={l: pasta / f"cta_{l}.png" for l in "ab"},
        encerramento=pasta / "encerramento.png",
    )
    arquivos = [kit.gancho, kit.capa, kit.encerramento, *kit.selo.values(), *kit.cta.values()]
    if all(a.exists() for a in arquivos):
        return kit

    pasta.mkdir(parents=True, exist_ok=True)
    foto_a = quadro(clip_a, _instante_foto(clip_a))
    foto_b = quadro(clip_b, _instante_foto(clip_b))

    gancho = _Gancho(foto_a, foto_b, conf, roteiro.gancho_duracao)
    gancho.quadro(roteiro.gancho_duracao).save(kit.capa)
    _renderizar_gancho(gancho, kit.gancho)

    for lado in "ab":
        _selo(lado, layout).save(kit.selo[lado])
        _cta(lado, layout).save(kit.cta[lado])
    _encerramento(foto_a, foto_b, conf, roteiro.encerramento).save(kit.encerramento)
    return kit


def confronto_do_match(estado, match: dict) -> Confronto:
    """Monta o ``Confronto`` (nomes, fase e nº do jogo) a partir do estado."""
    meme_a = estado.buscar_meme(match["meme_a_id"]) or {}
    meme_b = estado.buscar_meme(match["meme_b_id"]) or {}
    conf = Confronto(
        nome_a=match.get("titulo_a") or meme_a.get("nome", "A"),
        nome_b=match.get("titulo_b") or meme_b.get("nome", "B"),
    )
    torneio = estado.buscar_torneio(match["tournament_id"])
    if torneio and torneio.get("tamanho"):
        vagas = int(torneio["tamanho"]) >> (int(match["round"]) - 1)
        conf.rodada = rotulo_rodada(vagas)
        jogos = vagas // 2
        if jogos > 1:
            conf.jogo = f"jogo {int(match['posicao']) + 1} de {jogos}"
    return conf


def _cli() -> None:
    import argparse

    from ..layout import carregar_layout
    from ..roteiro import carregar_roteiro
    from ..store import Estado
    from .downloader import preparar_clip

    parser = argparse.ArgumentParser(description="Gera o kit de vídeo de um confronto")
    parser.add_argument("--match", type=int, required=True)
    args = parser.parse_args()

    estado = Estado.carregar()
    match = estado.buscar_match(args.match)
    if match is None or not match.get("meme_a_id") or not match.get("meme_b_id"):
        raise SystemExit("confronto inexistente ou incompleto")
    clip_a = preparar_clip(estado.buscar_meme(match["meme_a_id"]))
    clip_b = preparar_clip(estado.buscar_meme(match["meme_b_id"]))
    kit = gerar_kit(clip_a, clip_b, confronto_do_match(estado, match), carregar_layout(),
                    carregar_roteiro())
    print(kit.pasta)


if __name__ == "__main__":
    _cli()
