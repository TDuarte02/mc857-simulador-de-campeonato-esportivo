FROM python:3.12-slim
WORKDIR /srv
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt
COPY python_prototype python_prototype
COPY api api
# O dataset NÃO vai na imagem: monte em /data/players_data.csv.
ENV COPA_DATASET_PATH=/data/players_data.csv
EXPOSE 8000
CMD ["uvicorn", "api.asgi:app", "--host", "0.0.0.0", "--port", "8000"]
