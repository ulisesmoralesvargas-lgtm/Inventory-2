import streamlit as st
import pandas as pd
from google.cloud import storage
import io

# 1. Page Config
st.set_page_config(page_title="Inventory Management", layout="wide")
st.title("📦 Inventory Dashboard (from GCS)")

# 2. Cloud Storage Config
BUCKET_NAME = "bucket-asset-auscc"
FILE_NAME = "inventory_data.csv"

@st.cache_data
def load_data_from_gcs():
    try:
        # Initialize the Storage Client
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(FILE_NAME)

        # Download and read
        content = blob.download_as_bytes()
        df = pd.read_csv(io.BytesIO(content))
        
        # Data Cleaning
        df = df.fillna("")
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# 3. Main UI Logic
data = load_data_from_gcs()

if data is not None:
    st.write(f"Showing {len(data)} items from `{FILE_NAME}`")
    
    # Search Filter
    search = st.text_input("Search Assets", "")
    if search:
        data = data[data.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
    
    # Display the Table
    st.dataframe(data, use_container_width=True)
else:
    st.warning("No data found in the bucket.")

