import streamlit as st
import pandas as pd
import altair as alt
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime

# -----------------------------------------------------
# Make Screen Wide
# -----------------------------------------------------
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded")

# -----------------------------------------------------
# Load passwords from Streamlit Secrets
# -----------------------------------------------------

GLOBAL_PASSWORD = st.secrets["GLOBAL_PASSWORD"]
DIVISION_PASSWORDS = dict(st.secrets["DIVISION_PASSWORDS"])


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user_division" not in st.session_state:
    st.session_state.user_division = None

# -----------------------------------------------------
# Modern UI Styling + Gradient Sidebar + KPI Cards
# -----------------------------------------------------
modern_style = """
<style>
MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
:root { color-scheme: light !important; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
    background: #ffffff !important; color: #2c3e50 !important;
}
html { filter: invert(0) !important; }
body { background-color: #f4f6ff !important; }
h1 { color: #2c3e50; font-weight: 800 !important; padding-bottom: 10px; }
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e272e 0%, #2f3542 100%) !important;
}
section[data-testid="stSidebar"] * { color: white !important; }
div[data-baseweb="select"] div { background-color: #2f3640 !important; color: white !important; }
div[data-baseweb="select"] span { color: white !important; }
ul[role="listbox"] li { color: black !important; }
.kpi-card { background: white; padding: 18px; border-radius: 14px; box-shadow: 0px 4px 10px rgba(0,0,0,0.08); text-align: center; border-left: 6px solid #4b7bec; }
.kpi-title { color: #576574; font-size: 16px; font-weight: 600; }
.kpi-value { color: #2d3436; font-size: 32px; font-weight: 800; margin-top: -5px; }
[data-testid="stDataFrame"] { background: white !important; border: 1.5px solid #dcdde1 !important; border-radius: 12px !important; padding: 12px !important; box-shadow: 0px 4px 12px rgba(0,0,0,0.06) !important; }
h3, h4 { color: #2c3e50 !important; font-weight: 700 !important; }
</style>
"""
st.markdown(modern_style, unsafe_allow_html=True)

