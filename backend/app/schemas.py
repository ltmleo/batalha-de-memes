from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MemeBase(BaseModel):
    nome: str
    youtube_url: str
    inicio: float = 0.0
    fim: float = 15.0
    autor_fonte: str = ""
    tags: list[str] = []
    status: str = "ativo"


class MemeCreate(MemeBase):
    pass


class MemeOut(MemeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TournamentCreate(BaseModel):
    nome: str
    temporada: str = "1"
    seed: Optional[int] = None
    meme_ids: Optional[list[int]] = None


class TournamentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    temporada: str
    seed: int
    tamanho: int
    status: str
    criado_em: datetime


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tournament_id: int
    round: int
    posicao: int
    meme_a_id: Optional[int]
    meme_b_id: Optional[int]
    winner_id: Optional[int]
    video_path: Optional[str]
    tiktok_url: Optional[str]
    status: str
    votos_a: int
    votos_b: int


class TournamentDetail(TournamentOut):
    memes: list[MemeOut] = []
    matches: list[MatchOut] = []


class DefinirVencedor(BaseModel):
    winner_id: int
