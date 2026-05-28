FROM python:3.11-slim
WORKDIR /app

# Instalar requerimientos del backend
COPY requirements.backend.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# Forzamos a arrancar solo FastAPI en el puerto que pide Google Cloud
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
CMD ["python", "main.py"]
