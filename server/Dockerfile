FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN pip install --no-cache-dir uv==0.11.18

WORKDIR /app

# Dependencies first, so code changes don't reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY main.py ./
COPY api ./api

ENV PATH="/opt/venv/bin:$PATH" \
    REPOSITORY=mongo \
    MONGO_URI=mongodb://mongo:27017 \
    MONGO_DB=copa

RUN useradd --system --no-create-home app
USER app

EXPOSE 5000
CMD ["flask", "--app", "main", "run", "--host", "0.0.0.0", "--port", "5000"]
