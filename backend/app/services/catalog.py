import json

from ..config import CATALOGO_DIR
from ..store import Estado


def carregar_catalogo(estado: Estado) -> int:
    """Sincroniza os catálogos de ``data/memes/*.json`` com o estado.

    Cada arquivo descreve uma temporada (campo ``temporada``), gravado em cada
    meme. Os arquivos são lidos em ordem de temporada. Insere memes novos e
    atualiza os existentes por nome.

    Devolve quantos memes foram inseridos.
    """
    if not CATALOGO_DIR.exists():
        return 0

    arquivos: list[tuple[object, str, dict]] = []
    for caminho in CATALOGO_DIR.glob("*.json"):
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        arquivos.append((dados.get("temporada"), caminho.name, dados))
    arquivos.sort(key=lambda item: (item[0] if isinstance(item[0], int) else 1 << 30, item[1]))

    inseridos = 0
    for temporada, _, dados in arquivos:
        for item in dados.get("memes", []):
            campos = {
                "youtube_url": item["youtube_url"],
                "inicio": float(item.get("inicio", 0.0)),
                "fim": float(item.get("fim", 15.0)),
                "autor_fonte": item.get("autor_fonte", ""),
                "tags": item.get("tags", []),
                "temporada": temporada,
                # metadados exibidos no site (card/história do meme)
                "ano": item.get("ano"),
                "origem": item.get("origem", ""),
                "historia": item.get("historia", ""),
            }
            existente = next((m for m in estado.memes if m["nome"] == item["nome"]), None)
            if existente:
                existente.update(campos)
                continue
            estado.adicionar(estado.memes, {"nome": item["nome"], "status": "ativo", **campos})
            inseridos += 1
    return inseridos
