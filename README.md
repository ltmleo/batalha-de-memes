# Batalha de Memes

Automatiza a produção de vídeos de "batalha de memes" para o TikTok: dois clipes de
meme se enfrentam, o público vota nos comentários e o vencedor avança no chaveamento.

- **Backend/worker:** Python 3.11, sem servidor. O pipeline lê e grava o estado em
  `backend/data/estado.json` (fonte única da verdade — sem banco, sem API).
- **Download/edição:** `yt-dlp` + `ffmpeg` (binário embutido via `imageio-ffmpeg`).
- **Site:** Next.js em **export estático** (`output: "export"`): o build lê
  `data/estado.json` e gera HTML/CSS/JS puros em `frontend/out/`.

Status atual: catálogo, chaveamento, montagem de vídeo (com **kit procedural**:
gancho, selos, CTA, encerramento personalizado e capa — sem IA), editor desktop,
**apuração de votos por arquivo de comentários** (`apurar`), montagem da rodada em
lote com pacote de publicação (`rodada`) e página de cada confronto no site.
Ainda não implementados: coleta automática dos comentários do TikTok (`scraper`)
e upload pela API oficial (`publisher`) — ver `SPEC.md`.

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

O catálogo editável é dividido por temporada em `backend/data/memes/temporada-N.json`
e alimenta o estado via `seed` (insere novos memes e atualiza os existentes por nome).

---

## Requisitos

- **Python 3.11+**
- **Node.js 20+** (com `npm`)
- Não é preciso instalar `ffmpeg` no sistema: o `imageio-ffmpeg` traz um binário embutido.
  (Se houver um `ffmpeg` no PATH, ele é usado.)

### Recursos de mídia esperados

| Caminho | Para quê |
| --- | --- |
| `videos/abertura.mp4` | Vinheta da marca (vertical 1080x1920) — fora da sequência padrão; inclua `"abertura"` em `data/roteiro.json` para usar |
| `videos/versus.mp4` | Transição "VS" (vertical 1080x1920) em tela cheia, **entre** o clipe A e o clipe B (sem moldura, sem título) |
| `videos/encerramento.mp4` | Encerramento "Quem ganha?" (vertical 1080x1920); o kit encaixa fotos e nomes dos memes nos painéis MEME 1/MEME 2 |
| `assets/moldura2.png` | Moldura 9:16 com **janela transparente** — o clipe aparece por trás dela |
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
# lê backend/data/memes/*.json e grava no estado (ignora memes já existentes)
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

