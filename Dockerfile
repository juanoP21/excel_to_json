FROM python:3.10-slim

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Asegurar que Django pueda ejecutar collectstatic sin errores
ENV DJANGO_SETTINGS_MODULE=excel_to_json.settings
ENV DEBUG=False
# Esta clave es solo para la construcción de la imagen, será reemplazada en tiempo de ejecución
ENV SECRET_KEY=temp_build_key_replace_in_production
ENV ALLOWED_HOSTS=localhost,127.0.0.1

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . .

# Crear directorio estático si no existe
RUN mkdir -p staticfiles

# Ejecutar collectstatic con las variables de entorno configuradas
RUN python manage.py collectstatic --noinput || echo "Collectstatic failed but continuing build"

# Puerto en el que corre gunicorn
EXPOSE 8000

# Comando para iniciar la aplicación con gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "excel_to_json.wsgi:application"]