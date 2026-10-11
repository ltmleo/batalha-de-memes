from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Meme(Base):
    __tablename__ = "memes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    youtube_url: Mapped[str] = mapped_column(String(300))
    inicio: Mapped[float] = mapped_column(Float, default=0.0)
    fim: Mapped[float] = mapped_column(Float, default=15.0)
    autor_fonte: Mapped[str] = mapped_column(String(200), default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="ativo")


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    temporada: Mapped[str] = mapped_column(String(40), default="1")
    seed: Mapped[int] = mapped_column(Integer, default=0)
    tamanho: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="em_andamento")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    round: Mapped[int] = mapped_column(Integer)
    posicao: Mapped[int] = mapped_column(Integer)

    meme_a_id: Mapped[Optional[int]] = mapped_column(ForeignKey("memes.id"), nullable=True)
    meme_b_id: Mapped[Optional[int]] = mapped_column(ForeignKey("memes.id"), nullable=True)
    winner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("memes.id"), nullable=True)

    video_path: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    tiktok_url: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    publicado_em: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="pendente")
    votos_a: Mapped[int] = mapped_column(Integer, default=0)
    votos_b: Mapped[int] = mapped_column(Integer, default=0)


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    user_hash: Mapped[str] = mapped_column(String(64))
    raw_comment: Mapped[str] = mapped_column(String(1000), default="")
    escolha: Mapped[str] = mapped_column(String(1))
    valido: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
