"""
x-69 Wormdemon — Lokal/Termux backend
Aynı kodu paylaşır: api/index.py
"""
import os
import sys
from pathlib import Path

# api/index.py'i import et
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from api.index import app  # noqa: E402

# uvicorn server:app --host 0.0.0.0 --port 8001 ile çalışır
