# API Copa América (Issue #41)

Rodar localmente (a partir de `simulador/`):

    pip install -r api/requirements.txt
    COPA_DATASET_PATH=/caminho/players_data.csv uvicorn api.asgi:app --port 8000
    python -m pytest python_prototype api

Variáveis: `COPA_DATASET_PATH`, `COPA_GAME_TTL_SECONDS` (3600), `COPA_MAX_GAMES` (1000), `COPA_CORS_ORIGINS` (`*`).
Docs interativas: `/docs`. Antes de tudo, aplique `PATCHES.md` (enum de cartões e `TournamentConfig.cards`).

Notas: um único worker (sessões em memória); mínimos de setor do elenco em `api/catalog.py` (**critério a confirmar**).
