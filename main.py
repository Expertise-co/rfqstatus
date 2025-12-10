import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ---------------------- GOOGLE CONNECTION ---------------------- #
@st.cache_resource
def connect_to_google():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return creds

creds = connect_to_google()
sheets_api = build("sheets", "v4", credentials=creds)
drive_api = build("drive", "v3", credentials=creds)

SPREADSHEET_ID = "16dyupQvFCgPxCez-zKj3mgl62tIH2jR2sYahYS7D8U8"
RANGE = "Sheet1!A1:Z"   # FIXED RANGE (no A:Z error)

# ---------------------- LOAD DATA ---------------------- #
@st.cache_data
def load_sheet():
    result = (
        sheets_api.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=RANGE)
        .execute()
    )

    values = result.get("values", [])

    if not values:
        st.error("No data found in sheet.")
        return pd.DataFrame()

    df = pd.DataFrame(values[1:], columns=values[0])
    return df


# ---------------------- APP ---------------------- #
st.title("Google Sheets Data Loader")

df = load_sheet()

st.subheader("Loaded Data")
st.dataframe(df)
