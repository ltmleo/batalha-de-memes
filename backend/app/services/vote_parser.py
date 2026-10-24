"""Apuração dos votos de um confronto a partir dos comentários.

A coleta é desacoplada: os comentários chegam por **arquivo** (exportação,
cópia manual ou, no futuro, o ``scraper``) e são salvos brutos em
``data/raw/match_{id}.json`` para auditoria/recontagem.

Formatos aceitos em ``ler_comentarios``:

- ``.json``: lista de objetos com ``usuario``/``user``/``author``,
  ``texto``/``text``/``comment`` e, opcional, ``criado_em``/``create_time``
  (ISO-8601 ou epoch);
- ``.csv``: colunas ``usuario,texto[,criado_em]`` (com cabeçalho);
- ``.txt``: uma linha por comentário, ``usuario: texto`` (ou separado por TAB).

Regras (ver SPEC §4):

1. normaliza (minúsculas, sem acento);
2. extrai a escolha: comentário que é só ``a``/``b``/``1``/``2``, frases como
   "voto no A", "time B", "meme 1", emojis 🅰️/🅱️ ou o nome do meme;
   comentário que cita os dois lados é inválido;
3. **um voto por usuário** (o primeiro válido);
4. só conta entre ``publicado_em`` e ``deadline`` quando há horário;
5. vencedor = mais votos válidos; empate é desfeito pelo ``seed`` do torneio.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import RAW_DATA_DIR
from ..store import Estado, agora, gravar_json_atomico

_PALAVRAS_VAZIAS = {
    "o", "a", "os", "as", "de", "do", "da", "dos", "das", "e", "que", "no", "na",
    "meme", "memes", "pai", "seu", "sua", "eu", "nao", "um", "uma", "com", "pra",
}
_EMOJI = {"🅰": "A", "🅱": "B"}
_FRASE = re.compile(
    r"\b(?:voto|vote|votei|votando|time|meme|letra|opcao|equipe|vai|fecho|fechado)\s+"
    r"(?:(?:no|na|o|a|com|de|do|da)\s+)?([ab12])\b"
)
_SOZINHO = re.compile(r"^(?:o|a|no|na)?\s*([ab12])$")


@dataclass
class Comentario:
    usuario: str
    texto: str
    criado_em: str | None = None


@dataclass
class Apuracao:
    votos_a: int = 0
    votos_b: int = 0
    validos: int = 0
    invalidos: int = 0
    duplicados: int = 0
    fora_do_prazo: int = 0
    votos: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.votos_a + self.votos_b


# --------------------------------------------------------------------------
# leitura
# --------------------------------------------------------------------------
def _primeiro(item: dict[str, Any], *chaves: str) -> Any:
    for chave in chaves:
        if item.get(chave) not in (None, ""):
            return item[chave]
    return None


def _iso(valor: Any) -> str | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, (int, float)) or str(valor).isdigit():
        seg = float(valor)
        if seg > 1e12:  # milissegundos
            seg /= 1000
        return datetime.fromtimestamp(seg, timezone.utc).isoformat().replace("+00:00", "Z")
    return str(valor)


def ler_comentarios(caminho: Path) -> list[Comentario]:
    caminho = Path(caminho)
    sufixo = caminho.suffix.lower()
    if sufixo == ".json":
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        if isinstance(dados, dict):
            dados = _primeiro(dados, "comentarios", "comments", "data") or []
        return [
            Comentario(
                usuario=str(_primeiro(c, "usuario", "user", "author", "unique_id", "nickname") or ""),
                texto=str(_primeiro(c, "texto", "text", "comment", "comentario") or ""),
                criado_em=_iso(_primeiro(c, "criado_em", "create_time", "created_at", "timestamp")),
            )
            for c in dados
            if isinstance(c, dict)
        ]
    if sufixo == ".csv":
        with caminho.open(encoding="utf-8-sig", newline="") as arq:
            return [
                Comentario(
                    usuario=str(_primeiro(l, "usuario", "user", "author") or ""),
                    texto=str(_primeiro(l, "texto", "text", "comment", "comentario") or ""),
                    criado_em=_iso(_primeiro(l, "criado_em", "create_time", "created_at")),
                )
                for l in csv.DictReader(arq)
            ]
    comentarios = []
    for n, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), 1):
        if not linha.strip():
            continue
        usuario, sep, texto = linha.partition("\t") if "\t" in linha else linha.partition(":")
        if not sep:  # sem autor: cada linha vira um "usuário" (sem dedupe)
            usuario, texto = f"linha-{n}", linha
        comentarios.append(Comentario(usuario.strip(), texto.strip()))
    return comentarios


# --------------------------------------------------------------------------
# interpretação
# --------------------------------------------------------------------------
def normalizar(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(c for c in base if not unicodedata.combining(c))


def _palavras(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalizar(texto))


def aliases(nome: str) -> set[str]:
    """Formas que identificam o meme: nome inteiro e palavras marcantes."""
    palavras = _palavras(nome)
    saida = {" ".join(palavras)} if palavras else set()
    saida |= {p for p in palavras if len(p) >= 4 and p not in _PALAVRAS_VAZIAS}
    return saida


def extrair_escolha(texto: str, aliases_a: set[str] = frozenset(),
                    aliases_b: set[str] = frozenset()) -> str | None:
    """'A', 'B' ou None (sem voto claro / cita os dois)."""
    lados: set[str] = set()
    for emoji, lado in _EMOJI.items():
        if emoji in texto:
            lados.add(lado)

    palavras = _palavras(texto)
    limpo = " ".join(palavras)
    achado = _SOZINHO.match(limpo)
    if achado:
        lados.add("A" if achado.group(1) in "a1" else "B")
    for grupo in _FRASE.findall(limpo):
        lados.add("A" if grupo in "a1" else "B")

    if not lados:
        # nomes: alias exclusivo de um lado (palavras compartilhadas não decidem)
        so_a, so_b = aliases_a - aliases_b, aliases_b - aliases_a
        envolto = f" {limpo} "
        if any(f" {al} " in envolto for al in so_a):
            lados.add("A")
        if any(f" {al} " in envolto for al in so_b):
            lados.add("B")

    return lados.pop() if len(lados) == 1 else None


def hash_usuario(usuario: str) -> str:
    """Hash do autor (dedupe sem guardar o nome)."""
    return hashlib.sha256(normalizar(usuario).strip().encode("utf-8")).hexdigest()[:16]


def _no_prazo(criado_em: str | None, inicio: str | None, fim: str | None) -> bool:
    if not criado_em:
        return True
    try:
        t = datetime.fromisoformat(criado_em.replace("Z", "+00:00"))
        if inicio and t < datetime.fromisoformat(inicio.replace("Z", "+00:00")):
            return False
        if fim and t > datetime.fromisoformat(fim.replace("Z", "+00:00")):
            return False
    except ValueError:
        return True
    return True


def apurar(comentarios: list[Comentario], nome_a: str = "", nome_b: str = "",
           publicado_em: str | None = None, deadline: str | None = None,
           match_id: int | None = None) -> Apuracao:
    """Conta os votos (um por usuário, o primeiro válido)."""
    resultado = Apuracao()
    al_a, al_b = aliases(nome_a), aliases(nome_b)
    vistos: set[str] = set()
    ordenados = sorted(comentarios, key=lambda c: c.criado_em or "")
    for c in ordenados:
        escolha = extrair_escolha(c.texto, al_a, al_b)
        usuario = hash_usuario(c.usuario)
        valido = escolha is not None
        if valido and not _no_prazo(c.criado_em, publicado_em, deadline):
            resultado.fora_do_prazo += 1
            valido = False
        elif valido and usuario in vistos:
            resultado.duplicados += 1
            valido = False
        elif not valido:
            resultado.invalidos += 1

        if valido:
            vistos.add(usuario)
            resultado.validos += 1
            if escolha == "A":
                resultado.votos_a += 1
            else:
                resultado.votos_b += 1
        resultado.votos.append({
            "match_id": match_id,
            "user_hash": usuario,
            "raw_comment": c.texto,
            "escolha": escolha,
            "valido": valido,
            "criado_em": c.criado_em,
        })
    return resultado


def vencedor(apuracao: Apuracao, match: dict[str, Any], seed: Any) -> int | None:
    """Id do vencedor; empate decidido de forma reprodutível pelo seed."""
    if apuracao.total == 0:
        return None
    if apuracao.votos_a != apuracao.votos_b:
        return match["meme_a_id"] if apuracao.votos_a > apuracao.votos_b else match["meme_b_id"]
    rng = random.Random(f"{seed}-{match['id']}")
    return rng.choice([match["meme_a_id"], match["meme_b_id"]])


def apurar_match(estado: Estado, match: dict[str, Any], arquivo: Path) -> Apuracao:
    """Lê o arquivo, guarda o bruto, conta e grava votos/placar no estado.

    Idempotente: refazer a apuração substitui os votos anteriores do confronto.
    """
    comentarios = ler_comentarios(arquivo)
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    gravar_json_atomico(
        RAW_DATA_DIR / f"match_{match['id']}.json",
        {"arquivo": str(arquivo), "lido_em": agora(),
         "comentarios": [c.__dict__ for c in comentarios]},
    )

    meme_a = estado.buscar_meme(match["meme_a_id"]) or {}
    meme_b = estado.buscar_meme(match["meme_b_id"]) or {}
    resultado = apurar(
        comentarios,
        match.get("titulo_a") or meme_a.get("nome", ""),
        match.get("titulo_b") or meme_b.get("nome", ""),
        match.get("publicado_em"),
        match.get("deadline"),
        match["id"],
    )

    # estado.json é público (vai para o repositório/site): guarda só os votos
    # válidos, sem o texto do comentário — o bruto fica em data/raw (git-ignored)
    estado.votes[:] = [v for v in estado.votes if v.get("match_id") != match["id"]]
    for voto in resultado.votos:
        if voto["valido"]:
            estado.adicionar(estado.votes, {k: v for k, v in voto.items() if k != "raw_comment"})
    gravar_json_atomico(RAW_DATA_DIR / f"match_{match['id']}_apuracao.json", resultado.votos)
    match["votos_a"], match["votos_b"] = resultado.votos_a, resultado.votos_b
    match["apurado_em"] = agora()
    return resultado
