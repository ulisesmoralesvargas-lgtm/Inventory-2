# 1. Usar una imagen oficial de Python ligera
FROM python:3.11-slim

# 2. Configurar el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar solo el archivo de requerimientos del backend
COPY requirements.backend.txt .

# 4. Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.backend.txt

# 5. Copiar el resto de los archivos del proyecto (como main.py y app.py)
COPY . .

# 6. Exponer el puerto que Cloud Run exige por defecto
EXPOSE 8080

# 7. Arrancar la aplicación con Uvicorn usando el puerto dinámico de Google
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
