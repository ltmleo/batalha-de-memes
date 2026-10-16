"""Título do vídeo: fonte de meme, cor e contorno.

Compartilhado pelo vídeo final (``services/assembler``) e pelo preview do editor
(``editor/preview``). O título é renderizado num PNG RGBA de quadro cheio
(gradiente no interior + contorno preto) e sobreposto ao vídeo — assim o preview
e o arquivo final ficam idênticos, sem depender das métricas do ``drawtext``.

A fonte (Dream MMA) desenha caixa-alta nos glifos minúsculos e não tem acentos;
por isso ``preparar`` normaliza o texto para minúsculo e sem acento (á->a, ç->c),
descartando o que a fonte não cobre.

Títulos longos que ficariam pequenos demais numa linha são quebrados em até duas
linhas (centralizadas) para manter o texto grande e legível.
"""

from __future__ import annotations

import hashlib
import unicodedata
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import FONTE_TITULO_PATH, TMP_DIR
from .layout import ALTURA, LARGURA, Layout

# Ajuste automático do tamanho
FONTE_MIN = 24   # piso sugerido (o editor usa como mínimo do campo manual)
FONTE_MAX = 150
FONTE_LEGIVEL = 44  # abaixo disso numa linha, tenta quebrar em duas
LINHAS_MAX = 2
ESPACO_LINHA = 1.06  # altura da linha / tamanho da fonte
FAIXA_ALTURA = round(0.10 * ALTURA)  # altura reservada para o título

# Estilo do título (px na escala 1080x1920)
CONTORNO = 10                          # espessura do contorno preto
SOMBRA = (5, 6)                        # deslocamento da sombra
COR_TOPO = (255, 247, 199)             # gradiente: topo (amarelo claro)
COR_BASE = (255, 176, 24)             # gradiente: base (dourado)
COR_CONTORNO = (12, 12, 14)            # cor do contorno/sombra

DIR_TITULOS = TMP_DIR / "titulos"

# a fonte cobre apenas isto (após minúsculas e sem acento)
_PERMITIDOS = set("abcdefghijklmnopqrstuvwxyz0123456789 .:")


def preparar(texto: str) -> str:
    """Normaliza o texto para a Dream MMA: minúsculas, sem acento, sem ruído."""
    base = unicodedata.normalize("NFKD", str(texto).lower())
    saida = [c if c in _PERMITIDOS else " " for c in base if not unicodedata.combining(c)]
    return " ".join("".join(saida).split())


@lru_cache(maxsize=96)
def _fonte_pil(tamanho: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTE_TITULO_PATH), max(1, int(tamanho)))


def _medir_prep(prep: str, tamanho: int) -> float:
    return float(_fonte_pil(tamanho).getlength(prep))


def medir(texto: str, tamanho: int) -> float:
    """Largura real (px) do texto preparado numa linha, na fonte do título."""
    return _medir_prep(preparar(texto), tamanho)


def _quebrar(prep: str, tamanho: int) -> list[str]:
    """Melhor divisão em duas linhas (menor largura máxima) para o tamanho dado."""
    palavras = prep.split()
    if len(palavras) < 2:
        return [prep]
    melhor: tuple[float, list[str]] | None = None
    for i in range(1, len(palavras)):
        linha1, linha2 = " ".join(palavras[:i]), " ".join(palavras[i:])
        largura = max(_medir_prep(linha1, tamanho), _medir_prep(linha2, tamanho))
        if melhor is None or largura < melhor[0]:
            melhor = (largura, [linha1, linha2])
    return melhor[1]


def _maior_1linha(prep: str, largura_max: float, teto: int) -> int:
    tamanho_atual = teto
    while tamanho_atual > 1 and _medir_prep(prep, tamanho_atual) > largura_max:
        tamanho_atual -= 1
    return tamanho_atual


def _melhor_2linhas(prep: str, largura_max: float, teto: int) -> tuple[list[str], int] | None:
    if len(prep.split()) < 2:
        return None
    for tamanho_atual in range(teto, 0, -1):
        linhas = _quebrar(prep, tamanho_atual)
        if len(linhas) == 2 and max(_medir_prep(l, tamanho_atual) for l in linhas) <= largura_max:
            return linhas, tamanho_atual
    return None


