from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
REPO_DIR = BASE_DIR.parent

DATA_DIR = BASE_DIR / "data"
MEDIA_DIR = BASE_DIR / "media"
RAW_DIR = MEDIA_DIR / "raw"
CLIPS_DIR = MEDIA_DIR / "clips"

# Trabalho temporário dentro do próprio repositório
TMP_DIR = REPO_DIR / "tmp"

# Recursos de vídeo do repositório
VIDEOS_DIR = REPO_DIR / "videos"
ASSETS_DIR = REPO_DIR / "assets"
ABERTURA_PATH = VIDEOS_DIR / "abertura.mp4"
ENCERRAMENTO_PATH = VIDEOS_DIR / "encerramento.mp4"
VERSUS_PATH = VIDEOS_DIR / "versus.mp4"
MOLDURA_PATH = ASSETS_DIR / "moldura2.png"
# Fonte de display do título (empacotada no repo; ver assets/fonts/LEIA-ME.txt)
FONTE_TITULO_PATH = ASSETS_DIR / "fonts" / "Dream MMA.ttf"

# Estado da aplicação (fonte única da verdade) e catálogo de entrada
CAMINHO_ESTADO = DATA_DIR / "estado.json"
# Catálogo de entrada dividido por temporada (data/memes/temporada-N.json)
CATALOGO_DIR = DATA_DIR / "memes"

# Layout da montagem (área do vídeo na moldura, preenchimento) — editável no editor
CAMINHO_LAYOUT = DATA_DIR / "layout.json"

# Roteiro do vídeo (sequência, transições, áudio, encode) — editável à mão
CAMINHO_ROTEIRO = DATA_DIR / "roteiro.json"

# Assets gerados pelo kit de vídeo (gancho, selos, capa...) — cache, git-ignored
KIT_DIR = TMP_DIR / "kit"

# Comentários brutos (entrada da apuração) e saídas para publicação
RAW_DATA_DIR = DATA_DIR / "raw"
PUBLICAR_DIR = MEDIA_DIR / "publicar"

# Capas publicadas no site (versionadas: o build do Pages precisa delas)
CAPAS_SITE_DIR = REPO_DIR / "frontend" / "public" / "capas"

for _dir in (DATA_DIR, MEDIA_DIR, RAW_DIR, CLIPS_DIR, TMP_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
