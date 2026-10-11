import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..services.bracket import gerar_torneio

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


def _detalhe(db: Session, torneio: models.Tournament) -> schemas.TournamentDetail:
    memes = db.query(models.Meme).all()
    matches = (
        db.query(models.Match)
        .filter_by(tournament_id=torneio.id)
        .order_by(models.Match.round, models.Match.posicao)
        .all()
    )
    base = schemas.TournamentOut.model_validate(torneio).model_dump()
    return schemas.TournamentDetail(**base, memes=memes, matches=matches)


@router.get("", response_model=list[schemas.TournamentOut])
def listar(db: Session = Depends(get_db)):
    return db.query(models.Tournament).order_by(models.Tournament.id.desc()).all()


@router.post("", response_model=schemas.TournamentDetail)
def criar(payload: schemas.TournamentCreate, db: Session = Depends(get_db)):
    if payload.meme_ids:
        ids = payload.meme_ids
    else:
        ids = [m.id for m in db.query(models.Meme).filter_by(status="ativo").all()]

    seed = payload.seed if payload.seed is not None else random.randrange(1, 2**31)
    try:
        torneio = gerar_torneio(db, payload.nome, ids, seed, payload.temporada)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _detalhe(db, torneio)


@router.get("/{tid}", response_model=schemas.TournamentDetail)
def obter(tid: int, db: Session = Depends(get_db)):
    torneio = db.get(models.Tournament, tid)
    if torneio is None:
        raise HTTPException(status_code=404, detail="Torneio não encontrado")
    return _detalhe(db, torneio)
