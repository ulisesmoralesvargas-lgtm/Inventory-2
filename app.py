"""
HYBRID APP: FastAPI (Backend con Cloud SQL + CSV GCS) + Streamlit (Frontend con Formularios)
Diseñado exclusivamente para Google Cloud Run en el Puerto 8080.
"""
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

# ==========================================
# 1. CONFIGURACIÓN DE FASTAPI Y BASE DE DATOS
# ==========================================
backend_app = FastAPI(title="Assignment Inventory API")

backend_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "inventory_db")

# Detectar automáticamente si estamos en Google Cloud o Local
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

# Modelo de base de datos adaptado exactamente a tus campos reales de la captura
class Asset(Base):
    __tablename__ = "assets"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, index=True)
    description = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    asset_tag = sqlalchemy.Column(sqlalchemy.String)
    serial_number = sqlalchemy.Column(sqlalchemy.String)
    part_number = sqlalchemy.Column(sqlalchemy.String)
    po_number = sqlalchemy.Column(sqlalchemy.String)
    quantity = sqlalchemy.Column(sqlalchemy.Integer, default=1)
    category = sqlalchemy.Column(sqlalchemy.String)
    department = sqlalchemy.Column(sqlalchemy.String)
    campus = sqlalchemy.Column(sqlalchemy.String)
    location = sqlalchemy.Column(sqlalchemy.String)
    supplier = sqlalchemy.Column(sqlalchemy.String)
    status = sqlalchemy.Column(sqlalchemy.String)

# Crear las tablas en PostgreSQL automáticamente si no existen
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

# --- REQUISITO: Endpoint que lee desde el CSV de GCS ---
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

