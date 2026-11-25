"""Entrada de produção: `uvicorn api.asgi:app` (dataset em COPA_DATASET_PATH)."""
from .main import create_app

app = create_app()
