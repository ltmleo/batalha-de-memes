"""Editor visual desktop da Batalha de Memes (Tkinter + Pillow).

Ajusta com preview ao vivo:
- a área do clipe dentro da moldura (arraste com 8 alças ou campos numéricos);
- o título de cada lado (override por confronto, gravado em ``estado.json``);
- o preenchimento da área (cover = corta as bordas / contain = barras pretas).

O layout global é salvo em ``data/layout.json`` e passa a valer para todo o
pipeline (``montar`` da CLI inclusive). "Frame exato" renderiza um quadro com o
ffmpeg para conferir o resultado real; "Salvar e gerar vídeo" salva e monta o mp4
do confronto (com "Salvar só o layout" para gravar sem gerar).
"""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from PIL import Image, ImageTk

from .. import titulo
from ..config import CLIPS_DIR, MOLDURA_PATH
from ..layout import Layout, carregar_layout, salvar_layout
from ..services import assembler, downloader
from ..services.catalog import carregar_catalogo
from ..store import Estado
from .preview import _carregar_moldura, compor_preview, extrair_frame, renderizar_frame_exato

ESCALA = 1 / 3  # 1080x1920 -> 360x640 no canvas
CANVAS_L, CANVAS_A = 360, 640
ALCA_RAIO = 8  # tolerância de clique nas alças (px do canvas)
LADO_MIN = 0.02  # tamanho mínimo da área (fração do quadro)


