# 1. Usar la imagen de Python
FROM python:3.11-slim

# 2. Directorio de trabajo
WORKDIR /app

# 3. Copiar el requirements de Streamlit (Asegúrate de que se llame requirements.txt)
COPY requirements.txt .

# 4. Instalar las librerías de Streamlit
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar todo el código del proyecto
COPY . .

# 6. Exponer el puerto de Cloud Run
EXPOSE 8080

# 7. Comando de arranque CORRECTO para Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
