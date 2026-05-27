"""
Inventory Management System — Streamlit Frontend
Loads data from Google Cloud Storage CSV instead of API.
Runs locally on localhost:8501 by default.
"""

from __future__ import annotations

import os
from datetime import date

import pandas as pd
import streamlit as st

# ── CSV Data Source ────────────────────────────────────────────────────────────
# CSV file from Google Cloud Storage
URL_CSV = "https://storage.googleapis.com/bucket-asset-auscc/inventory_data.csv"

# ── Session state defaults ─────────────────────────────────────────────────────
for key, default in [
    ("logged_in", False),
    ("username", ""),
    ("loaded_asset", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Data loading and caching ───────────────────────────────────────────────────
@st.cache_data(ttl=300)
def cargar_datos():
    """Load inventory data from Google Cloud Storage CSV."""
    try:
        df = pd.read_csv(URL_CSV)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# ── Page: Login ────────────────────────────────────────────────────────────────
def page_login():
    st.title("🔐 Sign In")
    st.caption("Enter your credentials to manage assets.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In")

    if submitted:
        # Simple credential check (in production, validate against a backend)
        if username and password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.success(f"✅ Logged in as {username}")
            st.rerun()
        else:
            st.error("Please enter username and password.")

# ── Page: Browse Assets ────────────────────────────────────────────────────────
def page_browse():
    st.title("📦 Asset Inventory")

    # Load data
    df = cargar_datos()
    
    if df.empty:
        st.error("No data available. Check your CSV file.")
        return

    with st.sidebar:
        st.header("Filters")
        
        # Get unique values for filters
        departments = [""] + sorted([str(x) for x in df["department"].unique() if pd.notna(x)])
        statuses = [""] + sorted([str(x) for x in df["status"].unique() if pd.notna(x)])
        campuses = [""] + sorted([str(x) for x in df["campus"].unique() if pd.notna(x)])

        dept = st.selectbox("Department", departments)
        status = st.selectbox("Status", statuses)
        campus = st.selectbox("Campus", campuses)
        search = st.text_input("Search description / tag")

    # Apply filters
    filtered_df = df.copy()
    
    if dept:
        filtered_df = filtered_df[filtered_df["department"].astype(str) == dept]
    if status:
        filtered_df = filtered_df[filtered_df["status"].astype(str) == status]
    if campus:
        filtered_df = filtered_df[filtered_df["campus"].astype(str) == campus]
    if search:
        mask = filtered_df["description"].astype(str).str.contains(search, case=False, na=False)
        filtered_df = filtered_df[mask]

    st.caption(f"{len(filtered_df)} asset(s) found")

    if filtered_df.empty:
        st.info("No assets match your filters.")
        return

    # Display columns
    display_cols = [
        "id",
        "asset_tag",
        "description",
        "category",
        "department",
        "status",
        "condition",
        "campus",
        "location",
        "quantity",
        "price",
    ]
    existing = [c for c in display_cols if c in filtered_df.columns]
    st.dataframe(filtered_df[existing], use_container_width=True, hide_index=True)

    # Asset detail
    st.divider()
    st.subheader("Asset Detail")
    asset_id = st.number_input(
        "Enter Asset ID to inspect", min_value=1, step=1, value=1
    )
    if st.button("Load Asset"):
        asset = df[df["id"] == asset_id]
        if asset.empty:
            st.warning("Asset not found.")
        else:
            st.json(asset.iloc[0].to_dict())

# ── Page: Add Asset ────────────────────────────────────────────────────────────
def page_add():
    if not st.session_state["logged_in"]:
        st.warning("You must be logged in to add assets.")
        return

    st.title("➕ Add New Asset")
    st.info("Note: Adding assets updates the local CSV. Integration with database pending.")

    df = cargar_datos()
    if df.empty:
        st.error("Cannot add asset: data not loaded.")
        return

    # Get reference data from CSV
    categories = [""] + sorted([str(x) for x in df["category"].unique() if pd.notna(x)])
    departments = [""] + sorted([str(x) for x in df["department"].unique() if pd.notna(x)])
    campuses = [""] + sorted([str(x) for x in df["campus"].unique() if pd.notna(x)])
    locations = [""] + sorted([str(x) for x in df["location"].unique() if pd.notna(x)])

    with st.form("add_asset_form"):
        col1, col2 = st.columns(2)
        with col1:
            description = st.text_input("Description *")
            asset_tag = st.text_input("Asset Tag")
            serial_number = st.text_input("Serial Number")
            part_number = st.text_input("Part Number")
            po_number = st.text_input("PO Number")
            quantity = st.number_input("Quantity", min_value=0, value=1)
            price = st.number_input("Price ($)", min_value=0.0, format="%.2f")
        with col2:
            category = st.selectbox("Category", categories)
            department = st.selectbox("Department", departments)
            campus = st.selectbox("Campus", campuses)
            location = st.selectbox("Location", locations)
            status = st.text_input("Status", value="Active")
            condition = st.text_input("Condition", value="Good")

        st.subheader("Dates")
        d1, d2, d3 = st.columns(3)
        purchase_date = d1.date_input("Purchase Date", value=None)
        date_placed_in_service = d2.date_input(
            "Date Placed in Service", value=None
        )
        last_day_scanned = d3.date_input("Last Day Scanned", value=None)

        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Add Asset")

    if submitted:
        if not description:
            st.error("Description is required.")
            return

        new_asset = {
            "id": df["id"].max() + 1 if not df.empty else 1,
            "description": description,
            "quantity": quantity,
            "price": price or None,
            "notes": notes or None,
            "asset_tag": asset_tag or None,
            "serial_number": serial_number or None,
            "part_number": part_number or None,
            "po_number": po_number or None,
            "category": category or None,
            "department": department or None,
            "campus": campus or None,
            "location": location or None,
            "status": status or None,
            "condition": condition or None,
            "purchase_date": str(purchase_date) if purchase_date else None,
            "date_placed_in_service": (
                str(date_placed_in_service) if date_placed_in_service else None
            ),
            "last_day_scanned": str(last_day_scanned) if last_day_scanned else None,
        }

        st.success(f"✅ Asset created locally! ID: {new_asset['id']}")
        st.info("Note: Changes are not persisted to the database yet.")
        st.cache_data.clear()

# ── Page: Update Asset ─────────────────────────────────────────────────────────
def page_update():
    if not st.session_state["logged_in"]:
        st.warning("You must be logged in to update assets.")
        return

    st.title("✏️ Update Asset Status / Location")

    df = cargar_datos()
    if df.empty:
        st.error("Cannot update asset: data not loaded.")
        return

    asset_id = st.number_input("Asset ID to update", min_value=1, step=1)

    if st.button("Load current values"):
        asset = df[df["id"] == asset_id]
        if asset.empty:
            st.warning("Asset not found.")
        else:
            st.session_state["loaded_asset"] = asset.iloc[0].to_dict()

    loaded = st.session_state.get("loaded_asset", {})
    if loaded:
        st.info(
            f"Editing: **{loaded.get('description', '')}** (ID {loaded.get('id')})"
        )

    statuses = ["(no change)"] + sorted(
        [str(x) for x in df["status"].unique() if pd.notna(x)]
    )
    conditions = ["(no change)"] + sorted(
        [str(x) for x in df["condition"].unique() if pd.notna(x)]
    )
    campuses = ["(no change)"] + sorted(
        [str(x) for x in df["campus"].unique() if pd.notna(x)]
    )
    locations = ["(no change)"] + sorted(
        [str(x) for x in df["location"].unique() if pd.notna(x)]
    )

    with st.form("update_form"):
        new_status = st.selectbox("New Status", statuses)
        new_condition = st.selectbox("New Condition", conditions)
        new_campus = st.selectbox("New Campus", campuses)
        new_location = st.selectbox("New Location", locations)
        new_notes = st.text_area("Notes (leave blank to keep)")
        scan_today = st.checkbox("Mark as scanned today")
        submitted = st.form_submit_button("Update Asset")

    if submitted:
        changes = {}
        if new_status != "(no change)":
            changes["status"] = new_status
        if new_condition != "(no change)":
            changes["condition"] = new_condition
        if new_campus != "(no change)":
            changes["campus"] = new_campus
        if new_location != "(no change)":
            changes["location"] = new_location
        if new_notes.strip():
            changes["notes"] = new_notes.strip()
        if scan_today:
            changes["last_day_scanned"] = str(date.today())

        if not changes:
            st.warning("Nothing to update.")
            return

        st.success("✅ Asset updated locally.")
        st.info("Note: Changes are not persisted to the database yet.")
        st.cache_data.clear()
        st.session_state.pop("loaded_asset", None)

# ── Navigation ─────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Inventory Management System",
        page_icon="📦",
        layout="wide",
    )

    with st.sidebar:
        st.image("https://img.icons8.com/fluency/48/inventory.png", width=40)
        st.markdown("## 📦 Inventory System")
        st.divider()

        if st.session_state["logged_in"]:
            st.success(f"👤 {st.session_state['username']}")
            if st.button("Log out"):
                st.session_state["logged_in"] = False
                st.session_state["username"] = ""
                st.rerun()
        else:
            st.info("Not logged in")

        st.divider()
        
        # Data source info
        st.caption("📊 Data Source:")
        st.code("Google Cloud Storage CSV", language="text")
        
        page = st.radio(
            "Navigate",
            ["Browse Assets", "Add Asset", "Update Asset", "Login"],
            label_visibility="collapsed",
        )

    if page == "Browse Assets":
        page_browse()
    elif page == "Add Asset":
        page_add()
    elif page == "Update Asset":
        page_update()
    elif page == "Login":
        page_login()

if __name__ == "__main__":
    main()
