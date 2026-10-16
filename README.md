# Batalha de Memes

Automatiza a produção de vídeos de "batalha de memes" para o TikTok: dois clipes de
meme se enfrentam, o público vota nos comentários e o vencedor avança no chaveamento.

- **Backend/worker:** Python 3.11, sem servidor. O pipeline lê e grava o estado em
  `backend/data/estado.json` (fonte única da verdade — sem banco, sem API).
- **Download/edição:** `yt-dlp` + `ffmpeg` (binário embutido via `imageio-ffmpeg`).
- **Site:** Next.js em **export estático** (`output: "export"`): o build lê
  `data/estado.json` e gera HTML/CSS/JS puros em `frontend/out/`.

Status atual: catálogo, chaveamento e CLI prontos; `downloader.py` e `assembler.py`
já geram um vídeo de confronto (abertura + moldura + título + clipes) e há um
**editor visual desktop** (`app.cli editor`) para ajustar a área do vídeo na
moldura, o título e o preenchimento (cover/contain). Coleta de votos
do TikTok (`scraper`/`vote_parser`) e publicação (`publisher`) ainda não
implementados — ver `SPEC.md`.

---

## Estado em JSON

Tudo o que o app precisa vive em `backend/data/estado.json`:

```json
{
  "memes":      [ { "id": 1, "nome": "...", "youtube_url": "...", "inicio": 0, "fim": 10, "tags": [], "status": "ativo" } ],
  "tournaments":[ { "id": 1, "nome": "Temporada 1", "temporada": "1", "seed": 42, "tamanho": 8, "status": "em_andamento", "criado_em": "..." } ],
  "matches":    [ { "id": 1, "tournament_id": 1, "round": 1, "posicao": 0, "meme_a_id": 4, "meme_b_id": 2, "winner_id": null, "status": "pendente", "votos_a": 0, "votos_b": 0 } ],
  "votes":      []
}
```

O catálogo editável em `backend/data/memes.json` alimenta o estado via `seed` (insere
novos memes e atualiza os existentes por nome).

---

## Requisitos

- **Python 3.11+**
- **Node.js 20+** (com `npm`)
- Não é preciso instalar `ffmpeg` no sistema: o `imageio-ffmpeg` traz um binário embutido.
  (Se houver um `ffmpeg` no PATH, ele é usado.)

### Recursos de mídia esperados

| Caminho | Para quê |
| --- | --- |
| `videos/abertura.mp4` | Intro (vertical 1080x1920) concatenada no início do vídeo |
| `assets/modulra.png` | Moldura 9:16 com espaço para título e para o meme |
| `assets/fonts/Dream MMA.ttf` | Fonte de display do título (empacotada; ver `assets/fonts/LEIA-ME.txt`) |
| `C:\Windows\Fonts\arial.ttf` | Fonte usada fora do título |

A geometria da montagem (área do vídeo na moldura, preenchimento) fica em
`backend/data/layout.json`, editável no **editor desktop** (veja abaixo) — sem o
arquivo, valem os valores padrão (área 11%–89% × 25%–81%, preenchimento por
recorte central).

---

## Backend (pipeline em CLI)

Todos os comandos abaixo rodam a partir da pasta `backend`.

### 1. Criar o ambiente e instalar dependências

```powershell
cd backend

# crie o venv uma única vez
py -3.11 -m venv .venv

# ative (opcional) ou chame o python do venv direto
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Se o venv já existir, pule a criação e só rode `pip install -r requirements.txt`.

### 2. Popular o catálogo e criar um torneio

```powershell
# lê backend/data/memes.json e grava no estado (ignora memes já existentes)
.\.venv\Scripts\python.exe -m app.cli seed

# cria a temporada com todos os memes ativos
.\.venv\Scripts\python.exe -m app.cli torneio --nome "Temporada 1" --temporada 1

# lista temporadas e mostra o chaveamento
.\.venv\Scripts\python.exe -m app.cli torneios
.\.venv\Scripts\python.exe -m app.cli mostrar --torneio 1
```

O comando `torneio` aceita `--seed` (sorteio reprodutível) e `--ids` (lista explícita
de memes). Sem `--seed`, um valor aleatório é usado.

Os IDs de confronto aparecem na saída de `mostrar` (coluna `id`).

### 3. Definir um vencedor e propagar na chave

```powershell
.\.venv\Scripts\python.exe -m app.cli vencedor --match 2 --winner 5
```

### 4. Montar o vídeo de um confronto

**Via CLI integrada** (baixa os trechos, normaliza e monta):

```powershell
.\.venv\Scripts\python.exe -m app.cli montar --match 1
# grava backend/media/clips/match_1.mp4 e imprime o caminho
```

**Serviços avulsos** (úteis para testar sem o estado):

```powershell
cd backend

