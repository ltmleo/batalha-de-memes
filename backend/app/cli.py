"""CLI do pipeline da Batalha de Memes.

Manipula ``data/estado.json`` (fonte única da verdade) sem API nem banco::

    python -m app.cli seed
    python -m app.cli torneio --nome "Temporada 1" --temporada 1
    python -m app.cli mostrar --torneio 1
    python -m app.cli vencedor --match 1 --winner 2
    python -m app.cli video --match 1 --tiktok URL --instagram URL --youtube URL
    python -m app.cli montar --match 1
    python -m app.cli editor          # editor visual desktop
    python -m app.cli painel          # painel de duelos (rodada inteira)

    python -m app.cli rodada --torneio 1          # monta a rodada + pacote de publicação
    python -m app.cli publicar --match 1 --tiktok URL [--horas 48]
    python -m app.cli apurar --match 1 --arquivo comentarios.txt [--definir-vencedor]
    python -m app.cli status                      # o que falta em cada temporada
    python -m app.cli doctor | validar | prebaixar
"""

from __future__ import annotations

if __name__ == "__main__":
    # antes das dependências: chamado pelo Python global, relança no .venv
    from ._venv import garantir_venv

    garantir_venv()

import argparse  # noqa: E402
import json
import logging
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .services import assembler
from .services.bracket import (
    criar_torneio_aguardando,
    definir_vencedor,
    gerar_torneio,
    jogavel,
    rodada_atual,
)
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

    executar(args.match)


def _cmd_painel(args: argparse.Namespace) -> None:
    from .editor.painel import executar

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


def _cmd_rodada(args: argparse.Namespace) -> None:
    from .services.publicacao import empacotar

    estado = Estado.carregar()
    if estado.buscar_torneio(args.torneio) is None:
        raise SystemExit(f"torneio {args.torneio} não encontrado")
    rodada = args.round or rodada_atual(estado, args.torneio)
    if rodada is None:
        raise SystemExit("nenhum confronto jogável (torneio terminado ou aguardando vencedores)")

    matches = [
        m for m in estado.matches_do_torneio(args.torneio)
        if m["round"] == rodada and jogavel(m)
    ]
    falhas = []
    for i, match in enumerate(matches, 1):
        pronto = match["status"] in ("pronto", "publicado") and match.get("video_path")
        if pronto and not args.refazer:
            print(f"[{i}/{len(matches)}] confronto {match['id']}: já montado")
            continue
        print(f"[{i}/{len(matches)}] montando confronto {match['id']}...", flush=True)
        try:
            saida = assembler.montar_match(estado, match, forcar=args.forcar)
        except Exception as exc:  # noqa: BLE001 — segue a rodada, reporta no fim
            falhas.append((match["id"], str(exc).splitlines()[0]))
            print(f"    falhou: {falhas[-1][1]}")
            continue
        estado.salvar()  # salva a cada vídeo: um erro adiante não perde o anterior
        print(f"    {saida} ({match.get('duracao')}s)")

    pasta = empacotar(estado, matches, args.torneio, rodada)
    print(f"pacote de publicação: {pasta}")
    if falhas:
        print("falhas:", *(f"  confronto {i}: {e}" for i, e in falhas), sep="\n")
        sys.exit(1)


def _cmd_publicar(args: argparse.Namespace) -> None:
    estado = Estado.carregar()
    match = estado.buscar_match(args.match)
    if match is None:
        raise SystemExit(f"confronto {args.match} não encontrado")
    for campo, valor in (("tiktok_url", args.tiktok), ("instagram_url", args.instagram),
                         ("youtube_url", args.youtube)):
        if valor:
            match[campo] = valor
    inicio = datetime.now(timezone.utc).replace(microsecond=0)
    match["publicado_em"] = inicio.isoformat().replace("+00:00", "Z")
    match["deadline"] = (inicio + timedelta(hours=args.horas)).isoformat().replace("+00:00", "Z")
    match["status"] = "publicado"
    estado.salvar()
    print(f"confronto {match['id']} publicado; votação até {match['deadline']}")


def _cmd_apurar(args: argparse.Namespace) -> None:
    from .services import vote_parser

    estado = Estado.carregar()
    match = estado.buscar_match(args.match)
    if match is None:
        raise SystemExit(f"confronto {args.match} não encontrado")
    res = vote_parser.apurar_match(estado, match, Path(args.arquivo))
    print(
        f"A {res.votos_a} x {res.votos_b} B  (válidos {res.validos}, sem voto {res.invalidos}, "
        f"repetidos {res.duplicados}, fora do prazo {res.fora_do_prazo})"
    )
    if args.definir_vencedor:
        torneio = estado.buscar_torneio(match["tournament_id"]) or {}
        vencedor = vote_parser.vencedor(res, match, torneio.get("seed"))
        if vencedor is None:
            print("nenhum voto válido: vencedor não definido")
        else:
            if res.votos_a == res.votos_b:
                print("empate: desempate pelo seed do torneio")
            definir_vencedor(estado, match, vencedor)
            nome = (estado.buscar_meme(vencedor) or {}).get("nome", vencedor)
            print(f"vencedor: {nome}")
    estado.salvar()


