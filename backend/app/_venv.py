"""Garante que a CLI rode no Python do venv do projeto (``backend/.venv``).

Rodar ``python -m app.cli ...`` com o Python global (sem yt-dlp/Pillow) dá erros
confusos no meio do pipeline ("yt-dlp não instalado"). Se o venv existe e o
processo atual não é dele, a CLI se relança com o Python do venv, com os mesmos
argumentos. Só usa a biblioteca padrão: roda antes de qualquer dependência.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_VENV = _BACKEND / ".venv"
_GUARDA = "BATALHA_NO_VENV"


def _python_do_venv() -> Path:
    if os.name == "nt":
        # sem console (pythonw) continua sem console
        nome = "pythonw.exe" if Path(sys.executable).name.lower() == "pythonw.exe" else "python.exe"
        return _VENV / "Scripts" / nome
    return _VENV / "bin" / "python"


def garantir_venv() -> None:
    """Relança ``app.cli`` no venv quando necessário (não retorna nesse caso)."""
    python = _python_do_venv()
    if os.environ.get(_GUARDA) or not python.exists():
        return
    if Path(sys.prefix).resolve() == _VENV.resolve():
        return
    env = {**os.environ, _GUARDA: "1"}
    codigo = subprocess.call([str(python), "-m", "app.cli", *sys.argv[1:]], cwd=_BACKEND, env=env)
    sys.exit(codigo)
