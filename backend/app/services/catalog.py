import json

from sqlalchemy.orm import Session

from .. import models
from ..config import CAMINHO_CATALOGO


def carregar_catalogo(db: Session) -> int:
    """Sincroniza data/memes.json com o banco (insere novos, atualiza existentes por nome)."""
    if not CAMINHO_CATALOGO.exists():
        return 0

    dados = json.loads(CAMINHO_CATALOGO.read_text(encoding="utf-8"))
    inseridos = 0
    for item in dados.get("memes", []):
        existente = db.query(models.Meme).filter_by(nome=item["nome"]).first()
        if existente:
            existente.youtube_url = item["youtube_url"]
            existente.inicio = float(item.get("inicio", 0.0))
            existente.fim = float(item.get("fim", 15.0))
            existente.autor_fonte = item.get("autor_fonte", "")
            existente.tags = item.get("tags", [])
            continue
        db.add(
            models.Meme(
                nome=item["nome"],
                youtube_url=item["youtube_url"],
                inicio=float(item.get("inicio", 0.0)),
                fim=float(item.get("fim", 15.0)),
                autor_fonte=item.get("autor_fonte", ""),
                tags=item.get("tags", []),
            )
        )
        inseridos += 1
    db.commit()
    return inseridos
