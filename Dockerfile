FROM python:3.10-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY eda.py .
COPY dashboard_utils.py .
COPY training_utils.py .
COPY train_lstm.py .
COPY train_rnn.py .
COPY main.py .
COPY .streamlit .streamlit

RUN mkdir -p /app/data/input /app/data/output

# Port für Streamlit nach außen freigeben
EXPOSE 8501

# Startbefehl: Startet nun das Streamlit Frontend (ersetzt den alten python-Aufruf)
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.fileWatcherType=none", "--server.headless=true", "--browser.gatherUsageStats=false"]