def _hhmmss(segundos: float) -> str:
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class Editor(tk.Tk):
    """Janela do editor: preview à esquerda, controles à direita."""

    def __init__(self, match_id: int | None = None) -> None:
        super().__init__()
        self.title("Batalha de Memes — editor de montagem")
        self._match_inicial = match_id
        self.resizable(False, False)

        self.estado = Estado.carregar()
        self.layout: Layout = carregar_layout()
        self.moldura = _carregar_moldura()
        self.match: dict[str, Any] | None = None
        self.frames: dict[int, Image.Image | None] = {}
        self._arrastando: dict[str, Any] | None = None
        self._imagem: ImageTk.PhotoImage | None = None
        self._lado = tk.StringVar(value="a")
        self._preenchimento = tk.StringVar(value=self.layout.preenchimento)
        self._var_x = tk.StringVar()
        self._var_y = tk.StringVar()
        self._var_l = tk.StringVar()
        self._var_a = tk.StringVar()
        self._var_titulo_a = tk.StringVar()
        self._var_titulo_b = tk.StringVar()
        self._var_titulo_y = tk.StringVar()
        self._var_titulo_largura = tk.StringVar()
        self._var_titulo_fonte = tk.StringVar()
        self._auto_fonte = tk.BooleanVar(value=self.layout.titulo_fonte == 0)

        if self.moldura is None:
            messagebox.showwarning(
                "Moldura ausente",
                f"Não encontrei {MOLDURA_PATH}.\nO preview mostra o quadro preto.",
            )

        self._montar_ui()
        self._sincronizar_campos()
        self._carregar_matches()
        self._aplicar()
        self.bind("<Control-s>", lambda _e: self._salvar_e_gerar())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ------------------------------------------------------------------ UI
    def _montar_ui(self) -> None:
        raiz = ttk.Frame(self, padding=8)
        raiz.grid(sticky="nsew")

        # -- preview ----------------------------------------------------
        self.canvas = tk.Canvas(
            raiz, width=CANVAS_L, height=CANVAS_A, bg="#111", highlightthickness=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<ButtonPress-1>", self._pressionar)
        self.canvas.bind("<B1-Motion>", self._arrastar)
        self.canvas.bind("<ButtonRelease-1>", lambda _e: self._finalizar())

        painel = ttk.Frame(raiz)
        painel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # -- confronto --------------------------------------------------
        f_match = ttk.LabelFrame(painel, text="Confronto", padding=8)
        f_match.grid(sticky="ew")
        self.combo = ttk.Combobox(f_match, state="readonly", width=30)
        self.combo.grid(sticky="ew")
        self.combo.bind("<<ComboboxSelected>>", lambda _e: self._selecionar_match())
        ttk.Button(f_match, text="Baixar clipes p/ preview", command=self._baixar_clipes).grid(
            sticky="ew", pady=(6, 0)
        )

        # -- dados (json) ----------------------------------------------
        f_dados = ttk.LabelFrame(painel, text="Dados (json)", padding=8)
        f_dados.grid(sticky="ew", pady=(8, 0))
        ttk.Button(f_dados, text="Sincronizar catálogo (seed)",
                   command=self._sincronizar_catalogo).grid(sticky="ew")
        ttk.Button(f_dados, text="Recarregar do disco",
                   command=self._recarregar).grid(sticky="ew", pady=(4, 0))
        ttk.Label(f_dados, text="data/memes/*.json → estado.json → editor",
                  foreground="#666").grid(sticky="w", pady=(4, 0))

        # -- ver lado ---------------------------------------------------
        f_lado = ttk.LabelFrame(painel, text="Ver no preview", padding=8)
        f_lado.grid(sticky="ew", pady=(8, 0))
        ttk.Radiobutton(f_lado, text="Meme A", value="a", variable=self._lado,
                        command=self._aplicar).grid(row=0, column=0)
        ttk.Radiobutton(f_lado, text="Meme B", value="b", variable=self._lado,
                        command=self._aplicar).grid(row=0, column=1)

        # -- título -----------------------------------------------------
        f_titulo = ttk.LabelFrame(painel, text="Título (vazio = nome do meme)", padding=8)
        f_titulo.grid(sticky="ew", pady=(8, 0))
        ttk.Label(f_titulo, text="A").grid(row=0, column=0, padx=(0, 4))
        e_a = ttk.Entry(f_titulo, textvariable=self._var_titulo_a, width=24)
        e_a.grid(row=0, column=1, sticky="ew")
        ttk.Label(f_titulo, text="B").grid(row=1, column=0, padx=(0, 4), pady=(6, 0))
        e_b = ttk.Entry(f_titulo, textvariable=self._var_titulo_b, width=24)
        e_b.grid(row=1, column=1, sticky="ew", pady=(6, 0))
        for entrada in (e_a, e_b):
            entrada.bind("<KeyRelease>", lambda _e: self._aplicar())

        # -- enquadramento do título ------------------------------------
        f_enq = ttk.LabelFrame(painel, text="Enquadramento do título", padding=8)
        f_enq.grid(sticky="ew", pady=(8, 0))
        ttk.Label(f_enq, text="Posição Y (%)").grid(row=0, column=0, sticky="w", padx=(0, 4))
        sp_y = ttk.Spinbox(f_enq, from_=2.0, to=98.0, increment=0.5, width=7,
                           textvariable=self._var_titulo_y, command=self._campos_mudaram)
        sp_y.grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Label(f_enq, text="Largura (%)").grid(row=0, column=2, sticky="w", padx=(8, 4))
        sp_larg = ttk.Spinbox(f_enq, from_=10.0, to=100.0, increment=1.0, width=7,
                              textvariable=self._var_titulo_largura, command=self._campos_mudaram)
        sp_larg.grid(row=0, column=3, sticky="ew", pady=2)
        for spin in (sp_y, sp_larg):
            spin.bind("<KeyRelease>", lambda _e: self._campos_mudaram())
            spin.bind("<FocusOut>", lambda _e: self._campos_mudaram())
        ttk.Checkbutton(f_enq, text="Tamanho automático", variable=self._auto_fonte,
                        command=self._auto_mudou).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(f_enq, text="Fonte (px)").grid(row=1, column=2, sticky="w", padx=(8, 4))
        self.sp_fonte = ttk.Spinbox(f_enq, from_=titulo.FONTE_MIN, to=400, increment=2, width=7,
                                    textvariable=self._var_titulo_fonte, command=self._campos_mudaram)
        self.sp_fonte.grid(row=1, column=3, sticky="ew", pady=(6, 0))
        self.sp_fonte.bind("<KeyRelease>", lambda _e: self._campos_mudaram())
        self.sp_fonte.bind("<FocusOut>", lambda _e: self._campos_mudaram())
        ttk.Label(
            f_enq, text="Arraste a faixa amarela no preview\npara subir/descer o título.",
            foreground="#666", justify="left",
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))

        # -- preenchimento ----------------------------------------------
        f_preench = ttk.LabelFrame(painel, text="Preenchimento do clipe", padding=8)
        f_preench.grid(sticky="ew", pady=(8, 0))
        ttk.Radiobutton(f_preench, text="Cover — corta as bordas", value="cover",
                        variable=self._preenchimento, command=self._preenchimento_mudou).grid(
            sticky="w"
        )
        ttk.Radiobutton(f_preench, text="Contain — barras pretas", value="contain",
                        variable=self._preenchimento, command=self._preenchimento_mudou).grid(
            sticky="w", pady=(4, 0)
        )

        # -- área do vídeo ----------------------------------------------
        f_area = ttk.LabelFrame(painel, text="Área do vídeo na moldura (%)", padding=8)
        f_area.grid(sticky="ew", pady=(8, 0))
        self._spinboxes: dict[str, ttk.Spinbox] = {}
        for i, (rotulo, var) in enumerate(
            (("X", self._var_x), ("Y", self._var_y), ("Largura", self._var_l), ("Altura", self._var_a))
        ):
            ttk.Label(f_area, text=rotulo).grid(row=i // 2, column=(i % 2) * 2, sticky="w", padx=(0, 4))
            spin = ttk.Spinbox(
                f_area, from_=0.0, to=100.0, increment=0.5, textvariable=var, width=7,
                command=self._campos_mudaram,
            )
            spin.grid(row=i // 2, column=(i % 2) * 2 + 1, sticky="ew", pady=2)
            spin.bind("<KeyRelease>", lambda _e: self._campos_mudaram())
            spin.bind("<FocusOut>", lambda _e: self._campos_mudaram())
            self._spinboxes[rotulo.lower()] = spin
        ttk.Label(
            f_area, text="Também dá para arrastar a área\nno preview (alças nos cantos).",
            foreground="#666", justify="left",
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))

        # -- ações ------------------------------------------------------
        f_acoes = ttk.Frame(painel, padding=(0, 8, 0, 0))
        f_acoes.grid(sticky="ew")
        self.botao_gerar = ttk.Button(f_acoes, text="Salvar e gerar vídeo", command=self._salvar_e_gerar)
        self.botao_gerar.grid(sticky="ew")
        ttk.Button(f_acoes, text="Salvar só o layout", command=self._salvar).grid(
            sticky="ew", pady=(4, 0)
        )
        ttk.Button(f_acoes, text="Restaurar padrão", command=self._restaurar).grid(
            sticky="ew", pady=(4, 0)
        )
        ttk.Button(f_acoes, text="Frame exato (ffmpeg)", command=self._frame_exato).grid(
            sticky="ew", pady=(4, 0)
        )

        # -- status -----------------------------------------------------
        self.progresso = ttk.Progressbar(raiz, mode="determinate", maximum=100)
        self.progresso.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.barra_status = ttk.Label(raiz, text="Pronto.", anchor="w", relief="sunken")
        self.barra_status.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    # --------------------------------------------------------------- dados
    def _carregar_matches(self, manter_selecao: bool = True) -> None:
        selecionado = self.match.get("id") if (manter_selecao and self.match) else None
        if selecionado is None:
            selecionado, self._match_inicial = self._match_inicial, None
        completos = [
            m for m in self.estado.matches if m.get("meme_a_id") and m.get("meme_b_id")
        ]
        nomes = {m["id"]: m["nome"] for m in self.estado.memes}
        self._matches = completos
        self.combo["values"] = [
            f"#{m['id']}  {nomes.get(m['meme_a_id'], '?')} vs {nomes.get(m['meme_b_id'], '?')}"
            for m in completos
        ]
        if completos:
            indice = 0
            if selecionado is not None:
                indice = next(
                    (i for i, m in enumerate(completos) if m["id"] == selecionado), 0
                )
            self.combo.current(indice)
            self._selecionar_match(silencioso=True)

    def _selecionar_match(self, silencioso: bool = False) -> None:
        indice = self.combo.current()
        self.match = self._matches[indice] if 0 <= indice < len(self._matches) else None
        if self.match is not None:
            self._var_titulo_a.set(self.match.get("titulo_a") or "")
            self._var_titulo_b.set(self.match.get("titulo_b") or "")
        if not silencioso:
            self._status(f"confronto selecionado: {self.combo.get()}")
        self._aplicar()

    def _meme(self, lado: str) -> dict[str, Any] | None:
        if self.match is None:
            return None
        return self.estado.buscar_meme(self.match.get(f"meme_{lado}_id"))

    def _titulo_efetivo(self, lado: str) -> str:
        """Texto digitado no campo ou, se vazio, o nome do meme."""
        digitado = (self._var_titulo_a.get() if lado == "a" else self._var_titulo_b.get()).strip()
        if digitado:
            return digitado
        meme = self._meme(lado)
        return meme["nome"] if meme else ""

    def _override_titulo(self, lado: str) -> str | None:
        """Grava no estado só se difere do nome do meme (senão, padrão)."""
        meme = self._meme(lado)
        texto = self._titulo_efetivo(lado).strip()
        if meme and texto == meme["nome"]:
            return None
        return texto or None

    def _clip_caminho(self, lado: str) -> Path | None:
        meme = self._meme(lado)
        if meme is None:
            return None
        caminho = CLIPS_DIR / f"clip_meme_{meme['id']}.mp4"
        return caminho if caminho.exists() else None

    def _frame_conteudo(self, lado: str) -> Image.Image | None:
        """Frame do clipe normalizado (lê do disco, com cache em memória)."""
        meme = self._meme(lado)
        if meme is None:
            return None
        if meme["id"] not in self.frames:
            self.frames[meme["id"]] = extrair_frame(self._clip_caminho(lado))
        return self.frames[meme["id"]]

    # ------------------------------------------------------- layout/preview
    def _sincronizar_campos(self) -> None:
        self._var_x.set(f"{self.layout.x * 100:.1f}")
        self._var_y.set(f"{self.layout.y * 100:.1f}")
        self._var_l.set(f"{self.layout.l * 100:.1f}")
        self._var_a.set(f"{self.layout.a * 100:.1f}")
        self._var_titulo_y.set(f"{self.layout.titulo_y * 100:.1f}")
        self._var_titulo_largura.set(f"{self.layout.titulo_largura * 100:.1f}")
        automatico = self.layout.titulo_fonte == 0
        self._auto_fonte.set(automatico)
        if automatico:
            # mostra o tamanho que o ajuste automático escolheu (base p/ o manual)
            self._var_titulo_fonte.set(str(titulo.tamanho(self._titulo_efetivo(self._lado.get()), self.layout)))
        else:
            self._var_titulo_fonte.set(str(self.layout.titulo_fonte))
        self.sp_fonte.config(state="disabled" if automatico else "normal")

    def _ler_campos(self) -> None:
        def _frac(var: tk.StringVar, atual: float) -> float:
            try:
                return float(var.get().replace(",", ".")) / 100
            except ValueError:
                return atual

        self.layout.x = _frac(self._var_x, self.layout.x)
        self.layout.y = _frac(self._var_y, self.layout.y)
        self.layout.l = _frac(self._var_l, self.layout.l)
        self.layout.a = _frac(self._var_a, self.layout.a)
        self.layout.titulo_y = _frac(self._var_titulo_y, self.layout.titulo_y)
        self.layout.titulo_largura = _frac(self._var_titulo_largura, self.layout.titulo_largura)
        self.layout.titulo_fonte = 0 if self._auto_fonte.get() else self._fonte_digitada()
        self.layout.normalizar()

    def _fonte_digitada(self) -> int:
        try:
            return max(0, int(float(self._var_titulo_fonte.get().replace(",", "."))))
        except ValueError:
            return self.layout.titulo_fonte or 0

    def _auto_mudou(self) -> None:
        automatico = self._auto_fonte.get()
        self.sp_fonte.config(state="disabled" if automatico else "normal")
        self.layout.titulo_fonte = 0 if automatico else self._fonte_digitada()
        self._sincronizar_campos()
        self._aplicar()

    def _campos_mudaram(self) -> None:
        self._ler_campos()
        self._sincronizar_campos()
        self._aplicar()

    def _preenchimento_mudou(self) -> None:
        self.layout.preenchimento = self._preenchimento.get()
        self._aplicar()

    def _aplicar(self) -> None:
        """Redesenha o preview PIL + retângulo com o estado atual."""
        self.layout.normalizar()
        lado = self._lado.get()
        img = compor_preview(
            self.layout,
            self._titulo_efetivo(lado),
            self._frame_conteudo(lado),
            ESCALA,
            moldura=self.moldura,
        )
        self._exibir_imagem(img)

    def _exibir_imagem(self, img: Image.Image) -> None:
        self._imagem = ImageTk.PhotoImage(img)
        self.canvas.delete("img")
        self.canvas.create_image(0, 0, image=self._imagem, anchor="nw", tags="img")
        self._desenhar_retangulo()

    # -- retângulo arrastável -------------------------------------------
    def _retangulo(self) -> tuple[float, float, float, float]:
        return (
            self.layout.x * CANVAS_L,
            self.layout.y * CANVAS_A,
            (self.layout.x + self.layout.l) * CANVAS_L,
            (self.layout.y + self.layout.a) * CANVAS_A,
        )

    def _alcas(self) -> dict[str, tuple[float, float]]:
        x0, y0, x1, y1 = self._retangulo()
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        return {
            "nw": (x0, y0), "n": (cx, y0), "ne": (x1, y0),
            "w": (x0, cy), "e": (x1, cy),
            "sw": (x0, y1), "s": (cx, y1), "se": (x1, y1),
        }

    def _faixa_titulo(self) -> tuple[float, float, float, float]:
        """(x0, y, x1, y) da faixa do título no canvas."""
        cx = CANVAS_L / 2
        meia = self.layout.titulo_largura * CANVAS_L / 2
        return (cx - meia, self.layout.titulo_y * CANVAS_A, cx + meia, self.layout.titulo_y * CANVAS_A)

    def _desenhar_retangulo(self) -> None:
        self.canvas.delete("ui")
        x0, y0, x1, y1 = self._retangulo()
        self.canvas.create_rectangle(x0, y0, x1, y1, outline="#00e5ff", width=2, dash=(4, 3), tags="ui")
        for cx, cy in self._alcas().values():
            self.canvas.create_rectangle(
                cx - 5, cy - 5, cx + 5, cy + 5, fill="#00e5ff", outline="#00343d", tags="ui"
            )
        # faixa do título (arrastável na vertical)
        tx0, ty, tx1, _ = self._faixa_titulo()
        self.canvas.create_line(tx0, ty, tx1, ty, fill="#ffd54a", width=1, dash=(3, 3), tags="ui")
        cx = CANVAS_L / 2
        self.canvas.create_rectangle(cx - 7, ty - 7, cx + 7, ty + 7,
                                     fill="#ffd54a", outline="#4d3d00", tags="ui")

    def _hit_test(self, px: float, py: float) -> str | None:
        tx0, ty, tx1, _ = self._faixa_titulo()
        if abs(py - ty) <= ALCA_RAIO and tx0 - ALCA_RAIO <= px <= tx1 + ALCA_RAIO:
            return "titulo"
        for nome, (cx, cy) in self._alcas().items():
            if abs(px - cx) <= ALCA_RAIO and abs(py - cy) <= ALCA_RAIO:
                return nome
        x0, y0, x1, y1 = self._retangulo()
        if x0 <= px <= x1 and y0 <= py <= y1:
            return "mover"
        return None

    def _pressionar(self, evento: tk.Event) -> None:
        alca = self._hit_test(evento.x, evento.y)
        if alca is None:
            return
        self._arrastando = {
            "alca": alca,
            "x0": evento.x,
            "y0": evento.y,
            "rect": self._retangulo(),
            "titulo_y": self.layout.titulo_y,
        }

    def _arrastar(self, evento: tk.Event) -> None:
        if self._arrastando is None:
            return
        arraste = self._arrastando
        dx = (evento.x - arraste["x0"]) / CANVAS_L
        dy = (evento.y - arraste["y0"]) / CANVAS_A
        alca = arraste["alca"]

        if alca == "titulo":
            self.layout.titulo_y = arraste["titulo_y"] + dy
            self.layout.normalizar()
            self._sincronizar_campos()
            self._aplicar()
            return

        x0, y0, x1, y1 = arraste["rect"]
        x, y, l, a = x0 / CANVAS_L, y0 / CANVAS_A, (x1 - x0) / CANVAS_L, (y1 - y0) / CANVAS_A

        if alca == "mover":
            x, y = x + dx, y + dy
        else:
            if "w" in alca:
                novo_x = min(max(x + dx, 0.0), x + l - LADO_MIN)
                l += x - novo_x
                x = novo_x
            if "e" in alca:
                l = min(max(l + dx, LADO_MIN), 1.0 - x)
            if "n" in alca:
                novo_y = min(max(y + dy, 0.0), y + a - LADO_MIN)
                a += y - novo_y
                y = novo_y
            if "s" in alca:
                a = min(max(a + dy, LADO_MIN), 1.0 - y)

        self.layout.x, self.layout.y = x, y
        self.layout.l, self.layout.a = l, a
        self.layout.normalizar()
        self._sincronizar_campos()
        self._aplicar()

    def _finalizar(self) -> None:
        if self._arrastando is not None:
            alvo = "título" if self._arrastando["alca"] == "titulo" else "área"
            self._arrastando = None
            self._status(f"{alvo} atualizado(a) — lembre de clicar em Salvar")

    # -------------------------------------------------------------- ações
    def _salvar(self) -> None:
        self._ler_campos()
        caminho = salvar_layout(self.layout)
        if self.match is not None:
            self.match["titulo_a"] = self._override_titulo("a")
            self.match["titulo_b"] = self._override_titulo("b")
            self.estado.salvar()
        self._status(f"salvo: {caminho.name} (layout global)"
                     + (", títulos no confronto" if self.match is not None else ""))

    def _restaurar(self) -> None:
        self.layout = Layout()
        self._preenchimento.set(self.layout.preenchimento)
        self._sincronizar_campos()
        self._aplicar()
        self._status("padrão restaurado (área, título e preenchimento) — clique em Salvar para aplicar")

    def _sincronizar_catalogo(self) -> None:
        """Copia data/memes/*.json -> estado.json (mesmo que o `seed` da CLI)."""
        if not messagebox.askyesno(
            "Sincronizar catálogo",
            "Copiar data/memes/*.json para o estado.json?\n\n"
            "Atualiza link/trecho/metadados dos memes existentes (casados por nome) e "
            "insere os novos. O chaveamento e os votos não mudam.\n\n"
            "Útil quando você edita os arquivos de temporada e quer ver no editor.",
        ):
            self._status("sincronização cancelada")
            return
        try:
            estado = Estado.carregar()
            inseridos = carregar_catalogo(estado)
            caminho = estado.salvar()
            self.estado = Estado.carregar()
            self.frames.clear()
            self._carregar_matches()
            self._status(
                f"catálogo sincronizado: {inseridos} novo(s), {caminho.name} atualizado"
            )
        except Exception as exc:  # noqa: BLE001 — a UI precisa mostrar qualquer erro
            messagebox.showerror("Falha ao sincronizar catálogo", str(exc))
            self._status(f"erro ao sincronizar catálogo: {exc}")

    def _recarregar(self) -> None:
        """Relê estado.json + layout.json do disco (descarta edições não salvas)."""
        if not messagebox.askyesno(
            "Recarregar do disco",
            "Relê estado.json e layout.json, descartando ajustes não salvos no editor.\n\n"
            "Continuar?",
        ):
            self._status("recarga cancelada")
            return
        self.estado = Estado.carregar()
        self.layout = carregar_layout()
        self.frames.clear()
        self._preenchimento.set(self.layout.preenchimento)
        self._sincronizar_campos()
        self._carregar_matches()
        self._aplicar()
        self._status("recarregado do disco (estado.json + layout.json)")

    # ------------------------------------------------------------ progresso
    def _progresso_de(self, valor: float) -> None:
        """Agenda a atualização da barra (pode ser chamado de outra thread)."""
        self.after(0, self._set_progresso, valor)

    def _set_progresso(self, valor: float) -> None:
        if str(self.progresso.cget("mode")) != "determinate":
            self.progresso.stop()
            self.progresso.config(mode="determinate")
        self.progresso["value"] = max(0.0, min(1.0, valor)) * 100

    def _progresso_iniciar(self) -> None:
        self.progresso.stop()
        self.progresso.config(mode="determinate")
        self.progresso["value"] = 0

    def _progresso_montagem(self) -> None:
        """Marco da montagem: mantém a barra determinada e explica a demora."""
        self.progresso.stop()
        self.progresso.config(mode="determinate")
        self.progresso["value"] = 50
        self._status("renderizando o vídeo com ffmpeg… (pode demorar alguns minutos)")

    def _progresso_render(self, valor: float) -> None:
        """Fração da renderização (0..1) -> metade direita da barra (50..100%)."""
        self._progresso_de(0.5 + 0.5 * max(0.0, min(1.0, valor)))

    def _progresso_fim(self, sucesso: bool) -> None:
        self.progresso.stop()
        self.progresso.config(mode="determinate")
        self.progresso["value"] = 100 if sucesso else 0

    def _confirmar_download(self, acao: str) -> bool:
        """Mostra o que será baixado e pede confirmação antes de acessar a rede."""
        if self.match is None:
            self._status("selecione um confronto primeiro")
            return False
        blocos = []
        for lado in ("a", "b"):
            meme = self._meme(lado)
            if meme is None:
                continue
            url = meme.get("youtube_url") or "(sem link definido)"
            inicio = float(meme.get("inicio") or 0)
            fim = float(meme.get("fim") or 0)
            blocos.append(
                f"{lado.upper()} — {meme['nome']}\n"
                f"   {url}\n"
                f"   trecho {_hhmmss(inicio)}–{_hhmmss(fim)}"
            )
        texto = (
            f"{acao}\n\n"
            + "\n\n".join(blocos)
            + "\n\nOs clipes já baixados são reaproveitados.\nDeseja continuar?"
        )
        return messagebox.askyesno("Confirmar download dos vídeos", texto)

    def _baixar_clipes(self) -> None:
        if self.match is None:
            self._status("selecione um confronto primeiro")
            return
        lados = [l for l in ("a", "b") if self._meme(l)]
        if not self._confirmar_download("Baixar os clipes deste confronto para o preview?"):
            self._status("download cancelado")
            return
        self._progresso_iniciar()
        self._status("baixando/normalizando clipes… (pode demorar)")
        threading.Thread(target=self._thread_baixar, args=(lados,), daemon=True).start()

    def _thread_baixar(self, lados: list[str]) -> None:
        try:
            total = max(1, len(lados))
            for indice, lado in enumerate(lados):
                meme = self._meme(lado)
                if meme is None:
                    continue

                def _callback(fracao: float, _i: int = indice) -> None:
                    self._progresso_de((_i + fracao) / total)

                downloader.preparar_clip(meme, progresso=_callback)
            self.after(0, self._baixados_ok, None)
        except Exception as exc:  # noqa: BLE001 — a UI precisa mostrar qualquer erro
            self.after(0, self._baixados_ok, exc)

    def _baixados_ok(self, erro: Exception | None) -> None:
        self.frames.clear()
        if erro is not None:
            self._progresso_fim(False)
            messagebox.showerror("Falha ao baixar clipes", str(erro))
            self._status(f"erro no download: {erro}")
        else:
            self._progresso_fim(True)
            self._status("clipes prontos — preview atualizado")
        self._aplicar()

    def _frame_exato(self) -> None:
        lado = self._lado.get()
        clip = self._clip_caminho(lado)
        if clip is None:
            self._status("clipe não baixado — use 'Baixar clipes p/ preview' antes")
            return
        texto = self._titulo_efetivo(lado)
        layout = self.layout
        self._status("renderizando frame exato com ffmpeg…")
        threading.Thread(
            target=self._thread_exato, args=(clip, layout, texto), daemon=True
        ).start()

    def _thread_exato(self, clip: Path, layout: Layout, texto: str) -> None:
        destino = renderizar_frame_exato(clip, layout, texto)
        self.after(0, self._mostrar_exato, destino)

    def _mostrar_exato(self, destino: Path | None) -> None:
        if destino is None:
            self._status("falha ao renderizar o frame exato (veja o console)")
            return
        img = Image.open(destino).convert("RGB").resize((CANVAS_L, CANVAS_A), Image.LANCZOS)
        self._exibir_imagem(img)
        self._status(f"frame exato: {destino.name} (qualquer ajuste volta ao preview rápido)")

    def _salvar_e_gerar(self) -> None:
        """Salva o layout/títulos e, em seguida, gera o vídeo do confronto."""
        self._salvar()
        self._gerar_video(salvar=False)

    def _gerar_video(self, salvar: bool = True) -> None:
        if self.match is None:
            self._status("selecione um confronto primeiro")
            return
        if salvar:
            self._salvar()
        match_id = self.match["id"]
        titulo_a, titulo_b = self._override_titulo("a"), self._override_titulo("b")
        self.match["titulo_a"], self.match["titulo_b"] = titulo_a, titulo_b
        if not self._confirmar_download(
            "Gerar o vídeo deste confronto? (os clipes são baixados, se necessário)"
        ):
            self._status("geração cancelada")
            return
        self.botao_gerar.config(state="disabled")
        self._progresso_iniciar()
        self._status("baixando clipes e montando o vídeo… (pode demorar)")
        threading.Thread(
            target=self._thread_gerar, args=(match_id, titulo_a, titulo_b), daemon=True
        ).start()

    def _thread_gerar(self, match_id: int, titulo_a: str | None, titulo_b: str | None) -> None:
        try:
            estado = Estado.carregar()  # recarrega para não sobrescrever edições externas
            match = estado.buscar_match(match_id)
            if match is None:
                raise RuntimeError(f"confronto {match_id} não encontrado")
            match["titulo_a"], match["titulo_b"] = titulo_a, titulo_b
            saida = assembler.montar_match(
                estado,
                match,
                progresso_download=lambda p: self._progresso_de(0.5 * p),
                ao_montar=lambda: self.after(0, self._progresso_montagem),
                progresso_montagem=self._progresso_render,
            )
            estado.salvar()
            self.after(0, self._gerado, saida, None)
        except Exception as exc:  # noqa: BLE001 — a UI precisa mostrar qualquer erro
            self.after(0, self._gerado, None, exc)

    def _gerado(self, saida: Path | None, erro: Exception | None) -> None:
        self.botao_gerar.config(state="normal")
        if erro is not None:
            self._progresso_fim(False)
            messagebox.showerror("Falha ao gerar vídeo", str(erro))
            self._status(f"erro na montagem: {erro}")
        else:
            self._progresso_fim(True)
            self._status(f"vídeo gerado: {saida}")

    def _status(self, msg: str) -> None:
        self.barra_status.config(text=msg)


def executar(match_id: int | None = None) -> None:
    """Abre o editor (bloqueia até fechar a janela), opcionalmente num confronto."""
    Editor(match_id).mainloop()


if __name__ == "__main__":
    executar()
