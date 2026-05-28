"""
Inventory Management System — FastAPI Backend
100% Google Cloud Platform.
Connects to Cloud SQL (PostgreSQL) and Cloud Storage (CSV).
"""

from __future__ import annotations
import os
import io  
import secrets
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
import pandas as pd  
from fastapi import Depends, FastAPI, HTTPException, Query, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from google.cloud import storage  
from google.cloud.sql.connector import Connector
from pydantic import BaseModel, Field
import sqlalchemy
from sqlalchemy import text

# ── Environment variables ─────────────────────────────────────────────────────
INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME", "t-cogency-497119-q0:northamerica-south1:inventory-db")
DB_USER     = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME     = os.environ.get("DB_NAME", "inventory")

ADMIN_USER     = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")

PORT = int(os.environ.get("PORT", 8080))
BUCKET_NAME = "bucket-asset-auscc"
BLOB_NAME = "inventory_data.csv"

# ── Cloud SQL connection pool ─────────────────────────────────────────────────
connector = Connector()

def get_connection():
    return connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pg8000",
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
    )

engine = sqlalchemy.create_engine(
    "postgresql+pg8000://",
    creator=get_connection,
)

def get_db():
    try:
        with engine.connect() as conn:
            yield conn
    except Exception:
        yield None

# ── App setup ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    try:
        connector.close()
    except Exception:
        pass

app = FastAPI(title="Inventory Management API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    valid_user = secrets.compare_digest(credentials.username, ADMIN_USER)
    valid_pass = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (valid_user and valid_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# ── Pydantic models ───────────────────────────────────────────────────────────
class AssetCreate(BaseModel):
    description: str = Field(..., min_length=1)
    quantity: int = Field(1, ge=0)
    # ... other fields ...

# ── SECURE CSV ROUTE: Fetches directly from GCS ──────────────────────────────
@app.get("/assets/csv")  
def get_assets_from_csv():
    """
    Directly fetches the CSV from Cloud Storage using the Service Account.
    No public URL required.
    """
    try:
        # Initialize the Storage client
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(BLOB_NAME)
        
        # Download as bytes and read into Pandas
        content = blob.download_as_bytes()
        df = pd.read_csv(io.BytesIO(content))
        
        # Clean data for JSON compatibility (replace NaN with empty strings)
        df = df.fillna("")
        
        data = df.to_dict(orient="records")
        return {"data": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GCS Error: {str(e)}")

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "port": PORT}

# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)

