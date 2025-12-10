import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ---------------------- CONFIG ---------------------- #
SPREADSHEET_ID = "16dyupQvFCgPxCez-zKj3mgl62tIH2jR2sYahYS7D8U8"
RANGE = "rfq_2025!A1:Z"   # ✅ Correct sheet name

# ---------------------- GOOGLE CONNECTION ---------------------- #
@st.cache_resource
def connect_to_google():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    return creds

# ---------------------- LOAD SHEET ---------------------- #
@st.cache_data
def load_sheet():
    creds = connect_to_google()
    sheets_api = build("sheets", "v4", credentials=creds)

    result = (
        sheets_api.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=RANGE)
        .execute()
    )

    values = result.get("values", [])

    if not values:
        return pd.DataFrame()

    df = pd.DataFrame(values[1:], columns=values[0])
    return df

# ---------------------- APP ---------------------- #
st.title("Google Sheets Data Loader")

df = load_sheet()

st.subheader("Loaded Data")
st.dataframe(df)
