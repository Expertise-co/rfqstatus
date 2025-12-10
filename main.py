import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ---------------------- CONFIG ---------------------- #
SPREADSHEET_ID = "16dyupQvFCgPxCez-zKj3mgl62tIH2jR2sYahYS7D8U8"
RANGE = "rfq_2025!A:Z"  # Correct sheet range

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

# Show existing data
df = load_sheet()
st.subheader("Loaded Data")
st.dataframe(df)

# ---------------------- UPLOAD FUNCTION ---------------------- #
st.subheader("Upload CSV to update sheet")
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    # Read uploaded CSV
    upload_df = pd.read_csv(uploaded_file)
    st.subheader("Uploaded Data Preview")
    st.dataframe(upload_df)

    # Optional: write to Google Sheets
    if st.button("Upload to Google Sheets"):
        creds = connect_to_google()
        sheets_api = build("sheets", "v4", credentials=creds)
        
        # Prepare values
        values = [upload_df.columns.tolist()] + upload_df.values.tolist()
        body = {"values": values}

        sheets_api.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE,
            valueInputOption="RAW",
            body=body
        ).execute()

        st.success("Data uploaded successfully!")
