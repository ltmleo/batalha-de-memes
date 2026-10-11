from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import ABERTURA_PATH, CLIPS_DIR, ENCERRAMENTO_PATH
from ..db import get_db
from ..services import assembler, downloader
from ..services.bracket import definir_vencedor

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[schemas.MatchOut])
def listar(tournament_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Match)
    if tournament_id is not None:
        q = q.filter_by(tournament_id=tournament_id)
    return q.order_by(models.Match.round, models.Match.posicao).all()


@router.get("/{mid}", response_model=schemas.MatchOut)
def obter(mid: int, db: Session = Depends(get_db)):
    match = db.get(models.Match, mid)
    if match is None:
        raise HTTPException(status_code=404, detail="Confronto não encontrado")
    return match


@router.post("/{mid}/vencedor", response_model=schemas.MatchOut)
def vencedor(mid: int, payload: schemas.DefinirVencedor, db: Session = Depends(get_db)):
    match = db.get(models.Match, mid)
    if match is None:
        raise HTTPException(status_code=404, detail="Confronto não encontrado")
    if payload.winner_id not in (match.meme_a_id, match.meme_b_id):
        raise HTTPException(status_code=400, detail="winner_id não pertence ao confronto")
    definir_vencedor(db, match, payload.winner_id)
    db.commit()
    db.refresh(match)
    return match


@router.post("/{mid}/montar")
def montar(mid: int, db: Session = Depends(get_db)):
    """Baixa os dois trechos, normaliza e monta o vídeo do confronto."""
    match = db.get(models.Match, mid)
    if match is None:
        raise HTTPException(status_code=404, detail="Confronto não encontrado")
    if not match.meme_a_id or not match.meme_b_id:
        raise HTTPException(status_code=400, detail="Confronto incompleto")

    meme_a = db.get(models.Meme, match.meme_a_id)
    meme_b = db.get(models.Meme, match.meme_b_id)

    clip_a = downloader.preparar_clip(meme_a)
    clip_b = downloader.preparar_clip(meme_b)
    destino = assembler.montar_video(
        clip_a,
        clip_b,
        texto_a=meme_a.nome,
        texto_b=meme_b.nome,
        abertura=ABERTURA_PATH,
        encerramento=ENCERRAMENTO_PATH,
        destino=CLIPS_DIR / f"match_{match.id}.mp4",
    )

    match.video_path = str(destino)
    match.status = "pronto"
    db.commit()
    return {"match_id": match.id, "video_path": match.video_path}