st.markdown("""
<style>
/* Sidebar login input text */
section[data-testid="stSidebar"] input {
    color: #000000 !important;
    background-color: #ffffff !important;
}

/* Sidebar login button text */
section[data-testid="stSidebar"] button {
    color: #000000 !important;
    background-color: #2196F3 !important;
    font-weight: 600;
}

/* Button hover (optional) */
section[data-testid="stSidebar"] button:hover {
    background-color: #1976D2 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ---------- Sidebar Upload Section Fix ---------- */

/* File uploader label */
section[data-testid="stSidebar"] label {
    color: #2c3e50 !important;
    font-weight: 600;
}

/* File uploader drop area */
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    background-color: #ffffff !important;
    color: #2c3e50 !important;
    border: 2px dashed #4b7bec !important;
    border-radius: 10px !important;
}

/* File uploader text */
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {
    color: #2c3e50 !important;
}

/* Sidebar dataframe preview */
section[data-testid="stSidebar"] [data-testid="stDataFrame"] {
    background-color: #ffffff !important;
    color: #2c3e50 !important;
}

/* Radio buttons */
section[data-testid="stSidebar"] div[role="radiogroup"] label {
    color: #2c3e50 !important;
}

/* Confirm upload button */
section[data-testid="stSidebar"] button[kind="primary"] {
    background-color: #4b7bec !important;
    color: #4b7bec !important;
    font-weight: 600;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------
# GOOGLE SHEETS CONFIG
# -----------------------------------------------------
SPREADSHEET_ID = st.secrets["DRIVE_SHEET_ID"]
RANGE = "rfq_2025.csv"  # Full range

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

    result = sheets_api.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE
    ).execute()

    values = result.get("values", [])
    if not values:
        return pd.DataFrame()

    return pd.DataFrame(values[1:], columns=values[0])

@st.cache_data
def get_csv_last_modified_time():
    creds = connect_to_google()
    drive_service = build("drive", "v3", credentials=creds)

    file = drive_service.files().get(
        fileId=SPREADSHEET_ID,
        fields="modifiedTime"
    ).execute()

    modified_time = file["modifiedTime"]
    return datetime.fromisoformat(modified_time.replace("Z", "")).strftime(
        "%d-%b-%Y"
    )

# -----------------------------------------------------
# Load Data from Google Sheets
# -----------------------------------------------------
df = load_sheet()

df['Division'] = df['Division'].astype(str).str.strip()
df['Clients'] = df['Clients'].astype(str).str.strip()
df['Affiliate'] = df['Affiliate'].astype(str).str.strip()
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

# -----------------------------------------------------
# DASHBOARD UI
# -----------------------------------------------------
st.title("📊 RFQ Status Dashboard")
try:
    last_upload = get_csv_last_modified_time()
    st.sidebar.info(f"📅 Last Upload:\n{last_upload}")
except Exception:
    st.sidebar.warning("📅 Last Upload:\nNot available")

if st.sidebar.button("🔄 Refresh Data"):
    load_sheet.clear()
    get_csv_last_modified_time.clear()
    st.rerun()

# -----------------------------------------------------
# Sidebar Login
# -----------------------------------------------------
if not st.session_state.authenticated:
    st.sidebar.title("🔐 Login")

    password_input = st.sidebar.text_input(
        "Enter Password",
        type="password"
    )

    login_btn = st.sidebar.button("Login")

    if login_btn:
        if password_input == GLOBAL_PASSWORD:
            st.session_state.authenticated = True
            st.session_state.user_division = None
            st.rerun()

        elif password_input in DIVISION_PASSWORDS.values():
            division = [
                d for d, p in DIVISION_PASSWORDS.items()
                if p == password_input
            ][0]
        
            st.session_state.authenticated = True
            st.session_state.user_division = division
            st.rerun()
        else:
            st.sidebar.error("Incorrect password ❌")

    st.stop()

#st.sidebar.success("Logged in")

st.sidebar.header("🔎 Filter Options")

# --------------------------------------------------------
# 🔵 DIVISION FILTER (Restricted)
# --------------------------------------------------------

if st.session_state.user_division:
    selected_divisions = [st.session_state.user_division]
    st.sidebar.markdown(
        f"""
        <div style="
            background-color: #2196F3;
            color: #ff0022;
            padding: 10px 12px;
            border-radius: 8px;
            font-weight: 700;
            margin-top: 8px;
            border-left: 5px solid #4b7bec;
        ">
            🔒 Division Locked<br> <span style="font-size: 14px;">{st.session_state.user_division}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

else:
    # Global user → full access
    division_list = sorted(df['Division'].dropna().unique())

    selected_divisions = st.sidebar.multiselect(
        "Select Division(s)",
        options=division_list,
        default=division_list
    )

# Client Dropdown
if selected_divisions:
    filtered_clients = sorted(df[df['Division'].isin(selected_divisions)]['Clients'].dropna().unique())
else:
    filtered_clients = sorted(df['Clients'].dropna().unique())
client_list = ["All"] + filtered_clients
selected_client = st.sidebar.selectbox("Select Client", client_list)

# Affiliate Dropdown
if selected_client == "All":
    filtered_affiliates = sorted(df[df['Division'].isin(selected_divisions)]['Affiliate'].dropna().unique())
else:
    filtered_affiliates = sorted(
        df[(df['Division'].isin(selected_divisions)) & (df['Clients'] == selected_client)]['Affiliate'].dropna().unique()
    )
affiliate_list = ["All"] + filtered_affiliates
selected_affiliate = st.sidebar.selectbox("Select Affiliate", affiliate_list)


if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticated = False
    st.session_state.user_division = None
    st.rerun()


# Final Filtering
filtered_df = df.copy()
if selected_divisions:
    filtered_df = filtered_df[filtered_df['Division'].isin(selected_divisions)]
if selected_client != "All":
    filtered_df = filtered_df[filtered_df['Clients'] == selected_client]
if selected_affiliate != "All":
    filtered_df = filtered_df[filtered_df['Affiliate'] == selected_affiliate]

# ---------------------- SIDEBAR: UPLOAD ---------------------- #
if st.session_state.get("user_division") is None:

    st.sidebar.markdown("---")
    st.sidebar.header("📤 Upload Options")

    uploaded_file = st.sidebar.file_uploader(
        "Upload RFQ file",
        type="csv"
    )

    if uploaded_file:
        upload_df = pd.read_csv(uploaded_file)
        st.sidebar.subheader("Preview of Uploaded CSV")
        st.sidebar.dataframe(upload_df.head(5))

        upload_action = st.sidebar.radio(
            "Choose Upload Action",
            options=["Replace Sheet", "Append to Sheet"]
        )

        if st.sidebar.button("Confirm Upload"):

            creds = connect_to_google()
            sheets_api = build("sheets", "v4", credentials=creds)

            values = [upload_df.columns.tolist()] + upload_df.values.tolist()
            body = {"values": values}

            # REPLACE SHEET
            if upload_action == "Replace Sheet":
                sheets_api.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=RANGE,
                    valueInputOption="RAW",
                    body=body
                ).execute()
                st.sidebar.success(f"✅ Sheet replaced with {len(upload_df)} rows")

            # APPEND TO SHEET
            else:
                sheets_api.spreadsheets().values().append(
                    spreadsheetId=SPREADSHEET_ID,
                    range=RANGE,
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"values": upload_df.values.tolist()}
                ).execute()
                st.sidebar.success(f"✅ {len(upload_df)} rows appended successfully")

