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
MOLDURA_PATH = ASSETS_DIR / "moldura2.png"
FONTE_PATH = Path("C:/Windows/Fonts/arial.ttf")
# Fonte de display do título (empacotada no repo; ver assets/fonts/LEIA-ME.txt)
FONTE_TITULO_PATH = ASSETS_DIR / "fonts" / "Dream MMA.ttf"

# Estado da aplicação (fonte única da verdade) e catálogo de entrada
CAMINHO_ESTADO = DATA_DIR / "estado.json"
CAMINHO_CATALOGO = DATA_DIR / "memes.json"

# Layout da montagem (área do vídeo na moldura, preenchimento) — editável no editor
CAMINHO_LAYOUT = DATA_DIR / "layout.json"

for _dir in (DATA_DIR, MEDIA_DIR, RAW_DIR, CLIPS_DIR, TMP_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
