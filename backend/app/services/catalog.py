import json

from ..config import CAMINHO_CATALOGO
from ..store import Estado


def carregar_catalogo(estado: Estado) -> int:
    """Sincroniza ``data/memes.json`` com o estado (insere novos, atualiza por nome).

    Devolve quantos memes foram inseridos.
    """
    if not CAMINHO_CATALOGO.exists():
        return 0

    dados = json.loads(CAMINHO_CATALOGO.read_text(encoding="utf-8"))
    inseridos = 0
    for item in dados.get("memes", []):
        campos = {
            "youtube_url": item["youtube_url"],
            "inicio": float(item.get("inicio", 0.0)),
            "fim": float(item.get("fim", 15.0)),
            "autor_fonte": item.get("autor_fonte", ""),
            "tags": item.get("tags", []),
            # metadados exibidos no site (card/história do meme)
            "ano": item.get("ano"),
            "origem": item.get("origem", ""),
            "historia": item.get("historia", ""),
            "confianca": item.get("confianca", "media"),
        }
        existente = next((m for m in estado.memes if m["nome"] == item["nome"]), None)
        if existente:
            existente.update(campos)
            continue
        estado.adicionar(estado.memes, {"nome": item["nome"], "status": "ativo", **campos})
        inseridos += 1
    return inseridos