# Status Count + KPI Cards
if not filtered_df.empty:
    status_counts = filtered_df['Status'].value_counts()
    status_percentage = (status_counts / status_counts.sum()) * 100
    result_df = pd.DataFrame({
        "Status": status_counts.index,
        "RFQ Count": status_counts.values,
        "Percentage (%)": status_percentage.round(2).values
    }).reset_index(drop=True)

    total_rfqs = filtered_df.shape[0]
    awarded = filtered_df[filtered_df['Status'].str.lower() == "awarded"].shape[0]
    submitted = filtered_df[filtered_df['Status'].str.lower() == "submitted"].shape[0]
    declined = filtered_df[filtered_df['Status'].str.lower() == "declined"].shape[0]

    awarded_ratio = (awarded / total_rfqs) * 100 if submitted > 0 else 0
    declined_ratio = (declined / total_rfqs) * 100 if total_rfqs > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">Total RFQs</div><div class="kpi-value">{total_rfqs}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">Awarded Ratio</div><div class="kpi-value">{awarded_ratio:.2f}%</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">Declined Ratio</div><div class="kpi-value">{declined_ratio:.2f}%</div></div>', unsafe_allow_html=True)

    st.subheader("📌 RFQ Status Breakdown")
    st.dataframe(result_df, use_container_width=True, hide_index=True)

    st.subheader("📊 Status Distribution Chart")
    chart = alt.Chart(result_df).mark_bar(color="#4f80ff").encode(
        x=alt.X('Status:N', axis=alt.Axis(labelAngle=0)),
        y='Percentage (%):Q',
        tooltip=['Status', 'RFQ Count', 'Percentage (%)']
    ).properties(height=400)
    st.altair_chart(chart, use_container_width=True)

    st.subheader("📈 RFQ Trend Over Time")
    trend_df = filtered_df.dropna(subset=['Date'])
    trend_df['Month'] = trend_df['Date'].dt.to_period('M').astype(str)
    monthly_counts = trend_df.groupby("Month").size()
    st.line_chart(monthly_counts)

        # ---------------------------
    # Client–Affiliate RFQ Count Table
    # ---------------------------
    st.subheader("📋 RFQs Received by Client & Affiliate")

    client_affiliate_df = (
        filtered_df
        .groupby(['Clients', 'Affiliate'])
        .size()
        .reset_index(name='RFQ Count')
        .sort_values('RFQ Count', ascending=False)
    )

    if not client_affiliate_df.empty:
        st.dataframe(
            client_affiliate_df,
            use_container_width=True,
            hide_index=True
        )  
    else:
        st.info("No RFQs found for the selected Client/Affiliate filters.")       
else:
    st.warning("⚠️ No data found for the selected filters.")
    









