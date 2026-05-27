FROM python:3.11-slim

WORKDIR /app

# Instalamos las dependencias de ambos mundos
COPY requirements.txt ./
# Si tienes un requirements.backend.txt, también lo instalamos:
COPY requirements.backend.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements.backend.txt

COPY . .

EXPOSE 8080

# Arrancamos Uvicorn (FastAPI) en segundo plano y Streamlit en primer plano
CMD uvicorn main:app --host 0.0.0.0 --port 8000 & streamlit run app.py --server.port=8080 --server.address=0.0.0.0