def _cmd_status(args: argparse.Namespace) -> None:
    estado = Estado.carregar()
    agora_dt = datetime.now(timezone.utc)
    nomes = {m["id"]: m["nome"] for m in estado.memes}
    for torneio in estado.tournaments:
        if torneio["status"] != "em_andamento":
            print(f'{torneio["nome"]}: {torneio["status"]}')
            continue
        rodada = rodada_atual(estado, torneio["id"])
        print(f'{torneio["nome"]} — rodada {rodada}')
        for m in estado.matches_do_torneio(torneio["id"]):
            if m["round"] != rodada or not jogavel(m):
                continue
            titulo = f'{nomes.get(m["meme_a_id"])} vs {nomes.get(m["meme_b_id"])}'
            if m["status"] == "pendente":
                acao = f"montar      → app.cli montar --match {m['id']}"
            elif m["status"] == "pronto":
                acao = f"publicar    → app.cli publicar --match {m['id']} --tiktok URL"
            elif m["status"] == "publicado":
                prazo = m.get("deadline")
                fim = datetime.fromisoformat(prazo.replace("Z", "+00:00")) if prazo else None
                if fim is None or fim <= agora_dt:
                    acao = f"apurar      → app.cli apurar --match {m['id']} --arquivo ... --definir-vencedor"
                else:
                    acao = f"votação até {fim.astimezone():%d/%m %H:%M}"
            else:
                acao = m["status"]
            print(f'  {m["id"]:>3}  {titulo:<45} {acao}')


def _cmd_doctor(args: argparse.Namespace) -> None:
    from .config import (
        ABERTURA_PATH,
        CAMINHO_ESTADO,
        ENCERRAMENTO_PATH,
        FONTE_TITULO_PATH,
        MOLDURA_PATH,
        VERSUS_PATH,
    )
    from .services.downloader import verificar_dependencias
    from .services.validacao import validar_catalogo, validar_estado

    problemas = 0

    def linha(ok: bool | None, texto: str) -> None:
        nonlocal problemas
        marca = {True: "ok ", False: "ERRO", None: "aviso"}[ok]
        problemas += ok is False
        print(f"[{marca:>5}] {texto}")

    linha(sys.version_info >= (3, 11), f"Python {sys.version.split()[0]} (3.11+)")
    deps = verificar_dependencias()
    linha(deps["ffmpeg"] is not None, f"ffmpeg: {deps['ffmpeg'] or 'não encontrado'}")
    versao = deps["yt_dlp"]
    if versao is None:
        linha(False, "yt-dlp não instalado (pip install -r requirements.txt)")
    else:
        try:
            idade = (datetime.now() - datetime.strptime(versao[:10], "%Y.%m.%d")).days
        except ValueError:
            idade = 0
        linha(True if idade < 60 else None,
              f"yt-dlp {versao}" + (f" — {idade} dias; rode: pip install -U yt-dlp" if idade >= 60 else ""))
    for caminho, obrigatorio in ((FONTE_TITULO_PATH, True), (MOLDURA_PATH, True),
                                 (VERSUS_PATH, False), (ENCERRAMENTO_PATH, False),
                                 (ABERTURA_PATH, False)):
        linha(True if caminho.exists() else (False if obrigatorio else None),
              f"{caminho.name}: {'ok' if caminho.exists() else 'ausente'}")
    try:
        estado = Estado.carregar()
        rel = validar_estado(estado)
        linha(rel.ok, f"{CAMINHO_ESTADO.name}: {len(estado.memes)} memes, "
                      f"{len(estado.matches)} confrontos" + ("" if rel.ok else f" — {rel.erros[0]}"))
    except json.JSONDecodeError as exc:
        linha(False, f"{CAMINHO_ESTADO.name} inválido: {exc}")
    cat = validar_catalogo()
    linha(cat.ok and (None if cat.avisos else True),
          f"catálogo: {len(cat.erros)} erro(s), {len(cat.avisos)} aviso(s) (detalhes: app.cli validar)")
    if problemas:
        sys.exit(1)


def _cmd_validar(args: argparse.Namespace) -> None:
    from .services.validacao import validar_catalogo, validar_estado

    rels = [("catálogo", validar_catalogo()), ("estado", validar_estado(Estado.carregar()))]
    for nome, rel in rels:
        for e in rel.erros:
            print(f"ERRO  [{nome}] {e}")
        if not args.so_erros:
            for a in rel.avisos:
                print(f"aviso [{nome}] {a}")
    erros = sum(len(r.erros) for _, r in rels)
    print(f"{erros} erro(s), {sum(len(r.avisos) for _, r in rels)} aviso(s)")
    if erros:
        sys.exit(1)


