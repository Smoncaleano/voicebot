FROM python:3.12-slim

WORKDIR /app

# Instala dependencias del sistema para psycopg2 si lo necesitas:
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia TODO el código (incluyendo la carpeta LLM/)
COPY . .

EXPOSE 8080

CMD ["python", "app.py"]
