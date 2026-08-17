FROM python:3.11-slim

WORKDIR /app

COPY src/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY classes.json .
COPY src/api/ .

# Code du modèle (Binôme B). Le fichier .keras, lui, n'est pas copié dans
# l'image : il pèse 23 Mo, n'est pas versionné, et arrive par le volume
# ./models monté sur /app/models par docker-compose.
COPY src/model/ ./model/

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
