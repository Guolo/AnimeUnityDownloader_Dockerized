# Usa un'immagine Python leggera
FROM python:3.11-slim

# Imposta la directory di lavoro nel container
WORKDIR /app

# Installa le dipendenze di sistema (necessarie per Brotli e pacchetti di rete)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia il file dei requisiti e installa le librerie Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del codice (backend e frontend)
COPY . .

# Esponi la porta utilizzata da app.py (di solito 5000 per Flask)
EXPOSE 5050

# Variabile d'ambiente per evitare che Python generi file .pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Comando per avviare l'applicazione frontend
CMD ["python", "frontend/app.py"]
