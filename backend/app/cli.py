"""CLI do pipeline da Batalha de Memes.

Manipula ``data/estado.json`` (fonte única da verdade) sem API nem banco::

    python -m app.cli seed
    python -m app.cli torneio --nome "Temporada 1" --temporada 1
    python -m app.cli mostrar --torneio 1
    python -m app.cli vencedor --match 1 --winner 2
    python -m app.cli video --match 1 --tiktok URL --instagram URL --youtube URL
    python -m app.cli montar --match 1
    python -m app.cli editor          # editor visual desktop
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from .services import assembler
from .services.bracket import criar_torneio_aguardando, definir_vencedor, gerar_torneio
from .services.catalog import carregar_catalogo
from .store import Estado


def _cmd_seed(args: argparse.Namespace) -> None:
    estado = Estado.carregar()
    inseridos = carregar_catalogo(estado)
    caminho = estado.salvar()
    print(f"{inseridos} meme(s) inserido(s) em {caminho}")


def _cmd_memes(args: argparse.Namespace) -> None:
    estado = Estado.carregar()
    for m in estado.memes:
        print(f'{m["id"]:>3}  {m["nome"]}')


def _cmd_torneio(args: argparse.Namespace) -> None:
    estado = Estado.carregar()
    if args.ids:
        ids = args.ids
    else:
        ids = [m["id"] for m in estado.memes if m.get("status", "ativo") == "ativo"]

    if args.aguardando:
        tamanho = args.tamanho
        if tamanho is None:
            tamanho = 2
            while tamanho < len(ids):
                tamanho *= 2
        torneio = criar_torneio_aguardando(estado, args.nome, ids, tamanho, str(args.temporada))
    else:
        seed = args.seed if args.seed is not None else random.randrange(1, 2**31)
        torneio = gerar_torneio(estado, args.nome, ids, seed, str(args.temporada))
    estado.salvar()
    print(json.dumps(torneio, ensure_ascii=False))


def _cmd_torneios(args: argparse.Namespace) -> None:
    estado = Estado.carregar()
    for t in estado.tournaments:
        print(f'{t["id"]:>3}  {t["nome"]}  (temp. {t["temporada"]}, {t["tamanho"]} memes)')


def _cmd_mostrar(args: argparse.Namespace) -> None:
    estado = Estado.carregar()
    torneio = estado.buscar_torneio(args.torneio)
    if torneio is None:
        raise SystemExit(f"torneio {args.torneio} não encontrado")

    nomes = {m["id"]: m["nome"] for m in estado.memes}
    print(f'{torneio["nome"]} (seed {torneio["seed"]})')
    for match in estado.matches_do_torneio(torneio["id"]):
        a = nomes.get(match["meme_a_id"], "-")
        b = nomes.get(match["meme_b_id"], "-")
        vencedor = nomes.get(match["winner_id"]) or ""
        placar = f'{match["votos_a"]}-{match["votos_b"]}'
        print(
            f'  id {match["id"]:>3}  R{match["round"]}P{match["posicao"]}  '
            f'{a} {placar} {b}  [{match["status"]}] {vencedor}'
        )


def _cmd_vencedor(args: argparse.Namespace) -> None:
    estado = Estado.carregar()
    match = estado.buscar_match(args.match)
    if match is None:
        raise SystemExit(f"confronto {args.match} não encontrado")
    if args.winner not in (match["meme_a_id"], match["meme_b_id"]):
        raise SystemExit("winner_id não pertence ao confronto")
    definir_vencedor(estado, match, args.winner)
    estado.salvar()
    print(f'confronto {match["id"]}: vencedor = {args.winner}')


def _cmd_montar(args: argparse.Namespace) -> None:
    estado = Estado.carregar()
    match = estado.buscar_match(args.match)
    if match is None:
        raise SystemExit(f"confronto {args.match} não encontrado")
    if not match["meme_a_id"] or not match["meme_b_id"]:
        raise SystemExit("confronto incompleto")

    destino = Path(args.saida) if args.saida else None
    saida = assembler.montar_match(estado, match, destino=destino)
    estado.salvar()
    print(saida)


def _cmd_editor(args: argparse.Namespace) -> None:
    from .editor.app import executar

    executar()


def _cmd_video(args: argparse.Namespace) -> None:
    estado = Estado.carregar()
    match = estado.buscar_match(args.match)
    if match is None:
        raise SystemExit(f"confronto {args.match} não encontrado")

    campos = {
        "tiktok_url": args.tiktok,
        "instagram_url": args.instagram,
        "youtube_url": args.youtube,
    }
    if not args.limpar and all(v is None for v in campos.values()):
        raise SystemExit(
            "informe ao menos um link (--tiktok / --instagram / --youtube) ou use --limpar"
        )

    for campo, valor in campos.items():
        if args.limpar:
            match[campo] = None
        elif valor is not None:
            match[campo] = valor

    estado.salvar()
    print(
        json.dumps(
            {"id": match["id"], **{campo: match.get(campo) for campo in campos}},
            ensure_ascii=False,
        )
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="app.cli", description="Pipeline da Batalha de Memes (estado em data/estado.json)"
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("seed", help="carrega data/memes.json no estado")
    p.set_defaults(func=_cmd_seed)

    p = sub.add_parser("memes", help="lista os memes")
    p.set_defaults(func=_cmd_memes)

    p = sub.add_parser("torneio", help="cria uma temporada e sorteia as chaves")
    p.add_argument("--nome", required=True)
    p.add_argument("--temporada", default="1")
    p.add_argument("--seed", type=int, default=None, help="sorteio reprodutível")
    p.add_argument("--ids", type=int, nargs="*", default=None, help="ids explícitos de memes")
    p.add_argument(
        "--aguardando",
        action="store_true",
        help="torneio incompleto: reserva os memes e espera o resto dos oponentes",
    )
    p.add_argument(
        "--tamanho",
        type=int,
        default=None,
        help="vagas da chave (padrão: próxima potência de 2 do nº de memes)",
    )
    p.set_defaults(func=_cmd_torneio)

    p = sub.add_parser("torneios", help="lista as temporadas")
    p.set_defaults(func=_cmd_torneios)

    p = sub.add_parser("mostrar", help="mostra o chaveamento de uma temporada")
    p.add_argument("--torneio", type=int, required=True)
    p.set_defaults(func=_cmd_mostrar)

    p = sub.add_parser("vencedor", help="define o vencedor e propaga na chave")
    p.add_argument("--match", type=int, required=True)
    p.add_argument("--winner", type=int, required=True)
    p.set_defaults(func=_cmd_vencedor)

    p = sub.add_parser("montar", help="baixa, normaliza e monta o vídeo do confronto")
    p.add_argument("--match", type=int, required=True)
    p.add_argument("--saida", type=str, default=None)
    p.set_defaults(func=_cmd_montar)

    p = sub.add_parser(
        "editor",
        help="abre o editor visual desktop (área do vídeo, título, preenchimento)",
    )
    p.set_defaults(func=_cmd_editor)

    p = sub.add_parser("video", help="define os links de vídeo (TikTok/Instagram/YouTube) de um confronto")
    p.add_argument("--match", type=int, required=True)
    p.add_argument("--tiktok", type=str, default=None, help="URL do vídeo no TikTok")
    p.add_argument("--instagram", type=str, default=None, help="URL do Reels no Instagram")
    p.add_argument("--youtube", type=str, default=None, help="URL do YouTube Shorts")
    p.add_argument("--limpar", action="store_true", help="remove todos os links do confronto")
    p.set_defaults(func=_cmd_video)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
