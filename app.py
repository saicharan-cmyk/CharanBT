import streamlit as st
import requests
import pandas as pd
import json
import io

# ================= DEFAULT CONFIG =================
DEFAULT_AUTH_URL = "https://saas-beeforce.labour.tech/authorization-server/oauth/token"
DEFAULT_BASE_URL = "https://saas-beeforce.labour.tech/resource-server/api/shift_templates"

# CLIENT_AUTH must be in Streamlit Secrets in TOML:
# CLIENT_AUTH = "Basic <your_base64_clientid_clientsecret>"
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

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Shift Templates", layout="wide")

# ================= TOP BAR =================
col1, col2 = st.columns([0.9, 0.1])
with col1:
    st.title("🧾 Shift Templates Management")
with col2:
    if st.button("⚙️ Settings"):
        st.session_state.show_settings = not st.session_state.show_settings

# ================= SETTINGS =================
if st.session_state.show_settings:
    st.markdown("### ⚙️ API Configuration")
    st.session_state.AUTH_URL = st.text_input("Auth URL", st.session_state.AUTH_URL)
    st.session_state.BASE_URL = st.text_input("Base URL", st.session_state.BASE_URL)
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
            headers = {"Authorization": CLIENT_AUTH, "Content-Type": "application/x-www-form-urlencoded"}
            r = requests.post(st.session_state.AUTH_URL, data=payload, headers=headers)
            if r.status_code != 200:
                st.error("❌ Invalid credentials")
            else:
                st.session_state.token = r.json()["access_token"]
                st.session_state.username = username
                st.success("✅ Login successful")
                st.rerun()
        except Exception:
            st.error("❌ Invalid credentials")
    st.stop()

# ================= AUTH HEADER =================
headers_auth = {
    "Authorization": f"Bearer {st.session_state.token}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# ================= USER INFO =================
st.success(f"👤 Logged in as **{st.session_state.username}**")
if st.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()
st.divider()

# ================= UPLOAD =================
st.header("📤 Upload Shift Templates File")

# CSV Template Columns
template_df = pd.DataFrame(columns=[
    "id", "name", "description",
    "startTime", "endTime",
    "beforeStartToleranceMinute", "afterStartToleranceMinute",
    "report", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "paycodes"
])

st.download_button(
    "⬇️ Download CSV Template",
    template_df.to_csv(index=False),
    file_name="shift_templates_template.csv",
    mime="text/csv"
)

uploaded_file = st.file_uploader("Upload CSV/Excel file", type=["csv", "xlsx", "xls"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    df.fillna("", inplace=True)
    final_body = []

    for _, row in df.iterrows():
        try:
            shift_template = {
                "name": row["name"],
                "description": row.get("description", row["name"]),
                "startTime": row.get("startTime", "1970-01-01 06:00:00"),
                "endTime": row.get("endTime", "1970-01-01 15:00:00"),
                "beforeStartToleranceMinute": int(row.get("beforeStartToleranceMinute", 0)),
                "afterStartToleranceMinute": int(row.get("afterStartToleranceMinute", 0)),
                "report": bool(row.get("report", False)),
                "monday": bool(row.get("monday", False)),
                "tuesday": bool(row.get("tuesday", False)),
                "wednesday": bool(row.get("wednesday", False)),
                "thursday": bool(row.get("thursday", False)),
                "friday": bool(row.get("friday", False)),
                "saturday": bool(row.get("saturday", False)),
                "sunday": bool(row.get("sunday", False)),
                "paycodes": json.loads(row.get("paycodes", "[]"))  # JSON string in CSV
            }
            if row.get("id"):
                shift_template["id"] = int(row["id"])
            final_body.append(shift_template)
        except Exception as e:
            st.warning(f"Skipped row due to error: {e}")

    st.session_state.final_body = final_body
    st.success(f"✅ Processed {len(final_body)} Shift Templates")

# ================= CREATE / UPDATE =================
st.header("🚀 Create / Update Shift Templates")

if st.button("Submit Shift Templates"):
    success, failed = 0, 0
    for payload in st.session_state.final_body:
        try:
            if "id" in payload:
                r = requests.put(f"{st.session_state.BASE_URL}/{payload['id']}", headers=headers_auth, json=payload)
            else:
                r = requests.post(st.session_state.BASE_URL, headers=headers_auth, json=payload)
            if r.status_code in (200, 201):
                success += 1
                st.write(f"✅ Processed ID {r.json().get('id') or payload.get('id')}")
            else:
                failed += 1
                st.write(f"❌ Failed: {r.status_code}, {r.text}")
        except Exception as e:
            failed += 1
            st.write(f"❌ Exception: {e}")
    st.info(f"Summary → Success: {success}, Failed: {failed}")

# ================= DELETE =================
st.header("🗑️ Delete Shift Templates")
ids_input = st.text_input("Enter Shift Template IDs (comma-separated)")
if st.button("Delete Shift Templates"):
    ids = [i.strip() for i in ids_input.split(",") if i.strip().isdigit()]
    for pid in ids:
        r = requests.delete(f"{st.session_state.BASE_URL}/{pid}", headers=headers_auth)
        if r.status_code in (200, 204):
            st.write(f"✅ Deleted ID {pid}")
        else:
            st.write(f"❌ Failed to delete ID {pid}, {r.text}")

# ================= FETCH & DOWNLOAD =================
st.header("⬇️ Download Existing Shift Templates")
if st.button("Download Existing Shift Templates"):
    r = requests.get(st.session_state.BASE_URL, headers=headers_auth)
    if r.status_code != 200:
        st.error(f"❌ Failed to fetch Shift Templates: {r.status_code}")
    else:
        rows = []
        for template in r.json():
            paycodes_str = json.dumps(template.get("paycodes", []))
            rows.append({
                "id": template.get("id"),
                "name": template.get("name"),
                "description": template.get("description"),
                "startTime": template.get("startTime"),
                "endTime": template.get("endTime"),
                "beforeStartToleranceMinute": template.get("beforeStartToleranceMinute"),
                "afterStartToleranceMinute": template.get("afterStartToleranceMinute"),
                "report": template.get("report"),
                "monday": template.get("monday"),
                "tuesday": template.get("tuesday"),
                "wednesday": template.get("wednesday"),
                "thursday": template.get("thursday"),
                "friday": template.get("friday"),
                "saturday": template.get("saturday"),
                "sunday": template.get("sunday"),
                "paycodes": paycodes_str
            })
        df = pd.DataFrame(rows)
        st.download_button(
            label="⬇️ Download CSV",
            data=df.to_csv(index=False),
            file_name="shift_templates_export.csv",
            mime="text/csv"
        )
