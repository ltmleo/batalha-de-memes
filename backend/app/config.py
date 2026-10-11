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
MOLDURA_PATH = ASSETS_DIR / "modulra.png"
FONTE_PATH = Path("C:/Windows/Fonts/arial.ttf")
FONTE_TITULO_PATH = Path("C:/Windows/Fonts/arialbd.ttf")

DATABASE_URL = f"sqlite:///{(BASE_DIR / 'batalha.db').as_posix()}"
CAMINHO_CATALOGO = DATA_DIR / "memes.json"

for _dir in (DATA_DIR, MEDIA_DIR, RAW_DIR, CLIPS_DIR, TMP_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
