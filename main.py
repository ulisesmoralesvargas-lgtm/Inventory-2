"""
Inventory Management System — FastAPI Backend
100% Google Cloud Platform — no Supabase, no Railway.
Connects to Cloud SQL (PostgreSQL) via cloud-sql-python-connector.
Runs on Cloud Run (listens on 0.0.0.0:$PORT).
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
INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME", "PROJECT:REGION:INSTANCE")
DB_USER     = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME     = os.environ.get("DB_NAME", "inventory")

ADMIN_USER     = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")

PORT = int(os.environ.get("PORT", 8080))

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
    pool_size=5,
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=1800,
)

def get_db():
    # Salvaguarda por si SQL no está listo, permitiendo que el modo CSV funcione solo
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

# ── Simple HTTP Basic Auth ────────────────────────────────────────────────────
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
    asset_tag:                    Optional[str]   = None
    serial_number:                Optional[str]   = None
    part_number:                  Optional[str]   = None
    po_number:                    Optional[str]   = None
    description:                  str             = Field(..., min_length=1)
    notes:                        Optional[str]   = None
    quantity:                     int             = Field(1, ge=0)
    price:                        Optional[float] = None
    category_id:                  Optional[int]   = None
    department_id:                Optional[int]   = None
    campus_id:                    Optional[int]   = None
    location_id:                  Optional[int]   = None
    supplier_id:                  Optional[int]   = None
    status_id:                    Optional[int]   = None
    condition_id:                 Optional[int]   = None
    purchase_date:                Optional[str]   = None
    date_placed_in_service:       Optional[str]   = None
    last_issued_or_transfer_date: Optional[str]   = None
    day_disposed:                 Optional[str]   = None
    last_day_scanned:             Optional[str]   = None

class AssetPatch(BaseModel):
    status_id:                    Optional[int]   = None
    condition_id:                 Optional[int]   = None
    location_id:                  Optional[int]   = None
    campus_id:                    Optional[int]   = None
    notes:                        Optional[str]   = None
    last_day_scanned:             Optional[str]   = None
    last_issued_or_transfer_date: Optional[str]   = None
    day_disposed:                 Optional[str]   = None
    quantity:                     Optional[int]   = Field(None, ge=0)

# ── Reference tables (Manejador de Fallos para soportar modo CSV) ─────────────
ALLOWED_REF = {"categories", "departments", "campuses", "locations",
               "suppliers", "statuses", "conditions"}

@app.get("/ref/{table}")
def get_reference(table: str, db=Depends(get_db)):
    if table not in ALLOWED_REF:
        raise HTTPException(status_code=404, detail="Reference table not found.")
    
    # Si la base de datos no está conectada, enviamos datos limpios de respaldo
    if db is None:
        return [{"id": 1, "name": "Default / CSV Mode"}]
        
    try:
        rows = db.execute(text(f"SELECT id, name FROM {table} ORDER BY name")).mappings().all()
        return [dict(r) for r in rows]
    except Exception:
        return [{"id": 1, "name": "Default / CSV Mode"}]


# ── NUEVA RUTA: Cargar Assets usando la API nativa de Google Cloud Storage ────
BUCKET_NAME = "bucket-asset-auscc"
BLOB_NAME = "inventory_data.csv"

@app.get("/assets/csv")  
def get_assets_from_csv():
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(BLOB_NAME)
        
        content = blob.download_as_bytes()
        df = pd.read_csv(io.BytesIO(content))
        
        # Limpieza de valores NaN/Null de Pandas para que JSON no falle al enviarse
        df = df.fillna("")
        
        data = df.to_dict(orient="records")
        return {"data": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo el CSV desde la API de Storage: {str(e)}")


# ── GET /assets (Desde la Base de Datos Cloud SQL) ────────────────────────────
@app.get("/assets")
def list_assets(
    department: Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    campus:     Optional[str] = Query(None),
    search:     Optional[str] = Query(None),
    limit:      int           = Query(200, le=1000),
    offset:     int           = Query(0, ge=0),
    db=Depends(get_db),
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection is unavailable.")

    where_clauses = []
    params = {"limit": limit, "offset": offset}

    if department:
        where_clauses.append("department = :department")
        params["department"] = department
    if status:
        where_clauses.append("status = :status")
        params["status"] = status
    if campus:
        where_clauses.append("campus = :campus")
        params["campus"] = campus
    if search:
        where_clauses.append("(description ILIKE :search OR asset_tag ILIKE :search)")
        params["search"] = f"%{search}%"

    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    sql = text(f"SELECT * FROM assets_view {where} ORDER BY id LIMIT :limit OFFSET :offset")
    
    try:
        rows = db.execute(sql, params).mappings().all()
        data = [dict(r) for r in rows]
        return {"data": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en consulta SQL: {str(e)}")

# ── GET /assets/{id} ─────────────────────────────────────────────────────────
@app.get("/assets/{asset_id}")
def get_asset(asset_id: int, db=Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection is unavailable.")
    row = db.execute(
        text("SELECT * FROM assets_view WHERE id = :id"),
        {"id": asset_id}
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found.")
    return dict(row)

# ── POST /assets (auth required) ─────────────────────────────────────────────
@app.post("/assets", status_code=201)
def create_asset(
    payload: AssetCreate,
    _user: str = Depends(get_current_user),
    db=Depends(get_db),
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection is unavailable.")
    data = payload.model_dump(exclude_none=True)
    cols = ", ".join(data.keys())
    vals = ", ".join(f":{k}" for k in data.keys())
    row = db.execute(
        text(f"INSERT INTO assets ({cols}) VALUES ({vals}) RETURNING *"),
        data
    ).mappings().first()
    db.commit()
    return dict(row)

# ── PATCH /assets/{id} (auth required) ───────────────────────────────────────
@app.patch("/assets/{asset_id}")
def update_asset(
    asset_id: int,
    payload: AssetPatch,
    _user: str = Depends(get_current_user),
    db=Depends(get_db),
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection is unavailable.")
    data = payload.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update.")
    sets = ", ".join(f"{k} = :{k}" for k in data.keys())
    data["asset_id"] = asset_id
    row = db.execute(
        text(f"UPDATE assets SET {sets} WHERE id = :asset_id RETURNING *"),
        data
    ).mappings().first()
    db.commit()
    if not row:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found.")
    return dict(row)

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "port": PORT}

# ── Entrypoint — 0.0.0.0 + $PORT for Cloud Run ───────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
