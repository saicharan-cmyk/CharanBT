import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Shift Templates", layout="wide")
st.title("Shift Templates")

API_URL = "https://saas-beeforce.labour.tech/resource-server/api/shift_templates/"

if st.button("Load Shift Templates"):
    with st.spinner("Calling API..."):
        response = requests.get(API_URL)

    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.error(f"API Error: {response.status_code}")
        st.text(response.text)
