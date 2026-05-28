FROM python:3.11-slim
WORKDIR /app

COPY requirements.frontend.txt ./requirements.frontend.txt
RUN pip install --no-cache-dir -r requirements.frontend.txt

COPY . .

EXPOSE 8080

# Arranca única y exclusivamente Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
CMD ["python", "main.py"]
