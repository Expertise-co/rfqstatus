import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(page_title="RFQ Sheet Manager", layout="wide")

SPREADSHEET_ID = "16dyupQvFCgPxCez-zKj3mgl62tIH2jR2sYahYS7D8U8"
SHEET_NAME = "Sheet1"

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

creds = connect_to_google()
sheets_api = build("sheets", "v4", credentials=creds)
drive_api = build("drive", "v3", credentials=creds)

# ---------------------- READ SHEET ---------------------- #
def load_sheet():
    result = sheets_api.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:Z"
    ).execute()

    values = result.get("values", [])
    if not values:
        return pd.DataFrame()

    df = pd.DataFrame(values[1:], columns=values[0])
    return df

# ---------------------- CLEAR SHEET ---------------------- #
def clear_sheet():
    sheets_api.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:Z"
    ).execute()

# ---------------------- WRITE SHEET ---------------------- #
def write_sheet(df):
    values = [df.columns.tolist()] + df.values.tolist()

    sheets_api.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1",
        valueInputOption="RAW",
        body={"values": values}
    ).execute()


# ---------------------- UI ---------------------- #
st.title("📊 RFQ Google Sheet Manager (Read + Replace)")

st.subheader("Current Google Sheet Data")
df = load_sheet()

if df.empty:
    st.warning("No data found in Google Sheet!")
else:
    st.dataframe(df, use_container_width=True)


st.subheader("Upload CSV to Replace Sheet")

uploaded_csv = st.file_uploader("Upload a new CSV file", type=["csv"])

if uploaded_csv is not None:
    new_df = pd.read_csv(uploaded_csv)
    st.write("### Preview of uploaded file:")
    st.dataframe(new_df, use_container_width=True)

    if st.button("Replace Google Sheet with this CSV"):
        clear_sheet()
        write_sheet(new_df)
        st.success("Google Sheet successfully replaced!")
        st.experimental_rerun()