def _dispor(texto: str, layout: Layout) -> tuple[list[str], int]:
    """Devolve (linhas, tamanho) que cabem na faixa do título."""
    prep = preparar(texto)
    if not prep:
        return [], 0
    if layout.titulo_fonte > 0:  # tamanho fixo escolhido no editor: uma linha
        return [prep], int(layout.titulo_fonte)

    largura_max = 0.98 * layout.px_titulo_largura()
    teto_1 = int(min(FONTE_MAX, 0.95 * FAIXA_ALTURA / 1.05))
    tamanho_1 = _maior_1linha(prep, largura_max, teto_1)
    if tamanho_1 >= FONTE_LEGIVEL:
        return [prep], tamanho_1

    teto_2 = int(min(FONTE_MAX, 0.95 * FAIXA_ALTURA / (LINHAS_MAX * ESPACO_LINHA)))
    em_duas = _melhor_2linhas(prep, largura_max, teto_2)
    if em_duas is not None and em_duas[1] > tamanho_1:
        return em_duas
    return [prep], tamanho_1


def tamanho(texto: str, layout: Layout | None = None) -> int:
    """Tamanho da fonte usado no título (considerando a quebra de linha)."""
    return _dispor(texto, layout or Layout())[1]


def _gradiente(largura: int, altura: int, y0: int, y1: int) -> Image.Image:
    """Gradiente vertical (topo -> base) com as cores do título."""
    img = Image.new("RGB", (largura, altura))
    desenho = ImageDraw.Draw(img)
    span = max(1, y1 - y0)
    for y in range(altura):
        t = min(max((y - y0) / span, 0.0), 1.0)
        cor = tuple(round(COR_TOPO[i] + (COR_BASE[i] - COR_TOPO[i]) * t) for i in range(3))
        desenho.line([(0, y), (largura, y)], fill=cor)
    return img


def _imagem(texto: str, t_y: float, t_larg: float, t_fonte: int) -> Image.Image:
    layout = Layout(titulo_y=t_y, titulo_largura=t_larg, titulo_fonte=t_fonte)
    camada = Image.new("RGBA", (LARGURA, ALTURA), (0, 0, 0, 0))
    linhas, tamanho_fonte = _dispor(texto, layout)
    if not linhas:
        return camada

    fonte = _fonte_pil(tamanho_fonte)
    espaco = ESPACO_LINHA * tamanho_fonte
    y0 = layout.px_titulo_y() - espaco * (len(linhas) - 1) / 2
    posicoes = [(LARGURA // 2, round(y0 + i * espaco)) for i in range(len(linhas))]

    desenho = ImageDraw.Draw(camada)
    if SOMBRA != (0, 0):
        for (x, y), linha in zip(posicoes, linhas):
            desenho.text((x + SOMBRA[0], y + SOMBRA[1]), linha, font=fonte,
                         fill=COR_CONTORNO + (150,), anchor="mm")
    for (x, y), linha in zip(posicoes, linhas):
        desenho.text((x, y), linha, font=fonte, fill=COR_CONTORNO + (255,), anchor="mm",
                     stroke_width=CONTORNO, stroke_fill=COR_CONTORNO + (255,))

    mascara = Image.new("L", (LARGURA, ALTURA), 0)
    mascara_desenho = ImageDraw.Draw(mascara)
    for (x, y), linha in zip(posicoes, linhas):
        mascara_desenho.text((x, y), linha, font=fonte, fill=255, anchor="mm")
    caixa = mascara.getbbox()
    if caixa is not None:
        gradiente = _gradiente(LARGURA, ALTURA, caixa[1], caixa[3]).convert("RGBA")
        gradiente.putalpha(mascara)
        camada.alpha_composite(gradiente)
    return camada


@lru_cache(maxsize=32)
def _imagem_cache(texto: str, t_y: float, t_larg: float, t_fonte: int) -> Image.Image:
    return _imagem(texto, t_y, t_larg, t_fonte)


def imagem(texto: str, layout: Layout | None = None) -> Image.Image:
    """Título como camada RGBA de quadro cheio (1080x1920)."""
    layout = layout or Layout()
    return _imagem_cache(texto, round(layout.titulo_y, 4), round(layout.titulo_largura, 4),
                         int(layout.titulo_fonte)).copy()


def caminho_png(texto: str, layout: Layout | None = None) -> Path:
    """Salva a camada do título num PNG (cacheado) e devolve o caminho."""
    layout = layout or Layout()
    chave = (
        f"{texto}|{layout.titulo_y:.4f}|{layout.titulo_largura:.4f}|{layout.titulo_fonte}"
        f"|{COR_TOPO}|{COR_BASE}|{COR_CONTORNO}|{CONTORNO}|{SOMBRA}|{LARGURA}x{ALTURA}"
    )
    nome = hashlib.md5(chave.encode("utf-8")).hexdigest()[:12]
    DIR_TITULOS.mkdir(parents=True, exist_ok=True)
    destino = DIR_TITULOS / f"titulo_{nome}.png"
    if not destino.exists():
        imagem(texto, layout).save(destino)
    return destino