# baixa + normaliza um meme (usa cache se já existir)
.\.venv\Scripts\python.exe -m app.services.downloader --id 1
.\.venv\Scripts\python.exe -m app.services.downloader --id 2 --forcar   # ignora cache

# monta a batalha (abertura + moldura) e imprime o caminho do vídeo
.\.venv\Scripts\python.exe -m app.services.assembler --a 1 --b 2
# flags: --sem-abertura  --sem-moldura  --sem-encerramento  --saida "caminho\saida.mp4"
```

Arquivos gerados (git-ignored):

- `backend/media/raw/meme_{id}.mp4` — trecho bruto baixado
- `backend/media/clips/clip_meme_{id}.mp4` — clipe normalizado 1080x1920
- `backend/media/clips/match_{id}.mp4` — vídeo final do confronto
- `tmp/batalha_{a}_{b}.mp4` — vídeo final gerado pelo assembler avulso

### Comandos da CLI

| Comando | Descrição |
| --- | --- |
| `seed` | Carrega `data/memes.json` no estado |
| `memes` | Lista os memes |
| `torneio --nome ...` | Cria torneio (sorteia as chaves) |
| `torneios` | Lista temporadas |
| `mostrar --torneio N` | Mostra o chaveamento |
| `vencedor --match N --winner M` | Define vencedor e propaga |
| `montar --match N` | Baixa, normaliza e monta o vídeo |
| `editor` | Abre o editor visual desktop |

---

## Editor visual (desktop)

Ajusta a montagem com preview ao vivo, sem mexer no código:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.cli editor
```

A janela (Tkinter + Pillow) tem:

- **preview 9:16** com a moldura, a área do vídeo **arrastável** (alças nos
  cantos/bordas), o título desenhado com a fonte real (Dream MMA, gradiente +
  contorno) e a **faixa amarela do título** (arraste na vertical para subir/descer);
- **título editável** por lado (A/B) — o texto vira `titulo_a`/`titulo_b` do
  confronto em `estado.json`; vazio = nome do meme;
- **enquadramento do título**: posição Y (%), largura da faixa (%) e tamanho da
  fonte — **automático** (mede a largura real na fonte e encolhe/ quebra em duas
  linhas até caber, sem estourar a margem) ou **manual** (px fixo);
- **preenchimento** do clipe na área: `cover` (corta as bordas) ou `contain`
  (barras pretas, nada é cortado);
- campos numéricos da área (X/Y/Largura/Altura em %) sincronizados com o arraste;
- botões **Salvar** (grava o layout global em `data/layout.json` e os títulos no
  confronto), **Restaurar padrão**, **Baixar clipes p/ preview**,
  **Frame exato (ffmpeg)** (renderiza um quadro 1080x1920 idêntico ao vídeo) e
  **Gerar vídeo** (monta o mp4 do confronto em `media/clips/match_N.mp4`).

Os dois botões que acessam a rede (**Baixar clipes p/ preview** e **Gerar
vídeo**) pedem **confirmação antes de baixar**: uma janela lista os memes do
confronto, o link de origem e o trecho (`inicio–fim`) que será baixado. Durante o
download a barra de progresso mostra o **percentual real** (frações do yt-dlp por
clipe, com ~85% para o download e ~15% para a normalização); na montagem, sem
percentual previsível, a barra vira **animada** até concluir. Os clipes já
baixados são reaproveitados (cache), e uma confirmação cancelada não baixa nada.

O preview é instantâneo (PIL); use "Frame exato" para conferir a fidelidade
(fonte, sombra, recorte) antes de gerar o vídeo. O `layout.json` passa a valer
para todo o pipeline — inclusive o `montar` da CLI.

## Frontend (site estático)

O site é **estático**: o build lê `backend/data/estado.json` e pré-renderiza as
páginas. Não há servidor de aplicação em tempo de execução.

```powershell
cd frontend
npm install
npm run dev        # desenvolvimento: http://localhost:3000
npm run build      # gera o site estático em frontend/out/
```

Para publicar, sirva a pasta `frontend/out/` em qualquer host estático (ou
`npx serve out`). Sempre que o estado mudar, rode `npm run build` de novo.

### Publicação no GitHub Pages

O site é publicado em **https://ltmleo.github.io/batalha-de-memes/** pelo workflow
de `/.github/workflows/deploy.yml` a cada push na `master`:

- o job do Actions roda `npm ci` + `npm run build` em `frontend/` e envia a pasta
  `frontend/out/` para o GitHub Pages (via artefato);
- o `basePath` em `frontend/next.config.mjs` é `/batalha-de-memes` (slug do
  repositório), então todos os links e assets são gerados com esse prefixo.

Ative uma única vez: **Settings → Pages → Source: "GitHub Actions"** (a partir do
primeiro push o workflow já publica sozinho).

Preview local com a mesma estrutura de URL do Pages:

```powershell
cd frontend
npm run build
npm run preview   # http://localhost:8138/batalha-de-memes/
```

