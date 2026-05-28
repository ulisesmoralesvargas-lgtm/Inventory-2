import os
import io
import uvicorn
import pandas as pd
import sqlalchemy
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage
from sqlalchemy.orm import declarative_base, sessionmaker, Session

app = FastAPI(title="Inventory Cloud API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURACIÓN DE BASES DE DATOS ---
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "inventory_db")

# Conexión local vs Conexión Cloud Run Unix Socket
if os.environ.get("INSTANCE_CONNECTION_NAME"):
    # Conexión en producción (Google Cloud)
    db_url = sqlalchemy.URL.create(
        drivername="postgresql+pg8000",
        username=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        query={"unix_sock": f"/cloudsql/{os.environ.get('INSTANCE_CONNECTION_NAME')}/.s.PGSQL.5432"}
    )
else:
    # Conexión local de respaldo
    db_url = f"postgresql+pg8000://{DB_USER}:{DB_PASS}@127.0.0.1:5432/{DB_NAME}"

engine = sqlalchemy.create_engine(db_url, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelo de la Tabla de Inventario
class Asset(Base):
    __tablename__ = "assets"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, index=True)
    nombre = sqlalchemy.Column(sqlalchemy.String)
    departamento = sqlalchemy.Column(sqlalchemy.String)
    sede = sqlalchemy.Column(sqlalchemy.String)
    estatus = sqlalchemy.Column(sqlalchemy.String)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

BUCKET_NAME = "bucket-asset-auscc"
FILE_NAME = "inventory_data.csv"

# 1. RUTA DEL CSV (Tu respaldo de Cloud Storage)
@app.get("/assets/csv")
def get_csv_data():
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(FILE_NAME)
        content = blob.download_as_bytes()
        df = pd.read_csv(io.BytesIO(content))
        records = df.fillna("").to_dict(orient="records")
        return {"data": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. RUTAS DE MENÚS Y DATOS (Lo que pide tu Streamlit de la Base de Datos)
@app.get("/assets")
def get_all_assets(db: Session = Depends(get_db)):
    assets = db.query(Asset).all()
    records = [{"id": a.id, "nombre": a.nombre, "departamento": a.departamento, "sede": a.sede, "estatus": a.estatus} for a in assets]
    return {"data": records}

@app.post("/assets")
def create_asset(asset_data: dict, db: Session = Depends(get_db)):
    nuevo = Asset(
        nombre=asset_data.get("nombre"),
        departamento=asset_data.get("departamento"),
        sede=asset_data.get("sede"),
        estatus=asset_data.get("estatus")
    )
    db.add(nuevo)
    db.commit()
    return {"status": "created"}

@app.get("/health")
def health():
    return {"status": "online"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
