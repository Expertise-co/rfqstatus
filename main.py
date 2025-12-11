import streamlit as st
import pandas as pd
import altair as alt
from google.oauth2 import service_account
from googleapiclient.discovery import build

# -----------------------------------------------------
# Make Screen Wide
# -----------------------------------------------------
st.set_page_config(layout="wide")

# -----------------------------------------------------
# Modern UI Styling + Gradient Sidebar + KPI Cards
# -----------------------------------------------------
modern_style = """
<style>
#MainMenu {visibility: hidden;}
#header {visibility: hidden;}
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

# -----------------------------------------------------
# GOOGLE SHEETS CONFIG
# -----------------------------------------------------
SPREADSHEET_ID = "16dyupQvFCgPxCez-zKj3mgl62tIH2jR2sYahYS7D8U8"
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
    df = pd.DataFrame(values[1:], columns=values[0])
    return df

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
st.sidebar.header("🔎 Filter Options")

# Multi-select Division
division_list = sorted(df['Division'].dropna().unique())
selected_divisions = st.sidebar.multiselect("Select Division(s)", options=division_list, default=division_list)

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

# Final Filtering
filtered_df = df.copy()
if selected_divisions:
    filtered_df = filtered_df[filtered_df['Division'].isin(selected_divisions)]
if selected_client != "All":
    filtered_df = filtered_df[filtered_df['Clients'] == selected_client]
if selected_affiliate != "All":
    filtered_df = filtered_df[filtered_df['Affiliate'] == selected_affiliate]

# ---------------------- SIDEBAR: UPLOAD ---------------------- #


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

else:
    st.warning("⚠️ No data found for the selected filters.")



