FROM python:3.11-slim

WORKDIR /app

# Copy and install unified requirements
COPY requirements.backend.txt .
RUN pip install --no-cache-dir -r requirements.backend.txt

# Copy all code assets
COPY . .

EXPOSE 8080

# Starts FastAPI instantly on the environment specified PORT
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