> O prefixo `/batalha-de-memes/` vem do nome do repositório. Se o repositório
> mudar de nome, atualize também o `basePath` em `next.config.mjs`.

Se o JSON estiver em outro caminho, defina `ESTADO_JSON` no ambiente antes do build:

```powershell
$env:ESTADO_JSON = "C:\caminho\para\estado.json"; npm run build
```

---

## Estrutura do projeto

```
batalha-de-memes/
  assets/modulra.png        # moldura usada na montagem
  videos/abertura.mp4       # intro
  backend/
    app/
      cli.py                # CLI do pipeline (seed, torneio, vencedor, montar, editor...)
      config.py             # caminhos (estado, mídia, moldura, fontes, layout, tmp)
      layout.py             # geometria da montagem (data/layout.json)
      titulo.py             # título: fonte de meme, gradiente, quebra de linha
      store.py              # lê/grava data/estado.json (fonte única da verdade)
      editor/
        app.py              # editor visual desktop (Tkinter)
        preview.py          # preview PIL + frame exato (ffmpeg)
      services/
        catalog.py          # lê data/memes.json  -> estado
        bracket.py          # sorteio das chaves + propagação do vencedor
        downloader.py       # yt-dlp + normalização 9:16   (CLI: --id)
        assembler.py        # ffmpeg: abertura + moldura + título (CLI: --a --b)
    data/
      memes.json            # catálogo editável (entrada do seed)
      estado.json           # estado da aplicação (fonte única da verdade)
      layout.json           # layout da montagem (criado ao salvar no editor)
    media/                  # cache de clipes (git-ignored)
    requirements.txt
  frontend/                 # Next.js (App Router) com output: "export"
    lib/estado.ts           # lê data/estado.json em tempo de build
    out/                    # site estático gerado (git-ignored)
  tmp/                      # saída temporária (git-ignored)
  SPEC.md                   # especificação e roadmap
```

---

## Como o vídeo final é montado

Cada clipe é exibido em tela cheia, em sequência: **abertura → meme A → meme B**.
Sobre cada clipe aplica-se a moldura (`assets/modulra.png`) com:

- o clipe preenchendo a área do "telão" definida em `backend/data/layout.json`
  (padrão: 11%–89% da largura × 25%–81% da altura) em `cover` (recorte central:
  ocupa todo o espaço, mesmo cortando as bordas) ou `contain` (encaixa e completa
  com barras pretas) — sem fundo desfocado;
- o título centralizado (padrão: centro a 18% da altura) com a fonte de display
  **Dream MMA** (caixa-alta, **gradiente dourado + contorno preto**), renderizado
  em PNG e sobreposto. O tamanho é automático: mede a largura **na fonte real** e,
  se ficaria pequeno demais numa linha, **quebra em até duas linhas** — nomes
  longos não estouram a margem. O texto é o `titulo_a`/`titulo_b` do confronto
  (quando definido no editor) ou o nome do meme;
- o áudio original de cada clipe.

Reescalas usam `flags=lanczos` para manter a nitidez (sem aspecto "borrado").

O layout (área + preenchimento + enquadramento do título) é editável no editor
desktop e fica em `backend/data/layout.json`; o estilo do título (fonte, cores,
contorno, quebra de linha) fica em `backend/app/titulo.py` e os caminhos em
`backend/app/config.py`.

---

## Problemas comuns

- **`yt-dlp` não encontra o ffmpeg:** o downloader cria um atalho do binário do
  `imageio-ffmpeg` em `backend/media/tools/` e o injeta no PATH automaticamente.
  Se faltar, rode `pip install imageio-ffmpeg`.
- **Título sem acento / com letra faltando:** a fonte de meme (Dream MMA) não tem
  acentos; o título converte acentos para a letra-base (á→a, ç→c), exceto `:` e
  `.`. Para voltar a uma fonte com acentos, troque `FONTE_TITULO_PATH` em
  `backend/app/config.py` (e o tratamento em `backend/app/titulo.py`).
- **Editor não abre / erro de Tkinter:** rode `pip install -r requirements.txt`
  (traz o `Pillow`); o Tkinter já vem no Python oficial do Windows.
- **Moldura/título fora de lugar:** abra `python -m app.cli editor` e ajuste a área
  (o "telão" e o preenchimento cover/contain viram `data/layout.json`).
- **Título estourando a margem:** no editor, reduza a **Largura (%)** da faixa,
  desça/ajuste a **Posição Y** ou defina um **tamanho manual** de fonte; o
  automático já encolhe para caber.
- **Site vazio / temporada antiga:** o site lê o JSON no **build**. Rode `seed` e
  `torneio` na CLI e refaça `npm run build` em `frontend/`.
- **Download falha / vídeo indisponível:** verifique `youtube_url`, `inicio`/`fim`
  (em segundos) em `backend/data/estado.json` (ou no catálogo `memes.json`).