# monta a batalha (abertura + moldura + VS) e imprime o caminho do vídeo
.\.venv\Scripts\python.exe -m app.services.assembler --a 1 --b 2
# flags: --sem-abertura  --sem-moldura  --sem-encerramento  --sem-versus  --saida "caminho\saida.mp4"
```

Arquivos gerados (git-ignored):

- `backend/media/raw/meme_{id}.mp4` — trecho bruto baixado
- `backend/media/clips/clip_meme_{id}.mp4` — clipe normalizado 1080x1920
- `backend/media/clips/match_{id}.mp4` — vídeo final do confronto
- `tmp/batalha_{a}_{b}.mp4` — vídeo final gerado pelo assembler avulso

### Comandos da CLI

| Comando | Descrição |
| --- | --- |
| `seed` | Carrega `data/memes/*.json` no estado |
| `memes` | Lista os memes |
| `torneio --nome ...` | Cria torneio (sorteia as chaves) |
| `torneios` | Lista temporadas |
| `mostrar --torneio N` | Mostra o chaveamento |
| `vencedor --match N --winner M` | Define vencedor e propaga |
| `montar --match N` | Baixa, normaliza e monta o vídeo |
| `painel` | Abre o painel de duelos (gerar, publicar e apurar a rodada) |
| `editor [--match N]` | Abre o editor visual desktop (opcionalmente já num confronto) |
| `rodada --torneio N` | Monta todos os confrontos da rodada atual e gera o pacote de publicação |
| `publicar --match N --tiktok URL [--horas 48]` | Grava links, `publicado_em` e o prazo (`deadline`) da votação |
| `apurar --match N --arquivo ARQ [--definir-vencedor]` | Conta os votos de um `.txt`/`.csv`/`.json` de comentários |
| `status` | Próxima ação (montar / publicar / apurar) de cada confronto da rodada |
| `legenda --match N` | Imprime a legenda pronta (texto, prazo, link e hashtags) |
| `doctor` | Checa Python, ffmpeg, idade do yt-dlp, assets e dados |
| `validar [--so-erros]` | Valida catálogo e estado (usado no CI) |
| `prebaixar [--ids ...]` | Baixa/normaliza os clipes de todos os memes ativos (acha links quebrados cedo) |
| `video --match N --tiktok URL ...` | Só grava os links de um confronto |

### Ciclo de uma rodada

```powershell
.\.venv\Scripts\python.exe -m app.cli rodada --torneio 1
# -> media/publicar/torneio_1_rodada_R/: match_N.mp4, match_N_capa.png,
#    match_N_legenda.txt e manifest.json (suba os vídeos no TikTok/Reels/Shorts)
.\.venv\Scripts\python.exe -m app.cli publicar --match 5 --tiktok https://www.tiktok.com/@.../video/...
# ...prazo encerrado: exporte/cole os comentários num arquivo
.\.venv\Scripts\python.exe -m app.cli apurar --match 5 --arquivo comentarios.txt --definir-vencedor
.\.venv\Scripts\python.exe -m app.cli status
```

Formato do `.txt` de comentários: uma linha por comentário, `usuario: texto`.
Votos válidos: comentário que é só `A`/`B`/`1`/`2`, frases como "voto no A",
"time B", 🅰️/🅱️ ou o nome do meme; um voto por usuário (o primeiro válido), só
dentro do prazo. Empate é desfeito pelo `seed` do torneio. O bruto fica em
`data/raw/` (git-ignored); o `estado.json` guarda só os votos válidos, sem texto.

### Testes e lint

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests
```

O CI (`.github/workflows/deploy.yml`) roda testes, lint, `validar` e `tsc` antes
de publicar o site.

---

## Painel de duelos (desktop)

A tela do dia a dia: **dê dois cliques em `painel.bat`** na raiz do repositório
(ou rode `python -m app.cli painel` em `backend/`).

- escolha o **torneio** e a **rodada** (abre na rodada em andamento); a lista
  mostra cada confronto com a situação — *a gerar*, *pronto p/ publicar*,
  *em votação* (com prazo), *apurar agora* (prazo vencido) ou o vencedor —,
  duração (fundo laranja se passar do limite do `roteiro.json`) e placar;
- **Gerar vídeo dos selecionados** (Ctrl/Shift para vários) ou **Gerar a rodada**
  (todos os pendentes): fila em segundo plano com barra de progresso e log; uma
  falha não para a fila e **Cancelar fila** para depois do vídeo atual;
- **Prévia da capa** gera só o kit (gancho + capa, ~6 s) para conferir antes de
  renderizar; **Ajustar no editor…** abre o editor de montagem já no confronto
  (salve lá e aperte **F5** no painel);
- **Abrir vídeo** (ou duplo clique na linha) e **Copiar legenda**;
- **Publicar…** grava os links (TikTok/Reels/Shorts) e o prazo da votação, e
  copia a legenda;
- **Apurar comentários…** lê o arquivo `.txt/.csv/.json`, mostra o placar e
  oferece definir o vencedor; **Vencedor: A/B** define na mão;
- **Pacote da rodada** junta vídeos, capas, legendas e `manifest.json` numa pasta
  e a abre.

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
- botões **Salvar e gerar vídeo** (grava o layout global em `data/layout.json` e os
  títulos no confronto **e já monta o mp4** do confronto em
  `media/clips/match_N.mp4`), **Salvar só o layout** (grava sem gerar), **Restaurar
  padrão**, **Baixar clipes p/ preview** e **Frame exato (ffmpeg)** (renderiza um
  quadro 1080x1920 idêntico ao vídeo);
- quadro **Dados (json)**: **Sincronizar catálogo (seed)** copia
  `data/memes/*.json` → `estado.json` (mesmo efeito do `seed` da CLI, sem sair do
  editor) e **Recarregar do disco** relê `estado.json`/`layout.json` descartando
  edições não salvas.

⚠️ O editor lê o **`estado.json`**, não os arquivos de temporada. Se você editar
o catálogo (`data/memes/*.json`), clique em **Sincronizar catálogo (seed)** para
ver a mudança no editor.

Os botões que geram vídeo (**Salvar e gerar vídeo**) e que baixam para o preview
(**Baixar clipes p/ preview**) pedem **confirmação antes de baixar**: uma janela
lista os memes do confronto, o link de origem e o trecho (`inicio–fim`) que será
baixado. Ao confirmar, o layout/título já foi salvo, então cancelar a geração não
perde as edições. Durante o download a barra de progresso mostra o **percentual
real** (frações do yt-dlp por clipe, com ~85% para o download e ~15% para a
normalização) e vai até **50%**; na **renderização** ela continua **determinada**
(0→100%, lendo o `-progress` do ffmpeg) e sobe de 50% a 100% — como renderizar um
confronto leva alguns minutos, dá para acompanhar o andamento em vez de parecer
travado. Os clipes já baixados são reaproveitados (cache), e uma confirmação
cancelada não baixa nada.
O cache é **invalidado automaticamente** quando o `youtube_url`/`inicio`/`fim` do
meme muda (uma assinatura do trecho é gravada ao lado do clipe), então editar o
trecho e baixar de novo já traz o vídeo novo.

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
  assets/moldura2.png       # moldura usada na montagem (janela transparente)
  assets/fonts/             # Dream MMA (título e kit)
  assets/_rascunhos/        # artes não usadas (git-ignored, só local)
  videos/                   # abertura, versus, encerramento (1080x1920)
  backend/
    app/
      cli.py                # CLI do pipeline (seed, torneio, rodada, apurar, status, doctor...)
      config.py             # caminhos (estado, mídia, moldura, fontes, layout, roteiro, tmp)
      layout.py             # geometria da montagem (data/layout.json)
      roteiro.py            # sequência/transições/áudio/encode (data/roteiro.json)
      titulo.py             # título: fonte de meme, gradiente, quebra de linha
      store.py              # lê/grava data/estado.json (gravação atômica)
      editor/               # painel de duelos + editor de montagem (Tkinter)
      services/
        catalog.py          # lê data/memes/*.json -> estado
        bracket.py          # sorteio das chaves + propagação do vencedor
        downloader.py       # yt-dlp + normalização 9:16   (CLI: --id)
        midia.py            # utilitários ffmpeg (duração, áudio, quadro)
        kit.py              # kit procedural: gancho, capa, selos, CTA, encerramento
        assembler.py        # ffmpeg: segmentos + transições + loudnorm (CLI: --a --b)
        vote_parser.py      # apuração A vs B a partir de comentários
        publicacao.py       # legenda + pacote/manifest da rodada
        validacao.py        # validação de catálogo e estado
    tests/                  # pytest (bracket, votos, layout/roteiro, grafo do ffmpeg)
    data/
      memes/                # catálogo editável por temporada (entrada do seed)
      estado.json           # estado da aplicação (fonte única da verdade)
      layout.json           # layout da montagem (criado ao salvar no editor)
      roteiro.json          # roteiro do vídeo (editável à mão)
      raw/                  # comentários brutos e apurações (git-ignored)
    media/                  # cache de clipes, vídeos e pacotes de publicação (git-ignored)
    requirements.txt / requirements-dev.txt / pyproject.toml
  frontend/                 # Next.js (App Router) com output: "export"
    app/match/[id]/         # página do confronto (link da bio/legenda)
    lib/estado.ts           # lê data/estado.json em tempo de build
    public/capas/           # capas dos confrontos (geradas pelo pipeline, versionadas)
    out/                    # site estático gerado (git-ignored)
  tmp/                      # saída temporária e cache do kit (git-ignored)
  SPEC.md                   # especificação e roadmap
```

---

## Como o vídeo final é montado

A sequência vem de `backend/data/roteiro.json` (padrão:
**gancho → meme A → versus → meme B → encerramento**), com transição `fade` de
0,25 s entre os segmentos (`xfade`/`acrossfade`; `"transicao": "corte"` volta ao
corte seco). Segmentos cujo arquivo não existe são pulados.

### Kit procedural (`app/services/kit.py`, sem IA)

Gerado por confronto com PIL + ffmpeg e cacheado em `tmp/kit/<hash>/`:

| Asset | O que é |
| --- | --- |
| `gancho.mp4` | 1,6 s: os dois memes entram pelos lados, o "VS" bate no centro (flash + tremida), fase/jogo no topo, "QUEM VENCE / COMENTE A OU B" embaixo; whoosh + impacto **sintetizados** no ffmpeg |
| `capa.png` | Último quadro do gancho — capa do TikTok/Reels; copiada para `frontend/public/capas/` (página do confronto e `og:image`) |
| `selo_a/b.png` | Badge A/B no canto do telão durante cada meme |
| `cta_a/b.png` | Faixa "COMENTE A/B" nos últimos `cta_segundos` de cada meme |
| `encerramento.png` | Fotos e nomes dos memes nos painéis do `encerramento.mp4` (geometria em `roteiro.json` → `encerramento`) |

Para conferir o visual sem renderizar o vídeo: `python -m app.services.kit --match N`.

### Composição dos memes

- a moldura (`assets/moldura2.png`) tem **janela transparente**: o clipe é
  composto por trás dela, na área de `data/layout.json` (editor desktop), em
  `cover` (recorte central) ou `contain` (barras pretas);
- título com a fonte **Dream MMA** (gradiente dourado + contorno), tamanho
  automático com quebra em até duas linhas (`app/titulo.py`);
- áudio dos memes normalizado a **-14 LUFS** (`loudnorm`), então um meme não
  estoura enquanto o outro some;
- barra de progresso dourada no topo do vídeo inteiro (retenção).

Encode: H.264 high, `crf 18`, `preset medium`, GOP 2 s, AAC 192k, `+faststart`
(ajustáveis em `roteiro.json`). O `montar_match` grava `video_path`, `capa_path`
e `duracao` no confronto e avisa se passar de `duracao_max` (60 s).

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
  (em segundos) em `backend/data/estado.json` (ou no catálogo `data/memes/*.json`).
