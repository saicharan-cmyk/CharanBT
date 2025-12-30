import streamlit as st
import requests
import pandas as pd
import csv
import io

# ================= DEFAULT CONFIG =================
DEFAULT_AUTH_URL = "https://saas-beeforce.labour.tech/authorization-server/oauth/token"
DEFAULT_BASE_URL = "https://saas-beeforce.labour.tech/resource-server/api/shift_templates"
DEFAULT_START_DATE = "2026-01-01"

CLIENT_AUTH = st.secrets["CLIENT_AUTH"]

# ================= SESSION STATE =================
if "token" not in st.session_state:
    st.session_state.token = None

if "username" not in st.session_state:
    st.session_state.username = None

if "final_body" not in st.session_state:
    st.session_state.final_body = []

if "show_settings" not in st.session_state:
    st.session_state.show_settings = False

if "AUTH_URL" not in st.session_state:
    st.session_state.AUTH_URL = DEFAULT_AUTH_URL

if "BASE_URL" not in st.session_state:
    st.session_state.BASE_URL = DEFAULT_BASE_URL

if "START_DATE" not in st.session_state:
    st.session_state.START_DATE = DEFAULT_START_DATE

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="Shift Templates",
    layout="wide"
)

# ================= TOP BAR =================
col1, col2 = st.columns([0.9, 0.1])

with col1:
    st.title("🕒 Shift Template Configuration")

with col2:
    if st.button("⚙️", help="Settings"):
        st.session_state.show_settings = not st.session_state.show_settings

# ================= SETTINGS PANEL =================
if st.session_state.show_settings:
    st.markdown("### ⚙️ API Configuration")
    st.session_state.AUTH_URL = st.text_input("Auth URL", st.session_state.AUTH_URL)
    st.session_state.BASE_URL = st.text_input("Shift Template Base URL", st.session_state.BASE_URL)
    st.session_state.START_DATE = st.text_input(
        "Start Date (YYYY-MM-DD)",
        st.session_state.START_DATE
    )
    st.divider()

# ================= LOGIN =================
if not st.session_state.token:
    st.header("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Generate Token"):
        try:
            payload = {
                "username": username,
                "password": password,
                "grant_type": "password"
            }

            headers = {
                "Authorization": CLIENT_AUTH,
                "Content-Type": "application/x-www-form-urlencoded"
            }

            r = requests.post(
                st.session_state.AUTH_URL,
                data=payload,
                headers=headers
            )

            if r.status_code != 200:
                st.error("❌ Invalid credentials")
            else:
                st.session_state.token = r.json()["access_token"]
                st.session_state.username = username
                st.success("✅ Login successful")
                st.rerun()

        except Exception:
            st.error("❌ Authentication failed")

    st.stop()

# ================= AUTH HEADER =================
headers_auth = {
    "Authorization": f"Bearer {st.session_state.token}",
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json"
}

# ================= USER INFO =================
st.success(f"👤 Logged in as **{st.session_state.username}**")

if st.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

st.divider()

# ================= INSTRUCTIONS =================
st.info(
    "**To create a Shift Template, do not enter the ID.**\n\n"
    "**To update an existing Shift Template, enter the ID.**"
)

# ================= UPLOAD SECTION =================
st.header("📤 Upload Shift Templates File")

template_df = pd.DataFrame(columns=[
    "id",
    "Shift Template Name",
    "Description",
    "shift_code_id",
    "shift_name",
    "shift_date(DD-MM-YYYY)",
    "repeatWeek",
    "repeatWeekday"
])

st.download_button(
    "⬇️ Download Upload Template",
    template_df.to_csv(index=False),
    file_name="shift_templates_template.csv",
    mime="text/csv"
)

uploaded_file = st.file_uploader(
    "Upload CSV or Excel file",
    type=["csv", "xlsx", "xls"]
)

