# Usa una imagen base de Python optimizada para contenedores
FROM python:3.12-slim

# Directorio de trabajo
WORKDIR /app

# Copia requirements.txt primero para aprovechar caché de Docker
COPY requirements.txt /app/

# Instala las dependencias desde el archivo requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de archivos de tu proyecto
COPY . /app/

# Expone el puerto 8080
EXPOSE 8080

# Variables de entorno por defecto
ENV PORT=8080
ENV ENV=prod

# Ejecuta la aplicación
CMD ["uvicorn", "prueba:app", "--host", "0.0.0.0", "--port", "8080"]
