"""
HYBRID APP: FastAPI (Requirement) + Streamlit (Frontend)
Unified for Google Cloud Run on Port 8080.
"""
import os
import io
import subprocess
import time
import uvicorn
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage

# --- Part 1: FastAPI Backend ---
app = FastAPI(title="Assignment Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BUCKET_NAME = "bucket-asset-auscc"
FILE_NAME = "inventory_data.csv"

@app.get("/assets/csv")
def get_csv_data():
    """Assignment Requirement: FastAPI endpoint reading from GCS"""
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
    return {"status": "ok", "service": "FastAPI"}

# --- Part 2: Process Management ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    
    # Check if we are being asked to run the Streamlit side
    if os.environ.get("RUN_MODE") == "frontend":
        # This part runs the Streamlit UI
        import streamlit.web.cli as stcli
        import sys
        sys.argv = [
            "streamlit", "run", "main.py", 
            "--server.port", str(port), 
            "--server.address", "0.0.0.0"
        ]
        stcli.main()
    else:
        # This part starts FastAPI as the primary server
        uvicorn.run(app, host="0.0.0.0", port=port)
