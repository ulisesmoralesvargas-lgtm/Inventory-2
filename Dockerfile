FROM python:3.11-slim

WORKDIR /app

COPY requirements.backend.txt .
RUN pip install --no-cache-dir -r requirements.backend.txt

COPY . .

# Exponemos el puerto de la API
EXPOSE 8080

# Comando: Lanza Streamlit en el puerto 8000 en segundo plano, 
# y luego arranca la API en el puerto 8080 en primer plano.
CMD streamlit run app.py frontend --server.port 8000 --server.address 0.0.0.0 & python app.py