def _cmd_prebaixar(args: argparse.Namespace) -> None:
    from .services.downloader import preparar_clip

    estado = Estado.carregar()
    memes = [m for m in estado.memes if m.get("status", "ativo") == "ativo"]
    if args.ids:
        memes = [m for m in memes if m["id"] in args.ids]
    falhas = []
    for i, meme in enumerate(memes, 1):
        try:
            preparar_clip(meme)
            print(f"[{i}/{len(memes)}] ok    {meme['nome']}")
        except Exception as exc:  # noqa: BLE001 — continua e lista no fim
            falhas.append(meme)
            print(f"[{i}/{len(memes)}] FALHA {meme['nome']}: {str(exc).splitlines()[0][:120]}")
    print(f"{len(memes) - len(falhas)} ok, {len(falhas)} falha(s)")
    if falhas:
        sys.exit(1)


def _cmd_legenda(args: argparse.Namespace) -> None:
    from .services.publicacao import legenda

    estado = Estado.carregar()
    match = estado.buscar_match(args.match)
    if match is None:
        raise SystemExit(f"confronto {args.match} não encontrado")
    print(legenda(estado, match, args.horas))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="app.cli", description="Pipeline da Batalha de Memes (estado em data/estado.json)"
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("seed", help="carrega data/memes/*.json no estado")
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
    p.add_argument("--match", type=int, default=None, help="abre já neste confronto")
    p.set_defaults(func=_cmd_editor)

    p = sub.add_parser(
        "painel",
        help="abre o painel de duelos (gerar vídeos, publicar, apurar a rodada)",
    )
    p.set_defaults(func=_cmd_painel)

    p = sub.add_parser("video", help="define os links de vídeo (TikTok/Instagram/YouTube) de um confronto")
    p.add_argument("--match", type=int, required=True)
    p.add_argument("--tiktok", type=str, default=None, help="URL do vídeo no TikTok")
    p.add_argument("--instagram", type=str, default=None, help="URL do Reels no Instagram")
    p.add_argument("--youtube", type=str, default=None, help="URL do YouTube Shorts")
    p.add_argument("--limpar", action="store_true", help="remove todos os links do confronto")
    p.set_defaults(func=_cmd_video)

    p = sub.add_parser("rodada", help="monta todos os confrontos da rodada + pacote de publicação")
    p.add_argument("--torneio", type=int, required=True)
    p.add_argument("--round", type=int, default=None, help="padrão: a rodada em andamento")
    p.add_argument("--refazer", action="store_true", help="remonta mesmo os já prontos")
    p.add_argument("--forcar", action="store_true", help="ignora o cache de download")
    p.set_defaults(func=_cmd_rodada)

    p = sub.add_parser("publicar", help="marca como publicado, grava links e abre a votação")
    p.add_argument("--match", type=int, required=True)
    p.add_argument("--tiktok", type=str, default=None)
    p.add_argument("--instagram", type=str, default=None)
    p.add_argument("--youtube", type=str, default=None)
    p.add_argument("--horas", type=int, default=48, help="duração da votação (padrão 48h)")
    p.set_defaults(func=_cmd_publicar)

    p = sub.add_parser("apurar", help="conta os votos a partir de um arquivo de comentários")
    p.add_argument("--match", type=int, required=True)
    p.add_argument("--arquivo", type=str, required=True, help=".txt (usuario: texto), .csv ou .json")
    p.add_argument("--definir-vencedor", action="store_true",
                   help="define o vencedor e propaga na chave")
    p.set_defaults(func=_cmd_apurar)

    p = sub.add_parser("status", help="próxima ação de cada confronto da rodada atual")
    p.set_defaults(func=_cmd_status)

    p = sub.add_parser("doctor", help="checa ambiente, assets e dados")
    p.set_defaults(func=_cmd_doctor)

    p = sub.add_parser("validar", help="valida catálogo e estado (sai com 1 se houver erro)")
    p.add_argument("--so-erros", action="store_true")
    p.set_defaults(func=_cmd_validar)

    p = sub.add_parser("prebaixar", help="baixa/normaliza os clipes de todos os memes ativos")
    p.add_argument("--ids", type=int, nargs="*", default=None)
    p.set_defaults(func=_cmd_prebaixar)

    p = sub.add_parser("legenda", help="imprime a legenda pronta de um confronto")
    p.add_argument("--match", type=int, required=True)
    p.add_argument("--horas", type=int, default=48)
    p.set_defaults(func=_cmd_legenda)

    args = parser.parse_args(argv)
    # console do Windows (cp1252) não imprime emoji/setas da legenda e do status
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    args.func(args)


if __name__ == "__main__":
    main()