# --- REQUISITO: Endpoints de Base de Datos para Altas y Consultas ---
@backend_app.get("/assets/sql")
def get_sql_assets(db: Session = Depends(get_db)):
    try:
        assets = db.query(Asset).all()
        records = []
        for a in assets:
            records.append({
                "ID": a.id, "Asset Tag": a.asset_tag, "Serial Number": a.serial_number,
                "Description": a.description, "Quantity": a.quantity, "Category": a.category,
                "Department": a.department, "Status": a.status, "Campus": a.campus,
                "Location": a.location, "Part Number": a.part_number, "PO Number": a.po_number, "Supplier": a.supplier
            })
        return {"data": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@backend_app.post("/assets/sql")
def create_sql_asset(asset_data: dict, db: Session = Depends(get_db)):
    try:
        nuevo = Asset(
            description=asset_data.get("description", "No Description"),
            asset_tag=asset_data.get("asset_tag", ""),
            serial_number=asset_data.get("serial_number", ""),
            part_number=asset_data.get("part_number", ""),
            po_number=asset_data.get("po_number", ""),
            quantity=int(asset_data.get("quantity", 1)),
            category=asset_data.get("category", ""),
            department=asset_data.get("department", ""),
            campus=asset_data.get("campus", ""),
            location=asset_data.get("location", ""),
            supplier=asset_data.get("supplier", ""),
            status=asset_data.get("status", "")
        )
        db.add(nuevo)
        db.commit()
        return {"status": "success", "message": "Asset saved to PostgreSQL"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@backend_app.get("/health")
def health():
    return {"status": "online"}

def start_backend_thread():
    uvicorn.run(backend_app, host="127.0.0.1", port=8000)


# ==========================================
# 2. INTERFAZ FRONTEND DE STREAMLIT
# ==========================================
def run_frontend():
    st.set_page_config(page_title="Inventory System", layout="wide")

    # Restaurando exactamente tu menú de la izquierda
    st.sidebar.title("🏢 Inventory System")
    st.sidebar.write("👤 Logged in as: **ulises.mova10@gmail.com**")
    
    menu = st.sidebar.radio(
        "Navigation Menu", 
        ["Browse Assets (CSV GCS)", "Browse Assets (PostgreSQL)", "Add Asset", "Update Asset", "Login"]
    )
    
    if st.sidebar.button("Log out"):
        st.sidebar.info("Logged out context")

    # --- MENÚ: Vista desde CSV ---
    if menu == "Browse Assets (CSV GCS)":
        st.title("📝 Live Data from Cloud Storage (CSV)")
        try:
            response = requests.get("http://127.0.0.1:8000/assets/csv", timeout=5)
            if response.status_code == 200:
                records = response.json().get("data", [])
                if records:
                    st.dataframe(pd.DataFrame(records), use_container_width=True)
                else:
                    st.warning("CSV is empty.")
            else:
                st.error("Error connecting to CSV route")
        except Exception as e:
            st.error(f"Error: {e}")

    # --- MENÚ: Vista desde Base de Datos SQL ---
    elif menu == "Browse Assets (PostgreSQL)":
        st.title("🗄️ Live Data from PostgreSQL Database")
        try:
            response = requests.get("http://127.0.0.1:8000/assets/sql", timeout=5)
            if response.status_code == 200:
                records = response.json().get("data", [])
                if records:
                    st.dataframe(pd.DataFrame(records), use_container_width=True)
                else:
                    st.info("No assets registered in SQL database yet.")
            else:
                st.error("Error reading database API")
        except Exception as e:
            st.error(f"Error connecting to backend: {e}")

    # --- MENÚ: Agregar Activo (Guardar en Base de Datos) ---
    elif menu == "Add Asset":
        st.title("➕ Add New Asset")
        
        col1, col2 = st.columns(2)
        with col1:
            desc = st.text_input("Description *")
            asset_tag = st.text_input("Asset Tag")
            serial = st.text_input("Serial Number")
            part_no = st.text_input("Part Number")
            po_no = st.text_input("PO Number")
            qty = st.number_input("Quantity", min_value=1, value=1)
        with col2:
            category = st.selectbox("Category", ["Hardware", "Tools", "Consumable", "Software"])
            dept = st.selectbox("Department", ["ALL", "HVAC", "AUTO", "IT"])
            campus = st.selectbox("Campus", ["Main Campus", "North Campus", "South Campus"])
            location = st.selectbox("Location", ["Warehouse A", "Room 101", "Lab 2"])
            supplier = st.selectbox("Supplier", ["Vendor A", "Vendor B", "Global Supplies"])
            status = st.selectbox("Status", ["In Use", "In Storage", "Maintenance"])
            
        if st.button("Submit Asset"):
            if not desc:
                st.error("Description is required.")
            else:
                payload = {
                    "description": desc, "asset_tag": asset_tag, "serial_number": serial,
                    "part_number": part_no, "po_number": po_no, "quantity": qty,
                    "category": category, "department": dept, "campus": campus,
                    "location": location, "supplier": supplier, "status": status
                }
                try:
                    res = requests.post("http://127.0.0.1:8000/assets/sql", json=payload, timeout=5)
                    if res.status_code == 200:
                        st.success("✅ Asset successfully saved inside Cloud SQL PostgreSQL Database!")
                    else:
                        st.error(f"Failed to save: {res.text}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

    # --- MENÚS RESTANTES ---
    elif menu == "Update Asset":
        st.title("🔄 Update Asset Profile")
        st.text_input("Enter Asset Tag to Modify:")
    elif menu == "Login":
        st.title("🔐 Authentication")
        st.text_input("Username")
        st.text_input("Password", type="password")
        st.button("Login")


# ==========================================
# 3. LANZAMIENTO SIMULTÁNEO
# ==========================================
if __name__ == "__main__":
    # 1. Arrancar el API de FastAPI en el fondo
    t = threading.Thread(target=start_backend_thread, daemon=True)
    t.start()
    
    # 2. Configurar Streamlit para que use el puerto asignado por Cloud Run
    port = os.environ.get("PORT", "8080")
    
    import streamlit.web.cli as stcli
    import sys
    
    sys.argv = [
        "streamlit", "run", "app.py",
        "--server.port", port,
        "--server.address", "0.0.0.0"
    ]
    stcli.main()
