import os
import io
import uvicorn
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage

app = FastAPI(title="Assignment API")

# Enable CORS so your frontend can talk to your backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BUCKET_NAME = "bucket-asset-auscc"
FILE_NAME = "inventory_data.csv"

# --- REQUIREMENT: FastAPI Endpoint ---
@app.get("/assets/csv")
def get_csv_data():
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(FILE_NAME)
        content = blob.download_as_bytes()
        df = pd.read_csv(io.BytesIO(content))
        return df.fillna("").to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "online", "framework": "FastAPI"}

# --- Start the App ---
if __name__ == "__main__":
    # Cloud Run provides the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

