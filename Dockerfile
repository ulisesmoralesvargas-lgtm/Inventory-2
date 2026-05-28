FROM python:3.11-slim
WORKDIR /app
COPY requirements.backend.txt .
RUN pip install --no-cache-dir -r requirements.backend.txt
COPY . .
EXPOSE 8080
CMD ["python", "app.py"]
