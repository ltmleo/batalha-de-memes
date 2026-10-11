from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..services.catalog import carregar_catalogo

router = APIRouter(prefix="/memes", tags=["memes"])


@router.get("", response_model=list[schemas.MemeOut])
def listar(db: Session = Depends(get_db)):
    return db.query(models.Meme).order_by(models.Meme.nome).all()


@router.post("/seed")
def seed(db: Session = Depends(get_db)):
    """Carrega backend/data/memes.json para o banco."""
    return {"inseridos": carregar_catalogo(db)}


@router.post("", response_model=schemas.MemeOut)
def criar(payload: schemas.MemeCreate, db: Session = Depends(get_db)):
    meme = models.Meme(**payload.model_dump())
    db.add(meme)
    db.commit()
    db.refresh(meme)
    return meme
