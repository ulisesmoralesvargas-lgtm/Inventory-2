import os
import io
import threading
import uvicorn
import pandas as pd
import streamlit as st
import requests
import sqlalchemy
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# =========================================
# 1. CONFIGURACIÓN DEL BACKEND (FASTAPI)
# =========================================
backend_app = FastAPI(title="Inventory Cloud API")

backend_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "inventory_db")

if os.environ.get("INSTANCE_CONNECTION_NAME"):
    db_url = sqlalchemy.URL.create(
        drivername="postgresql+pg8000",
        username=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        query={"unix_sock": f"/cloudsql/{os.environ.get('INSTANCE_CONNECTION_NAME')}/.s.PGSQL.5432"}
    )
else:
    db_url = f"postgresql+pg8000://{DB_USER}:{DB_PASS}@127.0.0.1:5432/{DB_NAME}"

engine = sqlalchemy.create_engine(db_url, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Asset(Base):
    __tablename__ = "assets"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, index=True)
    nombre = sqlalchemy.Column(sqlalchemy.String)
    departamento = sqlalchemy.Column(sqlalchemy.String)
    sede = sqlalchemy.Column(sqlalchemy.String)
    estatus = sqlalchemy.Column(sqlalchemy.String)

try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

BUCKET_NAME = "bucket-asset-auscc"
FILE_NAME = "inventory_data.csv"

@backend_app.get("/assets/csv")
def get_csv_data():
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(FILE_NAME)
        content = blob.download_as_bytes()
        df = pd.read_csv(io.BytesIO(content))
        return {"data": df.fillna("").to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@backend_app.get("/assets")
def get_all_assets(db: Session = Depends(get_db)):
    assets = db.query(Asset).all()
    records = [{"id": a.id, "nombre": a.nombre, "departamento": a.departamento, "sede": a.sede, "estatus": a.estatus} for a in assets]
    return {"data": records}

@backend_app.post("/assets")
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

@backend_app.get("/health")
def health():
    return {"status": "online"}

# Endpoint especial: Redirige la raíz de la API (8080) hacia el Streamlit (8000)
@backend_app.get("/")
def read_root():
    from fastapi.responses import RedirectResponse
    # Redirige al puerto de Streamlit para que no veas JSON vacío
    return RedirectResponse(url="http://localhost:8000")

def start_backend():
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(backend_app, host="0.0.0.0", port=port)

# =========================================
# 2. CONFIGURACIÓN DEL FRONTEND (STREAMLIT)
# =========================================
def run_frontend():
    st.set_page_config(page_title="Inventory System", layout="wide")

    # AQUÍ ESTÁ TU INTERFAZ QUE HABÍA DESAPARECIDO:
    st.sidebar.title("🏢 Inventory System")
    st.sidebar.write("👤 Logged in as: **ulises.mova10**")
    
    menu = st.sidebar.radio(
        "Navigation Menu", 
        ["Browse Assets (CSV)", "Browse Assets (SQL)", "Add Asset"]
    )

    if menu == "Browse Assets (CSV)":
        st.title("📝 Data from CSV")
        try:
            # Llama a la API local en el puerto 8080
            res = requests.get("http://127.0.0.1:8080/assets/csv")
            if res.status_code == 200:
                st.dataframe(pd.DataFrame(res.json().get("data", [])))
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu == "Browse Assets (SQL)":
        st.title("🗄️ Data from PostgreSQL")
        try:
            res = requests.get("http://127.0.0.1:8080/assets")
            if res.status_code == 200:
                st.dataframe(pd.DataFrame(res.json().get("data", [])))
        except Exception as e:
            st.error(f"Error: {e}")

    elif menu == "Add Asset":
        st.title("➕ Add New Asset")
        nombre = st.text_input("Asset Name")
        dept = st.selectbox("Department", ["IT", "HVAC", "AUTO"])
        sede = st.text_input("Campus / Sede")
        estatus = st.selectbox("Status", ["In Use", "In Storage"])
        
        if st.button("Submit"):
            payload = {"nombre": nombre, "departamento": dept, "sede": sede, "estatus": estatus}
            try:
                res = requests.post("http://127.0.0.1:8080/assets", json=payload)
                if res.status_code == 200:
                    st.success("Asset saved through FastAPI into PostgreSQL!")
            except Exception as e:
                st.error(f"Error: {e}")

# =========================================
# 3. LANZAMIENTO CONTROLADO
# =========================================
if __name__ == "__main__":
    import sys
    # Si se ejecuta pasándole el argumento "frontend", corre Streamlit en el 8000
    if len(sys.argv) > 1 and sys.argv[1] == "frontend":
        run_frontend()
    else:
        # Por defecto, arranca la API en el puerto 8080
        start_backend()
