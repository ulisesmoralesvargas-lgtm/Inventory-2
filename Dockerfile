# 1. Usar la imagen oficial de Python
FROM python:3.11-slim

# 2. Configurar el directorio de trabajo
WORKDIR /app

# 3. Copiar e instalar los requerimientos del FRONTEND y BACKEND por separado
COPY requirements.frontend.txt ./requirements.frontend.txt
COPY requirements.backend.txt ./requirements.backend.txt

# Instalar ambos archivos para que convivan FastAPI y Streamlit
RUN pip install --no-cache-dir -r requirements.frontend.txt
RUN pip install --no-cache-dir -r requirements.backend.txt

# 4. Copiar todo el código del proyecto al contenedor
COPY . .

# 5. Exponer el puerto principal que exige Cloud Run
EXPOSE 8080

# 6. Comando de arranque dual: Corre FastAPI en el puerto 8000 (segundo plano) 
# y Streamlit en el puerto 8080 (primer plano)
CMD uvicorn main:app --host 0.0.0.0 --port 8000 & streamlit run app.py --server.port=8080 --server.address=0.0.0.0
