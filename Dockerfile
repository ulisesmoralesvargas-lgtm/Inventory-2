FROM python:3.11-slim

WORKDIR /app

COPY requirements.backend.txt .
RUN pip install --no-cache-dir -r requirements.backend.txt

COPY . .

EXPOSE 8080

# Comando mágico: Corre la API en el puerto 8000 en segundo plano, 
# y lanza Streamlit en el puerto 8080 en primer plano.
CMD python app.py backend & streamlit run app.py --server.port 8080 --server.address 0.0.0.0
