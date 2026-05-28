FROM python:3.11-slim

# Step 1: Set working directory
WORKDIR /app

# Step 2: Install dependencies
# Make sure pandas, fastapi, uvicorn, and google-cloud-storage are in this file!
COPY requirements.backend.txt .
RUN pip install --no-cache-dir -r requirements.backend.txt

# Step 3: Copy your code
COPY . .

# Step 4: Start FastAPI
# This uses uvicorn to run the 'app' object inside 'main.py'
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
