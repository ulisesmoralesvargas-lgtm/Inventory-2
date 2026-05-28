import os
import io
import uvicorn
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage

app = FastAPI(title="Assignment Inventory System")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BUCKET_NAME = "bucket-asset-auscc"
FILE_NAME = "inventory_data.csv"

# --- REQUIREMENT: FastAPI Endpoint fetching from GCS ---
@app.get("/assets/csv")
def get_csv_data():
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(FILE_NAME)
        
        # Download GCS content into memory
        content = blob.download_as_bytes()
        df = pd.read_csv(io.BytesIO(content))
        
        # Data cleaning to prevent JSON formatting bugs
        clean_df = df.fillna("")
        records = clean_df.to_dict(orient="records")
        
        return {"data": records, "count": len(records)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GCS Error: {str(e)}")

# --- Cloud Run Health Check Endpoint ---
@app.get("/health")
def health():
    return {"status": "online", "framework": "FastAPI"}

# --- FRONTEND UI: Rendered directly by FastAPI to avoid 404s and Port conflicts ---
@app.get("/", response_class=HTMLResponse)
def index_frontend():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Inventory Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 font-sans leading-normal tracking-normal">
        <div class="container w-full mx-auto pt-20">
            <div class="w-full px-4 md:px-6 text-xl text-gray-800 leading-normal">
                <div class="font-sans">
                    <h1 class="font-bold font-sans break-normal text-gray-900 pt-6 pb-2 text-3xl md:text-4xl">📦 Inventory Control Panel</h1>
                    <p class="text-sm md:text-base font-normal text-gray-600">Connected to FastAPI Backend & Google Cloud Storage</p>
                </div>
                
                <div class="mt-8 bg-white p-6 rounded shadow">
                    <h2 class="text-xl font-bold mb-4">Live Inventory Data</h2>
                    <div class="overflow-x-auto">
                        <table class="min-w-full bg-white border border-gray-200" id="inventoryTable">
                            <thead>
                                <tr class="bg-gray-200 text-gray-600 text-sm leading-normal">
                                    <th class="py-3 px-6 text-left">Data Records Loading...</th>
                                </tr>
                            </thead>
                            <tbody class="text-gray-600 text-sm font-light" id="tableBody">
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // Automatically fetch data from your FastAPI requirement endpoint
            fetch('/assets/csv')
                .then(response => response.json())
                .then(resData => {
                    const data = resData.data;
                    if (!data || data.length === 0) return;
                    
                    // Build table columns dynamically based on CSV keys
                    const keys = Object.keys(data[0]);
                    const table = document.getElementById('inventoryTable');
                    
                    let headerRow = '<tr class="bg-gray-200 text-gray-700 uppercase text-xs leading-normal">';
                    keys.forEach(key => headerRow += `<th class="py-3 px-6 text-left">${key}</th>`);
                    headerRow += '</tr>';
                    
                    let bodyRows = '';
                    data.forEach(row => {
                        bodyRows += '<tr class="border-b border-gray-200 hover:bg-gray-100">';
                        keys.forEach(key => {
                            bodyRows += `<td class="py-3 px-6 text-left whitespace-nowrap">${row[key]}</td>`;
                        });
                        bodyRows += '</tr>';
                    });
                    
                    table.innerHTML = `<thead>${headerRow}</thead><tbody class="text-gray-600 text-sm font-light">${bodyRows}</tbody>`;
                })
                .catch(err => {
                    document.getElementById('tableBody').innerHTML = `<tr><td class="p-4 text-red-500">Error loading backend API data: ${err}</td></tr>`;
                });
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    # Pull port assigned by Google Cloud Run, defaulting to 8080 locally
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
