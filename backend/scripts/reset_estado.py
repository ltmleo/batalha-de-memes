"""Gera backend/data/estado.json a partir do catálogo (uso utilitário).

Roda sem depender de yt-dlp/ffmpeg: só store + catalog + bracket.

Estrutura gerada:
- Torneio 1 (Temporada 1): os 64 primeiros memes do catálogo numa chave cheia
  de 64 vagas (32 confrontos reais, sem byes).
- Torneio 2 (Temporada 2): os memes restantes aguardando o resto dos oponentes
  para completar a chave de 64 vagas.

Uso (na raiz do repositório):

    backend/.venv/scripts/python backend/scripts/reset_estado.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))

from app.services.bracket import criar_torneio_aguardando, gerar_torneio  # noqa: E402
from app.services.catalog import carregar_catalogo  # noqa: E402
from app.store import Estado  # noqa: E402

TAMANHO_CHAVE = 64


def main() -> None:
    estado = Estado()
    inseridos = carregar_catalogo(estado)
    ids = [m["id"] for m in estado.memes if m.get("status", "ativo") == "ativo"]

    ids_t1 = ids[:TAMANHO_CHAVE]
    ids_t2 = ids[TAMANHO_CHAVE:]

    t1 = gerar_torneio(estado, "Temporada 1", ids_t1, seed=42, temporada="1")
    t2 = criar_torneio_aguardando(
        estado, "Temporada 2", ids_t2, tamanho=TAMANHO_CHAVE, temporada="2"
    )

    caminho = estado.salvar()
    print(f"catálogo: {inseridos} inseridos | memes: {len(estado.memes)}")
    print(
        f"torneio {t1['id']} '{t1['nome']}': {len(ids_t1)} memes | "
        f"tamanho={t1['tamanho']} | confrontos={len(estado.matches_do_torneio(t1['id']))}"
    )
    print(
        f"torneio {t2['id']} '{t2['nome']}': {len(ids_t2)} memes aguardando | "
        f"tamanho={t2['tamanho']} | faltam {t2['tamanho'] - len(ids_t2)} oponentes"
    )
    print(f"salvo em {caminho}")


if __name__ == "__main__":
    main()