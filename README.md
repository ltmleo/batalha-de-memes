# Batalha de Memes

Automatiza a produção de vídeos de "batalha de memes" para o TikTok: dois clipes de
meme se enfrentam, o público vota nos comentários e o vencedor avança no chaveamento.

- **Backend/worker:** Python 3.11 + FastAPI + SQLAlchemy (SQLite).
- **Download/edição:** `yt-dlp` + `ffmpeg` (binário embutido via `imageio-ffmpeg`).
- **Site:** Next.js (lista de temporadas + chaveamento).

Status atual: catálogo, chaveamento e API prontos; `downloader.py` e `assembler.py`
já geram um vídeo de confronto (abertura + moldura + título + clipes). Coleta de votos
do TikTok (`scraper`/`vote_parser`) e publicação (`publisher`) ainda não implementados —
ver `SPEC.md`.

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
| `C:\Windows\Fonts\arial.ttf` e `arialbd.ttf` | Fonte dos textos (título usa Arial Bold) |

---

## Backend (API + pipeline)

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

### 2. Subir a API

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Documentação interativa (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health

O banco SQLite (`backend/batalha.db`) e as pastas de mídia são criados automaticamente.

### 3. Popular o catálogo e criar um torneio

Em outro terminal (PowerShell):

```powershell
# lê backend/data/memes.json e insere os memes no banco (ignora duplicados)
Invoke-RestMethod -Method Post http://localhost:8000/memes/seed

# cria a temporada com todos os memes ativos
Invoke-RestMethod -Method Post http://localhost:8000/tournaments `
  -ContentType "application/json" `
  -Body '{"nome":"Temporada 1","temporada":"1"}'
```

O `POST /tournaments` aceita também `seed` (sorteio reprodutível) e `meme_ids`
(lista explícita). Sem `seed`, um valor aleatório é usado.

### 4. Montar o vídeo de um confronto

Os IDs de confronto aparecem em `GET /tournaments/{id}` (campo `matches[].id`).

**Via API** (baixa os trechos, normaliza e monta):

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/matches/1/montar
# grava backend/media/clips/match_1.mp4 e retorna video_path
```

**Via linha de comando** (útil para testar sem subir a API):

```powershell
cd backend

# baixa + normaliza um meme (usa cache se já existir)
.\.venv\Scripts\python.exe -m app.services.downloader --id 1
.\.venv\Scripts\python.exe -m app.services.downloader --id 2 --forcar   # ignora cache

# monta a batalha (abertura + moldura) e imprime o caminho do vídeo
.\.venv\Scripts\python.exe -m app.services.assembler --a 1 --b 2
# flags: --sem-abertura  --sem-moldura  --saida "caminho\saida.mp4"
```

Arquivos gerados (git-ignored):

- `backend/media/raw/meme_{id}.mp4` — trecho bruto baixado
- `backend/media/clips/clip_meme_{id}.mp4` — clipe normalizado 1080x1920
- `backend/media/clips/match_{id}.mp4` — vídeo final do confronto (via API)
- `tmp/batalha_{a}_{b}.mp4` — vídeo final gerado pela CLI

### Endpoints da API

| Método | Rota | Descrição |
| --- | --- | --- |
| GET | `/health` | Status |
| GET | `/memes` | Lista memes |
| POST | `/memes` | Cria meme |
| POST | `/memes/seed` | Carrega `data/memes.json` |
| GET | `/tournaments` | Lista temporadas |
| POST | `/tournaments` | Cria torneio (sorteia as chaves) |
| GET | `/tournaments/{id}` | Detalhe (memes + matches) |
| GET | `/matches` | Lista confrontos (`?tournament_id=`) |
| GET | `/matches/{id}` | Detalhe do confronto |
| POST | `/matches/{id}/vencedor` | Define vencedor e propaga (`{"winner_id": N}`) |
| POST | `/matches/{id}/montar` | Baixa, normaliza e monta o vídeo |

---

## Frontend (site)

```powershell
cd frontend
npm install
npm run dev
```

- Site: http://localhost:3000
- Página inicial: lista de temporadas
- `/torneio/[id]`: chaveamento visual

Por padrão o site consome a API em `http://localhost:8000`. Para apontar para outro
endereço, crie `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Build de produção:

```powershell
npm run build
npm run start
```

---

## Estrutura do projeto

```
batalha-de-memes/
  assets/modulra.png        # moldura usada na montagem
  videos/abertura.mp4       # intro
  backend/
    app/
      main.py               # FastAPI (CORS para localhost:3000)
      config.py             # caminhos (mídia, moldura, fontes, tmp)
      db.py models.py schemas.py
      routers/              # memes, tournaments, matches
      services/
        catalog.py          # lê data/memes.json
        bracket.py          # sorteio das chaves + propagação do vencedor
        downloader.py       # yt-dlp + normalização 9:16   (CLI: --id)
        assembler.py        # ffmpeg: abertura + moldura + título (CLI: --a --b)
    data/memes.json         # catálogo
    media/                  # cache de clipes (git-ignored)
    requirements.txt
  frontend/                 # Next.js (App Router)
  tmp/                      # saída temporária (git-ignored)
  SPEC.md                   # especificação e roadmap
```

---

## Como o vídeo final é montado

Cada clipe é exibido em tela cheia, em sequência: **abertura → meme A → meme B**.
Sobre cada clipe aplica-se a moldura (`assets/modulra.png`) com:

- o clipe encaixado na área do "telão" (11%–89% da largura × 25%–81% da altura);
- o nome do meme como título centralizado (faixa 13%–23%), em Arial Bold, com o
  tamanho ajustado automaticamente para preencher a área;
- o áudio original de cada clipe.

Parâmetros ficam em `backend/app/services/assembler.py` (constantes `MEME_*` e
`TITULO_*`) e os caminhos em `backend/app/config.py`.

---

## Problemas comuns

- **`yt-dlp` não encontra o ffmpeg:** o downloader cria um atalho do binário do
  `imageio-ffmpeg` em `backend/media/tools/` e o injeta no PATH automaticamente.
  Se faltar, rode `pip install imageio-ffmpeg`.
- **Título com acento errado / quadrado:** confira que `arial.ttf` e `arialbd.ttf`
  existem em `C:\Windows\Fonts`.
- **Site mostra "Não foi possível falar com a API":** o backend não está rodando em
  `http://localhost:8000` (ou ajuste `NEXT_PUBLIC_API_URL`).
- **CORS:** a API libera apenas `http://localhost:3000` (ajuste em
  `backend/app/main.py` se mudar a porta do site).
- **Download falha / vídeo indisponível:** verifique `youtube_url`, `inicio`/`fim`
  (em segundos) em `backend/data/memes.json`.
