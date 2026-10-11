# Especificação — Batalha de Memes

Aplicação para automatizar a criação de vídeos de "batalha de memes" para o TikTok:
dois clipes de meme do YouTube se enfrentam, o público vota nos comentários e um
vencedor avança no chaveamento.

## Decisões
- **Votação:** TikTok (comentários via scraping).
- **Origem dos clipes:** download do YouTube (fair use).
- **Estado:** JSON único (`backend/data/estado.json`) — sem banco de dados e sem API.
- **Stack:** Python (pipeline/CLI) + Next.js em export estático (site).

## Fluxo
```
Catálogo → Sorteio das chaves → Download+recorte → Montagem → Publicação
   ↑                                                              ↓
   └──────────── próxima rodada ← Vencedor ← Contagem de votos ←──┘
```

## Stack
- **Backend / worker:** Python 3.11, sem servidor. O estado é lido/gravado em
  `data/estado.json`; a CLI (`app.cli`) orquestra o pipeline.
- **Download/edição:** `yt-dlp` + `ffmpeg` (CLI).
- **Coleta TikTok:** Playwright (headless) + fallback no endpoint interno de comentários.
- **Site:** Next.js com `output: "export"` — lê o JSON em tempo de build e gera HTML/CSS/JS.

## Estrutura
```
batalha-de-memes/
  backend/
    app/
      cli.py             # pipeline: seed, torneio, vencedor, montar...
      store.py           # lê/grava data/estado.json (fonte única da verdade)
      config.py          # caminhos (estado, mídia, moldura, fontes, tmp)
      services/
        catalog.py       # lê data/memes.json -> estado
        bracket.py       # sorteio das chaves + propagação
        downloader.py    # yt-dlp + crop 9:16
        assembler.py     # ffmpeg (montagem)
        scraper.py       # comentários TikTok        (a implementar)
        vote_parser.py   # apuração A vs B            (a implementar)
        publisher.py     # upload/publicação          (a implementar)
      workers/pipeline.py
    data/
      memes.json         # catálogo editável (entrada do seed)
      estado.json        # estado da aplicação (fonte única da verdade)
    media/               # cache de clipes (git-ignored)
    requirements.txt
  frontend/              # Next.js (export estático)
```

## Modelo de dados
Persistidos como listas de objetos em `backend/data/estado.json`:
```
Memes[]      Meme{id, nome, youtube_url, inicio, fim, autor_fonte, tags[], status}
Tournaments[] Tournament{id, nome, temporada, seed, tamanho, status, criado_em}
Matches[]    Match{id, tournament_id, round, posicao, meme_a_id, meme_b_id,
                   video_path, tiktok_url, publicado_em, deadline, status,
                   votos_a, votos_b, winner_id}
Votes[]      Vote{id, match_id, user_hash, raw_comment, escolha(A|B), valido, criado_em}
```
`user_hash` = hash do autor do comentário (dedupe sem guardar dado pessoal).
`inicio`/`fim` são em **segundos**.

## 1. Download (yt-dlp)
```powershell
yt-dlp -f "bv*[height<=1080]+ba/b" --download-sections "*HH:MM:SS-HH:MM:SS" `
  --force-keyframes-at-cuts --merge-output-format mp4 `
  -o "media/raw/meme_{id}.mp4" "{youtube_url}"
```
Depois `ffmpeg` normaliza para 1080x1920 por **recorte central (cover/crop)** —
o vídeo preenche todo o quadro, cortando as bordas quando necessário, sem fundo
desfocado — em `media/clips/`. Trechos já baixados são cacheados.

## 2. Sorteio das chaves (`bracket.py`)
- `N` memes → potência de 2 (16/8/4). `random.Random(seed)` torna o sorteio **reprodutível**.
- Cria todos os `Match` de todas as rodadas; rodadas seguintes são preenchidas conforme apura.
- Quem não tem adversário recebe *bye* e avança automaticamente.

## 3. Montagem (`assembler.py`, ffmpeg)
Template vertical **A em cima / B embaixo** (cada um 1080x960):
```
[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,setsar=1[top];
[1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,setsar=1[bot];
[top][bot]vstack=inputs=2[base];
[base]drawtext=text='A':...[v]
```
Sobreposições: labels **A/B**, contagem, placar, CTA "Comente A ou B". Export
`1080x1920 @30fps`. Intro/outro com vencedor do confronto anterior.

## 4. Coleta e apuração de votos
- `scraper.py`: Playwright abre o vídeo público (cookies de sessão), rola e salva os
  comentários brutos em `data/raw/{match_id}.json` (auditoria; permite recontar).
- `vote_parser.py`:
  1. Normaliza (lowercaixa, remove acento).
  2. Extrai escolha por token `a`/`b`, aliases do meme ou emoji.
  3. **Um voto por `user_hash` por match** (primeiro válido).
  4. Só conta entre `publicado_em` e `deadline`.
  5. Filtra contas suspeitas (novas, sem avatar, rajadas duplicadas).
  6. Vencedor = mais votos válidos. Desempate: total de votos → `seed`.

⚠️ Sem API pública, o scraping quebra quando o TikTok muda o layout e pode sofrer
rate-limit/captcha. Mitigação: cookies de sessão, retry com backoff e JSON bruto salvo.

## 5. Publicação (`publisher.py`)
TikTok tem **Content Posting API oficial** (requer app aprovado) — caminho sancionado;
fallback: upload manual assistido. Após publicar, grava `tiktok_url` e agenda a coleta.

## 6. Site (Next.js, export estático)
- `/` lista de temporadas; `/torneio/[id]` chaveamento visual (pré-renderizado por
  `generateStaticParams`). `/match/[id]` placar (a implementar).
- O site lê `backend/data/estado.json` em **tempo de build** (`frontend/lib/estado.ts`)
  e gera HTML/CSS/JS puros em `frontend/out/`. Não há API em tempo de execução;
  após o pipeline atualizar o JSON, basta refazer o build.

## 7. Monetização
TikTok Creator Rewards (requer **10k seguidores + 100k views/30d**), brand deals,
tráfego para o site (ranking/votação) e "inscrição de memes" patrocinada.

## Riscos
- **YouTube fair use:** strike/desmonetização são reais; registrar fonte/autoria e variar fontes.
- **Scraping TikTok:** frágil e sensível a ToS; manter publicação (API oficial) separada da votação.

## Roadmap
1. `catalog.py` + `bracket.py` + CLI com chaveamento. **(feito neste scaffold)**
2. `downloader.py` + `assembler.py`: gerar um match manualmente. **(scaffold pronto)**
3. `scraper.py` + `vote_parser.py` com coleta simulada.
4. `pipeline.py` automatiza o ciclo; `publisher.py` fecha.
