"""Gera backend/data/estado.json a partir do catálogo (uso utilitário).

Roda sem depender de yt-dlp/ffmpeg: só store + catalog + bracket.

Estrutura gerada:
- Temporada 1: os 32 primeiros memes do catálogo numa chave cheia de 32 vagas
  (16, 8, 4, 2).
- Temporada 2: os 32 memes seguintes, **aguardando** — aparecem no site com os
  participantes, mas ainda sem chave definida.
- Temporada 3: os memes restantes, também aguardando completar a chave de 32.

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

TAMANHO_CHAVE = 32
SEED = 42


def main() -> None:
    estado = Estado()
    inseridos = carregar_catalogo(estado)
    ids = [m["id"] for m in estado.memes if m.get("status", "ativo") == "ativo"]

    ids_t1 = ids[:TAMANHO_CHAVE]
    ids_t2 = ids[TAMANHO_CHAVE : TAMANHO_CHAVE * 2]
    ids_t3 = ids[TAMANHO_CHAVE * 2 :]

    t1 = gerar_torneio(estado, "Temporada 1", ids_t1, seed=SEED, temporada="1")
    t2 = criar_torneio_aguardando(
        estado, "Temporada 2", ids_t2, tamanho=TAMANHO_CHAVE, temporada="2"
    )
    t3 = criar_torneio_aguardando(
        estado, "Temporada 3", ids_t3, tamanho=TAMANHO_CHAVE, temporada="3"
    )

    caminho = estado.salvar()
    print(f"catálogo: {inseridos} inseridos | memes: {len(estado.memes)}")
    print(
        f"torneio {t1['id']} '{t1['nome']}': {len(ids_t1)} memes | "
        f"tamanho={t1['tamanho']} | confrontos={len(estado.matches_do_torneio(t1['id']))}"
    )
    for t in (t2, t3):
        n = len(t.get("participantes", []))
        print(
            f"torneio {t['id']} '{t['nome']}': {n} memes aguardando | "
            f"tamanho={t['tamanho']} | faltam {t['tamanho'] - n} oponentes"
        )
    print(f"salvo em {caminho}")


if __name__ == "__main__":
    main()
