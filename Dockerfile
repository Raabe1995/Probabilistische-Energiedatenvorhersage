FROM python:3.10-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    STREAMLIT_BROWSER_SERVER_ADDRESS=localhost \
    STREAMLIT_BROWSER_SERVER_PORT=8501

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY .streamlit .streamlit

RUN mkdir -p /app/data/input /app/data/output

# Interner Streamlit-Port; Docker Compose veröffentlicht ihn am Host als Port 8503.
EXPOSE 8501

# Streamlit ohne File-Watcher-Neuladungen während der Pipeline-Ausgaben starten.
CMD ["streamlit", "run", "src/energy_forecasting/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.fileWatcherType=none", "--server.headless=true", "--browser.gatherUsageStats=false"]
