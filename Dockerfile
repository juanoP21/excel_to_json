# ---------- 1. Etapa de build ----------
FROM python:3.10-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .

# gcc y build-deps sólo en la etapa de compilación (necesarios para gevent)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libffi-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

COPY . .
RUN python manage.py collectstatic --noinput

# ---------- 2. Etapa de runtime ----------
FROM python:3.10-slim

WORKDIR /app
ENV DJANGO_SETTINGS_MODULE=excel_to_json.settings \
    DEBUG=False \
    # Parámetros de Gunicorn en una sola variable:
    GUNICORN_CMD_ARGS="\
        --bind=0.0.0.0:8000 \
        --workers=4 \
        --worker-class=gevent \
        --timeout=120 \
        --keep-alive=5 \
        --max-requests=1000 \
        --max-requests-jitter=100"

# Copiamos los paquetes ya instalados y el código
COPY --from=build /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=build /app /app

# WhiteNoise para servir estáticos
ENV STATIC_ROOT=/app/staticfiles
EXPOSE 8000
CMD ["gunicorn", "excel_to_json.wsgi:application"]
