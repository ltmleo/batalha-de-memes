"""Painel de duelos (Tkinter) — o ciclo da rodada numa tela só.

Lista os confrontos de um torneio/rodada com o que falta em cada um e executa:

- **Gerar vídeo** dos selecionados ou da rodada inteira (fila em segundo
  plano, barra de progresso e log; cancela entre um vídeo e outro);
- **Prévia da capa** (gera só o kit — gancho/capa — sem renderizar o vídeo);
- **Ajustar no editor** (abre o editor de montagem já no confronto);
- **Publicar** (links + prazo da votação; a legenda vai para a área de transferência);
- **Apurar** um arquivo de comentários e **definir o vencedor** (ou na mão);
- **Pacote da rodada** (vídeos, capas, legendas e manifest numa pasta).

Abre com ``python -m app.cli painel``.
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from PIL import Image, ImageTk

from ..config import BASE_DIR
from ..layout import carregar_layout
from ..roteiro import carregar_roteiro
from ..services import assembler, kit
from ..services.bracket import definir_vencedor, jogavel, rodada_atual
from ..services.downloader import preparar_clip
from ..services.publicacao import absoluto, empacotar, legenda
from ..store import Estado

CAPA_L, CAPA_A = 180, 320
TODAS = "todas"

# rótulo de status -> (texto na lista, tag de cor)
_STATUS = {
    "pendente": ("a gerar", "pendente"),
    "pronto": ("pronto p/ publicar", "pronto"),
    "publicado": ("em votação", "publicado"),
    "finalizado": ("finalizado", "finalizado"),
    "cancelado": ("cancelado", "cancelado"),
}
_CORES = {
    "pendente": "#555555",
    "pronto": "#1f6fd1",
    "publicado": "#c27100",
    "apurar": "#c0392b",
    "finalizado": "#1e8e5a",
    "cancelado": "#999999",
    "aguardando": "#999999",
}


def _abrir(caminho: Path) -> None:
    """Abre arquivo/pasta no programa padrão do sistema."""
    if sys.platform.startswith("win"):
        os.startfile(caminho)  # noqa: S606 — caminho local gerado pelo próprio pipeline
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(caminho)])
    else:
        subprocess.Popen(["xdg-open", str(caminho)])


def _prazo(match: dict[str, Any]) -> datetime | None:
    texto = match.get("deadline")
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None


class Painel(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Batalha de Memes — painel de duelos")
        self.minsize(1100, 640)

        self.estado = Estado.carregar()
        self.roteiro = carregar_roteiro()
        self._ocupado = False
        self._cancelar = False
        self._capa_tk: ImageTk.PhotoImage | None = None
        self._var_torneio = tk.StringVar()
        self._var_rodada = tk.StringVar()

        # threads de trabalho não tocam no Tk: enfileiram chamadas que a thread
        # da interface executa a cada 80 ms
        self._fila_ui: queue.Queue[tuple[Callable[..., None], tuple]] = queue.Queue()
        self._montar_ui()
        self._carregar_torneios()
        self._drenar_fila_ui()
        self.bind("<F5>", lambda _e: self._recarregar())
        self.protocol("WM_DELETE_WINDOW", self._fechar)

    # ------------------------------------------------------------------ UI
    def _montar_ui(self) -> None:
        # pack (não grid): rodapé e coluna de ações reservam espaço primeiro e a
        # lista fica com o que sobrar — nada some quando a janela é pequena
        topo = ttk.Frame(self, padding=(8, 8, 8, 0))
        topo.pack(side="top", fill="x")
        ttk.Label(topo, text="Torneio").pack(side="left")
        self.combo_torneio = ttk.Combobox(topo, textvariable=self._var_torneio, state="readonly",
                                          width=34)
        self.combo_torneio.pack(side="left", padx=(4, 12))
        self.combo_torneio.bind("<<ComboboxSelected>>", lambda _e: self._torneio_mudou())
        ttk.Label(topo, text="Rodada").pack(side="left")
        self.combo_rodada = ttk.Combobox(topo, textvariable=self._var_rodada, state="readonly",
                                         width=26)
        self.combo_rodada.pack(side="left", padx=(4, 12))
        self.combo_rodada.bind("<<ComboboxSelected>>", lambda _e: self._preencher_lista())
        ttk.Button(topo, text="Recarregar (F5)", command=self._recarregar).pack(side="left")
        self.lbl_resumo = ttk.Label(topo, foreground="#555")
        self.lbl_resumo.pack(side="right")

        baixo = ttk.Frame(self, padding=(8, 0, 8, 8))
        baixo.pack(side="bottom", fill="x")
        self.progresso = ttk.Progressbar(baixo, mode="determinate", maximum=100)
        self.progresso.pack(fill="x")
        self.log = tk.Text(baixo, height=6, state="disabled", wrap="word",
                           font=("Consolas", 9), bg="#fafafa")
        self.log.pack(fill="x", pady=(6, 0))

        meio = ttk.Frame(self, padding=8)
        meio.pack(side="top", fill="both", expand=True)
        lado = ttk.Frame(meio)
        lado.pack(side="right", fill="y", padx=(10, 0))

        # -- lista de confrontos ------------------------------------------
        colunas = ("id", "fase", "a", "b", "status", "duracao", "prazo", "placar")
        self.lista = ttk.Treeview(meio, columns=colunas, show="headings", selectmode="extended")
        larguras = {"id": 40, "fase": 150, "a": 160, "b": 160, "status": 140, "duracao": 64,
                    "prazo": 100, "placar": 60}
        titulos = {"id": "#", "fase": "fase", "a": "meme A", "b": "meme B", "status": "situação",
                   "duracao": "duração", "prazo": "votação", "placar": "A x B"}
        for c in colunas:
            self.lista.heading(c, text=titulos[c])
            self.lista.column(c, width=larguras[c], stretch=c in ("a", "b"),
                              anchor="w" if c in ("a", "b", "status", "fase") else "center")
        for tag, cor in _CORES.items():
            self.lista.tag_configure(tag, foreground=cor)
        self.lista.tag_configure("longo", background="#fff1e6")
        rolagem = ttk.Scrollbar(meio, orient="vertical", command=self.lista.yview)
        self.lista.configure(yscrollcommand=rolagem.set)
        rolagem.pack(side="right", fill="y")
        self.lista.pack(side="left", fill="both", expand=True)
        self.lista.bind("<<TreeviewSelect>>", lambda _e: self._selecao_mudou())
        self.lista.bind("<Double-1>", lambda _e: self._abrir_video())

        # -- lado direito: capa + ações ------------------------------------
        self.canvas = tk.Canvas(lado, width=CAPA_L, height=CAPA_A, bg="#111",
                                highlightthickness=0)
        self.canvas.grid(row=0, column=0, columnspan=2)
        self.lbl_detalhe = ttk.Label(lado, wraplength=CAPA_L + 40, justify="left")
        self.lbl_detalhe.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 6))

        # cada linha: uma ação em largura total ou duas lado a lado
        linhas: list[list[tuple[str, Callable[[], None]]]] = [
            [("Gerar vídeo dos selecionados", self._gerar_selecionados)],
            [("Gerar a rodada (pendentes)", self._gerar_rodada)],
            [("Prévia da capa", self._previa_capa), ("Ajustar no editor…", self._abrir_editor)],
            [("Abrir vídeo", self._abrir_video), ("Copiar legenda", self._copiar_legenda)],
            [("Publicar…", self._publicar)],
            [("Apurar comentários…", self._apurar)],
            [("Vencedor: A", lambda: self._vencedor_manual("a")),
             ("Vencedor: B", lambda: self._vencedor_manual("b"))],
            [("Pacote da rodada", self._pacote)],
        ]
        lado.columnconfigure((0, 1), weight=1, uniform="acao")
        self.botoes: dict[str, ttk.Button] = {}
        for r, linha in enumerate(linhas, start=2):
            for c, (texto, cmd) in enumerate(linha):
                botao = ttk.Button(lado, text=texto, command=cmd)
                botao.grid(row=r, column=c, columnspan=2 if len(linha) == 1 else 1,
                           sticky="ew", pady=2, padx=(0 if c == 0 else 2, 0))
                self.botoes[texto] = botao
        self.btn_cancelar = ttk.Button(lado, text="Cancelar fila", command=self._pedir_cancelar,
                                       state="disabled")
        self.btn_cancelar.grid(row=20, column=0, columnspan=2, sticky="ew", pady=(10, 0))


    # --------------------------------------------------------------- dados
    def _carregar_torneios(self) -> None:
        self._torneios = [t for t in self.estado.tournaments if t.get("status") != "aguardando"]
        self.combo_torneio["values"] = [
            f"#{t['id']} {t['nome']} ({t['status']})" for t in self._torneios
        ]
        if not self._torneios:
            self._escrever("nenhum torneio com chave sorteada (crie com app.cli torneio)")
            return
        atual = self.combo_torneio.current()
        self.combo_torneio.current(atual if 0 <= atual < len(self._torneios) else 0)
        self._torneio_mudou(manter_rodada=True)

    def _torneio(self) -> dict[str, Any] | None:
        i = self.combo_torneio.current()
        return self._torneios[i] if 0 <= i < len(self._torneios) else None

    def _torneio_mudou(self, manter_rodada: bool = False) -> None:
        torneio = self._torneio()
        if torneio is None:
            return
        matches = self.estado.matches_do_torneio(torneio["id"])
        rodadas = sorted({m["round"] for m in matches})
        tamanho = int(torneio.get("tamanho") or 2)
        self._rodadas = rodadas
        rotulos = [f"{r} — {kit.rotulo_rodada(tamanho >> (r - 1)).lower()}" for r in rodadas]
        self.combo_rodada["values"] = rotulos + [TODAS]
        anterior = self.combo_rodada.current() if manter_rodada else -1
        if 0 <= anterior <= len(rodadas):
            self.combo_rodada.current(anterior)
        else:
            atual = rodada_atual(self.estado, torneio["id"])
            self.combo_rodada.current(rodadas.index(atual) if atual in rodadas else len(rodadas))
        self._preencher_lista()

    def _rodada(self) -> int | None:
        i = self.combo_rodada.current()
        return self._rodadas[i] if 0 <= i < len(self._rodadas) else None

    def _matches_visiveis(self) -> list[dict[str, Any]]:
        torneio = self._torneio()
        if torneio is None:
            return []
        rodada = self._rodada()
        return [m for m in self.estado.matches_do_torneio(torneio["id"])
                if rodada is None or m["round"] == rodada]

    def _linha(self, m: dict[str, Any]) -> tuple[tuple, tuple[str, ...]]:
        nomes = {x["id"]: x["nome"] for x in self.estado.memes}
        torneio = self._torneio() or {}
        vagas = int(torneio.get("tamanho") or 2) >> (m["round"] - 1)
        nome_fase = kit.rotulo_rodada(vagas).lower().replace(" de final", "")
        fase = f"{nome_fase} · {m['posicao'] + 1}/{max(vagas // 2, 1)}"
        texto, tag = _STATUS.get(m["status"], (m["status"], "pendente"))
        if not (m.get("meme_a_id") and m.get("meme_b_id")) and m["status"] == "pendente":
            texto, tag = "aguardando oponente", "aguardando"
        prazo = _prazo(m)
        votacao = ""
        if m["status"] == "publicado":
            if prazo is None or prazo <= datetime.now(timezone.utc):
                texto, tag, votacao = "apurar agora", "apurar", "encerrada"
            else:
                votacao = f"até {prazo.astimezone():%d/%m %Hh}"
        if m["status"] == "finalizado" and m.get("winner_id"):
            texto = f"✓ {nomes.get(m['winner_id'], '?')}"
        duracao = m.get("duracao")
        tags = [tag]
        if duracao and duracao > self.roteiro.duracao_max:
            tags.append("longo")
        placar = f"{m.get('votos_a', 0)} x {m.get('votos_b', 0)}" if m["status"] in (
            "publicado", "finalizado") else ""
        valores = (
            m["id"], fase, nomes.get(m.get("meme_a_id"), "—"), nomes.get(m.get("meme_b_id"), "—"),
            texto, f"{duracao:.0f}s" if duracao else "", votacao, placar,
        )
        return valores, tuple(tags)

    def _preencher_lista(self) -> None:
        selecionados = set(self._ids_selecionados())
        self.lista.delete(*self.lista.get_children())
        visiveis = self._matches_visiveis()
        for m in visiveis:
            valores, tags = self._linha(m)
            self.lista.insert("", "end", iid=str(m["id"]), values=valores, tags=tags)
        for mid in selecionados:
            if self.lista.exists(str(mid)):
                self.lista.selection_add(str(mid))
        contagem: dict[str, int] = {}
        for m in visiveis:
            contagem[m["status"]] = contagem.get(m["status"], 0) + 1
        self.lbl_resumo.config(text="  ·  ".join(
            f"{_STATUS.get(k, (k,))[0]}: {v}" for k, v in sorted(contagem.items())))
        self._selecao_mudou()

    def _recarregar(self) -> None:
        if self._ocupado:
            return
        self.estado = Estado.carregar()
        self.roteiro = carregar_roteiro()
        self._carregar_torneios()
        self._escrever("dados recarregados do disco")

    # ------------------------------------------------------------ seleção
    def _ids_selecionados(self) -> list[int]:
        return [int(i) for i in self.lista.selection()] if hasattr(self, "lista") else []

    def _match_unico(self, exigir: bool = True) -> dict[str, Any] | None:
        ids = self._ids_selecionados()
        if len(ids) != 1:
            if exigir:
                messagebox.showinfo("Selecione um confronto", "Selecione exatamente um confronto.")
            return None
        return self.estado.buscar_match(ids[0])

    def _selecao_mudou(self) -> None:
        match = self._match_unico(exigir=False)
        self._mostrar_capa(match)
        if match is None:
            n = len(self._ids_selecionados())
            self.lbl_detalhe.config(text=f"{n} confrontos selecionados" if n else
                                    "Selecione um confronto (Ctrl/Shift para vários).")
            return
        linhas = []
        for chave, rotulo in (("tiktok_url", "TikTok"), ("instagram_url", "Instagram"),
                              ("youtube_url", "YouTube")):
            if match.get(chave):
                linhas.append(f"{rotulo}: {match[chave]}")
        if match.get("video_path"):
            linhas.append(f"vídeo: {match['video_path']}")
        self.lbl_detalhe.config(text="\n".join(linhas) or "ainda sem vídeo nem links")

    def _mostrar_capa(self, match: dict[str, Any] | None, caminho: Path | None = None) -> None:
        self.canvas.delete("all")
        caminho = caminho or (absoluto(match.get("capa_path")) if match else None)
        if caminho is not None and caminho.exists():
            with Image.open(caminho) as img:
                self._capa_tk = ImageTk.PhotoImage(img.convert("RGB").resize((CAPA_L, CAPA_A)))
            self.canvas.create_image(0, 0, image=self._capa_tk, anchor="nw")
        else:
            self.canvas.create_text(CAPA_L / 2, CAPA_A / 2, fill="#888", justify="center",
                                    text="sem capa\n\n“Prévia da capa” gera\nsem renderizar o vídeo")

    # ------------------------------------------------------------- tarefas
    def _ui(self, funcao: Callable[..., None], *args: Any) -> None:
        """Agenda ``funcao(*args)`` na thread da interface (seguro de qualquer thread)."""
        self._fila_ui.put((funcao, args))

    def _drenar_fila_ui(self) -> None:
        try:
            while True:
                funcao, args = self._fila_ui.get_nowait()
                funcao(*args)
        except queue.Empty:
            pass
        self.after(80, self._drenar_fila_ui)

    def _escrever(self, texto: str) -> None:
        """Acrescenta uma linha ao log (seguro a partir de outra thread)."""
        def _fazer() -> None:
            self.log.configure(state="normal")
            self.log.insert("end", f"{datetime.now():%H:%M:%S}  {texto}\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self._ui(_fazer)

    def _progresso(self, fracao: float) -> None:
        valor = max(0.0, min(1.0, fracao)) * 100
        self._ui(lambda: self.progresso.configure(value=valor))

    def _ocupar(self, ocupado: bool, fila: bool = False) -> None:
        self._ocupado = ocupado
        estado = "disabled" if ocupado else "normal"
        for botao in self.botoes.values():
            botao.configure(state=estado)
        self.btn_cancelar.configure(state="normal" if (ocupado and fila) else "disabled")
        self.configure(cursor="watch" if ocupado else "")

    def _rodar(self, alvo: Callable[[], None], fila: bool = False) -> None:
        """Roda ``alvo`` numa thread; ao terminar recarrega o estado e a lista."""
        self._ocupar(True, fila)
        self._cancelar = False

        def _thread() -> None:
            try:
                alvo()
            except Exception as exc:  # noqa: BLE001 — qualquer falha vai para o log
                self._escrever(f"ERRO: {str(exc).splitlines()[0]}")
            finally:
                self._ui(self._fim_tarefa)

        threading.Thread(target=_thread, daemon=True).start()

    def _fim_tarefa(self) -> None:
        self._ocupar(False)
        self.estado = Estado.carregar()
        self._preencher_lista()

    def _pedir_cancelar(self) -> None:
        self._cancelar = True
        self._escrever("cancelamento pedido: a fila para depois do vídeo atual")

    # --------------------------------------------------------- gerar vídeo
    def _confirmar_geracao(self, ids: list[int]) -> bool:
        nomes = {m["id"]: m["nome"] for m in self.estado.memes}
        linhas = []
        for mid in ids[:12]:
            m = self.estado.buscar_match(mid)
            linhas.append(f"#{mid}  {nomes.get(m['meme_a_id'])} vs {nomes.get(m['meme_b_id'])}")
        if len(ids) > 12:
            linhas.append(f"… e mais {len(ids) - 12}")
        return messagebox.askyesno(
            "Gerar vídeos",
            f"Gerar {len(ids)} vídeo(s)?\n\n" + "\n".join(linhas) +
            "\n\nClipes que não estão em cache serão baixados do YouTube.\n"
            "Cada vídeo leva ~1–2 min para renderizar.",
        )

    def _gerar(self, ids: list[int]) -> None:
        ids = [i for i in ids if (m := self.estado.buscar_match(i)) and jogavel(m)]
        if not ids:
            messagebox.showinfo("Nada a gerar", "Nenhum confronto jogável selecionado "
                                "(precisa dos dois memes e não pode estar finalizado).")
            return
        if not self._confirmar_geracao(ids):
            return

        def _fila() -> None:
            total = len(ids)
            for i, mid in enumerate(ids):
                if self._cancelar:
                    self._escrever("fila cancelada")
                    break
                estado = Estado.carregar()  # sempre do disco: não perde edições externas
                match = estado.buscar_match(mid)
                self._escrever(f"[{i + 1}/{total}] confronto #{mid}: baixando clipes…")
                try:
                    saida = assembler.montar_match(
                        estado, match,
                        progresso_download=lambda f, i=i: self._progresso((i + 0.4 * f) / total),
                        ao_montar=lambda i=i, mid=mid: self._escrever(
                            f"[{i + 1}/{total}] confronto #{mid}: gerando kit e renderizando…"),
                        progresso_montagem=lambda f, i=i: self._progresso((i + 0.4 + 0.6 * f) / total),
                    )
                except Exception as exc:  # noqa: BLE001 — segue com o próximo
                    self._escrever(f"[{i + 1}/{total}] confronto #{mid}: FALHOU — "
                                   f"{str(exc).splitlines()[0][:160]}")
                    continue
                estado.salvar()
                aviso = " (passa do limite!)" if match["duracao"] > self.roteiro.duracao_max else ""
                self._escrever(f"[{i + 1}/{total}] confronto #{mid}: ok — {saida.name}, "
                               f"{match['duracao']:.0f}s{aviso}")
                self._ui(self._atualizar_linha, mid)
            self._progresso(1.0)

        self._rodar(_fila, fila=True)

    def _atualizar_linha(self, mid: int) -> None:
        self.estado = Estado.carregar()
        match = self.estado.buscar_match(mid)
        if match is not None and self.lista.exists(str(mid)):
            valores, tags = self._linha(match)
            self.lista.item(str(mid), values=valores, tags=tags)
            self._selecao_mudou()

    def _gerar_selecionados(self) -> None:
        if not self._ids_selecionados():
            messagebox.showinfo("Selecione", "Selecione um ou mais confrontos na lista.")
            return
        self._gerar(self._ids_selecionados())

    def _gerar_rodada(self) -> None:
        pendentes = [m["id"] for m in self._matches_visiveis()
                     if jogavel(m) and m["status"] == "pendente"]
        if not pendentes:
            messagebox.showinfo("Nada pendente", "Todos os confrontos visíveis já têm vídeo.")
            return
        self._gerar(pendentes)

    # --------------------------------------------------------------- capa
    def _previa_capa(self) -> None:
        match = self._match_unico()
        if match is None or not jogavel(match):
            return
        mid = match["id"]

        def _gerar_kit() -> None:
            estado = Estado.carregar()
            m = estado.buscar_match(mid)
            self._escrever(f"confronto #{mid}: preparando clipes e kit…")
            clips = [preparar_clip(estado.buscar_meme(m[k])) for k in ("meme_a_id", "meme_b_id")]
            pacote = kit.gerar_kit(*clips, kit.confronto_do_match(estado, m), carregar_layout(),
                                   carregar_roteiro())
            self._escrever(f"confronto #{mid}: prévia pronta em {pacote.pasta}")
            self._ui(self._mostrar_capa, None, pacote.capa)

        self._rodar(_gerar_kit)

    # ------------------------------------------------------- outras ações
    def _abrir_editor(self) -> None:
        match = self._match_unico()
        if match is None:
            return
        subprocess.Popen([sys.executable, "-m", "app.cli", "editor", "--match", str(match["id"])],
                         cwd=BASE_DIR)
        self._escrever(f"editor aberto no confronto #{match['id']} — ao salvar lá, aperte F5 aqui")

    def _abrir_video(self) -> None:
        match = self._match_unico()
        if match is None:
            return
        video = absoluto(match.get("video_path"))
        if video is None or not video.exists():
            messagebox.showinfo("Sem vídeo", "Este confronto ainda não tem vídeo gerado.")
            return
        _abrir(video)

    def _copiar_legenda(self) -> None:
        match = self._match_unico()
        if match is None:
            return
        self.clipboard_clear()
        self.clipboard_append(legenda(self.estado, match))
        self._escrever(f"legenda do confronto #{match['id']} copiada")

    def _publicar(self) -> None:
        match = self._match_unico()
        if match is None:
            return
        if not match.get("video_path"):
            if not messagebox.askyesno("Sem vídeo", "Este confronto não tem vídeo gerado. "
                                       "Marcar como publicado mesmo assim?"):
                return
        DialogoPublicar(self, match)

    def _registrar_publicacao(self, mid: int, links: dict[str, str], horas: int) -> None:
        from datetime import timedelta

        estado = Estado.carregar()
        match = estado.buscar_match(mid)
        for campo, valor in links.items():
            if valor:
                match[campo] = valor
        inicio = datetime.now(timezone.utc).replace(microsecond=0)
        match["publicado_em"] = inicio.isoformat().replace("+00:00", "Z")
        match["deadline"] = (inicio + timedelta(hours=horas)).isoformat().replace("+00:00", "Z")
        match["status"] = "publicado"
        estado.salvar()
        self.estado = estado
        self.clipboard_clear()
        self.clipboard_append(legenda(estado, match))
        self._escrever(f"confronto #{mid} publicado; votação até "
                       f"{_prazo(match).astimezone():%d/%m %H:%M} (legenda copiada)")
        self._preencher_lista()

    def _apurar(self) -> None:
        from ..services import vote_parser

        match = self._match_unico()
        if match is None:
            return
        arquivo = filedialog.askopenfilename(
            title=f"Comentários do confronto #{match['id']}",
            filetypes=[("Comentários", "*.txt *.csv *.json"), ("Todos", "*.*")],
        )
        if not arquivo:
            return
        estado = Estado.carregar()
        m = estado.buscar_match(match["id"])
        res = vote_parser.apurar_match(estado, m, Path(arquivo))
        estado.salvar()
        self._escrever(f"confronto #{m['id']}: A {res.votos_a} x {res.votos_b} B (válidos "
                       f"{res.validos}, sem voto {res.invalidos}, repetidos {res.duplicados}, "
                       f"fora do prazo {res.fora_do_prazo})")
        torneio = estado.buscar_torneio(m["tournament_id"]) or {}
        vencedor = vote_parser.vencedor(res, m, torneio.get("seed"))
        if vencedor is not None:
            nome = (estado.buscar_meme(vencedor) or {}).get("nome", vencedor)
            empate = " (empate decidido pelo seed)" if res.votos_a == res.votos_b else ""
            if messagebox.askyesno(
                "Definir vencedor",
                f"A {res.votos_a} x {res.votos_b} B\n\nDefinir {nome} como vencedor{empate} "
                "e avançar na chave?",
            ):
                definir_vencedor(estado, m, vencedor)
                estado.salvar()
                self._escrever(f"confronto #{m['id']}: vencedor {nome}")
        else:
            messagebox.showinfo("Sem votos", "Nenhum voto válido encontrado no arquivo.")
        self.estado = Estado.carregar()
        self._preencher_lista()

    def _vencedor_manual(self, lado: str) -> None:
        match = self._match_unico()
        if match is None or not jogavel(match):
            return
        estado = Estado.carregar()
        m = estado.buscar_match(match["id"])
        vencedor = m[f"meme_{lado}_id"]
        nome = (estado.buscar_meme(vencedor) or {}).get("nome", vencedor)
        if not messagebox.askyesno("Definir vencedor",
                                   f"Definir {nome} ({lado.upper()}) como vencedor do confronto "
                                   f"#{m['id']} e avançar na chave?"):
            return
        definir_vencedor(estado, m, vencedor)
        estado.salvar()
        self._escrever(f"confronto #{m['id']}: vencedor {nome} (manual)")
        self.estado = estado
        self._preencher_lista()

    def _pacote(self) -> None:
        torneio, rodada = self._torneio(), self._rodada()
        if torneio is None or rodada is None:
            messagebox.showinfo("Escolha a rodada", "Escolha uma rodada específica (não 'todas').")
            return
        matches = [m for m in self._matches_visiveis() if m.get("video_path")]
        if not matches:
            messagebox.showinfo("Sem vídeos", "Nenhum confronto desta rodada tem vídeo gerado.")
            return
        pasta = empacotar(self.estado, matches, torneio["id"], rodada)
        self._escrever(f"pacote da rodada {rodada}: {pasta} ({len(matches)} vídeo(s))")
        _abrir(pasta)

    def _fechar(self) -> None:
        if self._ocupado and not messagebox.askyesno(
            "Sair", "Há uma geração em andamento. Fechar mesmo assim? (o vídeo atual é perdido)"
        ):
            return
        self.destroy()


class DialogoPublicar(tk.Toplevel):
    """Links do vídeo publicado + duração da votação."""

    def __init__(self, painel: Painel, match: dict[str, Any]) -> None:
        super().__init__(painel)
        self.painel = painel
        self.match_id = match["id"]
        self.title(f"Publicar confronto #{match['id']}")
        self.resizable(False, False)
        self.transient(painel)
        self.grab_set()

        corpo = ttk.Frame(self, padding=12)
        corpo.grid()
        self.vars: dict[str, tk.StringVar] = {}
        for i, (campo, rotulo) in enumerate((("tiktok_url", "TikTok"),
                                             ("instagram_url", "Instagram (Reels)"),
                                             ("youtube_url", "YouTube (Shorts)"))):
            ttk.Label(corpo, text=rotulo).grid(row=i, column=0, sticky="w", pady=3)
            var = tk.StringVar(value=match.get(campo) or "")
            ttk.Entry(corpo, textvariable=var, width=56).grid(row=i, column=1, pady=3)
            self.vars[campo] = var
        ttk.Label(corpo, text="Votação (horas)").grid(row=3, column=0, sticky="w", pady=3)
        self.horas = tk.StringVar(value="48")
        ttk.Spinbox(corpo, from_=1, to=336, textvariable=self.horas, width=6).grid(
            row=3, column=1, sticky="w", pady=3)
        ttk.Label(corpo, foreground="#666",
                  text="O prazo começa agora. A legenda vai para a área de transferência.").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))
        botoes = ttk.Frame(corpo)
        botoes.grid(row=5, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(botoes, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(botoes, text="Publicar", command=self._ok).pack(side="right", padx=(0, 6))
        self.bind("<Return>", lambda _e: self._ok())
        self.bind("<Escape>", lambda _e: self.destroy())

    def _ok(self) -> None:
        links = {k: v.get().strip() for k, v in self.vars.items()}
        if not any(links.values()):
            messagebox.showwarning("Link", "Informe ao menos um link do vídeo publicado.",
                                   parent=self)
            return
        try:
            horas = max(1, int(self.horas.get()))
        except ValueError:
            messagebox.showwarning("Horas", "Duração da votação inválida.", parent=self)
            return
        self.destroy()
        self.painel._registrar_publicacao(self.match_id, links, horas)


def executar() -> None:
    """Abre o painel (bloqueia até fechar a janela)."""
    if sys.platform.startswith("win"):
        try:  # texto nítido em telas com escala (125%, 150%...)
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001 — Windows antigo: segue sem
            pass
    Painel().mainloop()


if __name__ == "__main__":
    executar()
