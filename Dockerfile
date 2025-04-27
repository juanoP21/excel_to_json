FROM python:3.10-slim

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . .

# Ejecutar migraciones y collectstatic (puede moverlo a un script de inicio si prefiere)
RUN python manage.py collectstatic --noinput

# Puerto en el que corre gunicorn
EXPOSE 8000

# Comando para iniciar la aplicación con gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "miciroservices.wsgi:application"]