if uploaded_file:
    store = {}

    if uploaded_file.name.endswith(".csv"):
        reader = csv.DictReader(
            io.StringIO(uploaded_file.getvalue().decode("utf-8"))
        )
        rows = list(reader)
    else:
        df = pd.read_excel(uploaded_file)
        rows = df.fillna("").to_dict(orient="records")

    for row in rows:
        raw_id = str(row.get("id", "")).strip()
        name = str(row.get("Shift Template Name", "")).strip()
        description = str(row.get("Description", "")).strip() or name
        shift_code_id = int(row.get("shift_code_id"))
        shift_name = str(row.get("shift_name", "")).strip()
        shift_date = str(row.get("shift_date(DD-MM-YYYY)", "")).strip()
        repeat_week = str(row.get("repeatWeek", "")).strip() or "*"
        repeat_weekday = str(row.get("repeatWeekday", "")).strip() or "*"

        if not name or not shift_name or not shift_date:
            continue

        day, month, year = shift_date.split("-")
        unique_key = raw_id if raw_id else name

        if unique_key not in store:
            base = {
                "name": name,
                "description": description,
                "shiftCode": {"id": shift_code_id},
                "schedules": []
            }
            if raw_id:
                base["id"] = int(raw_id)

            store[unique_key] = base

        store[unique_key]["schedules"].append({
            "name": shift_name,
            "startDate": st.session_state.START_DATE,
            "repeatDay": int(day),
            "repeatMonth": int(month),
            "repeatYear": int(year),
            "repeatWeek": repeat_week,
            "repeatWeekday": repeat_weekday
        })

    st.session_state.final_body = list(store.values())
    st.success(f"✅ File processed. Total Shift Templates: {len(st.session_state.final_body)}")

# ================= CREATE / UPDATE =================
st.header("🚀 Create / Update Shift Templates")

if st.button("Submit Shift Templates"):
    success = 0
    failed = 0

    for payload in st.session_state.final_body:
        try:
            if payload.get("id"):
                r = requests.put(
                    f"{st.session_state.BASE_URL}/{payload['id']}",
                    headers=headers_auth,
                    json=payload
                )
                if r.status_code in (200, 201):
                    success += 1
                    st.write(f"✅ Updated Shift Template ID {payload['id']}")
                else:
                    failed += 1
            else:
                r = requests.post(
                    st.session_state.BASE_URL,
                    headers=headers_auth,
                    json=payload
                )
                if r.status_code in (200, 201):
                    success += 1
                    st.write(f"✅ Created Shift Template ID {r.json().get('id')}")
                else:
                    failed += 1
        except Exception:
            failed += 1

    st.info(f"Summary → Success: {success}, Failed: {failed}")

# ================= DELETE =================
st.header("🗑️ Delete Shift Templates")

ids_input = st.text_input("Enter Shift Template IDs (comma-separated)")

if st.button("Delete Shift Templates"):
    ids = [i.strip() for i in ids_input.split(",") if i.strip().isdigit()]

    for sid in ids:
        r = requests.delete(
            f"{st.session_state.BASE_URL}/{sid}",
            headers=headers_auth
        )
        if r.status_code in (200, 204):
            st.write(f"✅ Shift Template deleted {sid}")
        else:
            st.write(f"❌ Failed to delete {sid}")

# ================= FETCH & DOWNLOAD =================
st.header("⬇️ Download Existing Shift Templates")

if st.button("Download Existing Shift Templates"):
    r = requests.get(st.session_state.BASE_URL, headers=headers_auth)

    if r.status_code != 200:
        st.error("❌ Failed to fetch Shift Templates")
    else:
        rows = []

        for template in r.json():
            for sch in template.get("schedules", []):
                date = f"{int(sch['repeatDay']):02d}-{int(sch['repeatMonth']):02d}-{int(sch['repeatYear'])}"

                rows.append({
                    "id": template.get("id"),
                    "name": template.get("name"),
                    "description": template.get("description"),
                    "shift_code_id": template.get("shiftCode", {}).get("id"),
                    "shift_name": sch.get("name"),
                    "shift_date(DD-MM-YYYY)": date
                })

        df = pd.DataFrame(rows)
        csv_data = df.to_csv(index=False)

        st.download_button(
            "⬇️ Download CSV",
            csv_data,
            "shift_templates_export.csv",
            "text/csv"
        )
