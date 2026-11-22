FROM python:3.12-slim
LABEL org.opencontainers.image.title="Altium Financiero" \
      org.opencontainers.image.version="v26-sin-ia" \
      org.opencontainers.image.description="Dashboard financiero con presupuestos, deudas y reportes PDF."
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 fonts-dejavu-core curl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt
# Solo codigo y recursos publicos. No copiar toda la carpeta ni los libros Excel.
COPY app.py ./app.py
COPY modules/ ./modules/
COPY imagenes/ ./imagenes/
COPY streamlit-docker.toml ./.streamlit/config.toml
COPY validar_imagen_publica.py /usr/local/lib/altium/validar_imagen_publica.py
# Comprobar con el mismo Python que ejecutará la imagen, antes de publicarla.
RUN python /usr/local/lib/altium/validar_imagen_publica.py
RUN mkdir -p /app/data /tmp/matplotlib \
    && chmod -R 755 /app \
    && chmod 1777 /tmp/matplotlib
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --fail http://127.0.0.1:8501/_stcore/health || exit 1
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
