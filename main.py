import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.title("Google Sheets RFQ Data Editor")

# ---------------------------------------------
# Service Account Authentication
# ---------------------------------------------
@st.cache_resource
def connect_to_google():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ],
    )
    return creds

creds = connect_to_google()

# Google Sheets API
sheets_api = build("sheets", "v4", credentials=creds)

SHEET_ID = "16dyupQvFCgPxCez-zKj3mgl62tIH2jR2sYahYS7D8U8"
RANGE = "Sheet1!A:Z"   # Change if needed

# ---------------------------------------------
# Load Data from Google Sheet
# ---------------------------------------------
def load_sheet():
    result = sheets_api.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=RANGE
    ).execute()

    values = result.get("values", [])
    df = pd.DataFrame(values[1:], columns=values[0])
    return df

df = load_sheet()
st.subheader("Current RFQ Data")
st.dataframe(df, use_container_width=True)

# ---------------------------------------------
# Upload New CSV to Replace Sheet Data
# ---------------------------------------------
st.subheader("Upload New CSV to Replace Google Sheet")

uploaded = st.file_uploader("Upload CSV file", type=["csv"])

if uploaded:
    new_df = pd.read_csv(uploaded)

    st.write("Preview of New File:")
    st.dataframe(new_df)

    if st.button("Replace Google Sheet Data"):
        # Convert to Google Sheets format
        data = [new_df.columns.tolist()] + new_df.astype(str).values.tolist()

        sheets_api.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=RANGE,
            valueInputOption="RAW",
            body={"values": data}
        ).execute()

        st.success("Google Sheet updated successfully!")
        st.balloons()


