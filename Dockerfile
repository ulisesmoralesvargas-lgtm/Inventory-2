# 1. Usar la imagen oficial de Python
FROM python:3.11-slim

# 2. Configurar el directorio de trabajo
WORKDIR /app

# 3. Copiar e instalar los requerimientos del FRONTEND
# (Asegúrate de cambiar el nombre si tu archivo se llama diferente, ej: requirements.frontend.txt)
COPY requirements.frontend.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar todo el código del proyecto al contenedor
COPY . .

# 5. Exponer el puerto que exige Cloud Run
EXPOSE 8080

# 6. Comando de arranque para Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
