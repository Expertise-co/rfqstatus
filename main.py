import hmac
import streamlit as st
import pandas as pd
import altair as alt
from google.oauth2 import service_account
from googleapiclient.discovery import build

alt.themes.enable("none")

st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="RFQ Dashboard",
    page_icon="📊"
)

# ─── Google Sheets config ─────────────────────────────────────────────────────
SPREADSHEET_ID = "16dyupQvFCgPxCez-zKj3mgl62tIH2jR2sYahYS7D8U8"
RANGE = "rfq_2025.csv"   # name of the tab in the Google Sheet
CACHE_TTL = 300          # seconds – dashboard re-reads the sheet at most every 5 min

# ─── Passwords ────────────────────────────────────────────────────────────────
# Preferred: keep these in Streamlit secrets (see notes) instead of in GitHub.
# The hard-coded values below are only a fallback so nothing breaks while you
# migrate – delete them once the secrets are set in Streamlit Cloud.
_FALLBACK_GLOBAL = "rfq@251$"
_FALLBACK_DIVISIONS = {
    "PMTA Sales Org":    "PM@TAst1",
    "E&I Sales Org.":    "stE&I521",
    "CSD Sales Org.":    "20!CSDsh",
    "E- Cube Sales Org": "E&CUBE67",
    "EMBS Sales Org.":   "M51BS&lm",
    "ISSD Sales Org.":   "IS25SDc$",
    "PSD Sales Org.":    "521@PS&D",
    "RSD Sales Org.":    "at@RSD61",
    "TSSD Sales Org.":   "TS@SDyo3",
    "ValVe Sales Org.":  "V71SDblu",
}

try:
    GLOBAL_PASSWORD = st.secrets["global_password"]
except Exception:
    GLOBAL_PASSWORD = _FALLBACK_GLOBAL

try:
    DIVISION_PASSWORDS = dict(st.secrets["division_passwords"])
except Exception:
    DIVISION_PASSWORDS = _FALLBACK_DIVISIONS

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_division" not in st.session_state:
    st.session_state.user_division = None

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Instrument+Serif&display=swap" rel="stylesheet">
<style>
:root {
    color-scheme: light !important;
    --bg-base:       #f4f6f9;
    --bg-card:       #ffffff;
    --border:        #e2e6ef;
    --border-strong: #cdd3e2;
    --accent:        #3d6b8e;
    --accent-light:  #eaf1f6;
    --accent-mid:    #b3cede;
    --green:         #1a7f5a;
    --green-light:   #e4f5ee;
    --red:           #c94030;
    --red-light:     #fcecea;
    --amber:         #b86e00;
    --amber-light:   #fef3e0;
    --slate:         #5c6e8a;
    --purple:        #6b52a1;
    --teal:          #1a7a82;
    --rose:          #a84060;
    --text-primary:  #1c2437;
    --text-secondary:#485068;
    --text-muted:    #8592a8;
    --shadow-sm:     0 1px 4px rgba(30,50,90,0.07);
    --shadow:        0 4px 18px rgba(30,50,90,0.10);
    --shadow-hover:  0 8px 30px rgba(30,50,90,0.14);
    --radius:        14px;
    --radius-sm:     8px;
}
* { box-sizing: border-box; }
#MainMenu, header, footer { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"] {
    display: flex !important;
    visibility: visible !important;
}
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
    background: var(--bg-base) !important;
    color: var(--text-primary) !important;
    font-family: 'DM Sans', sans-serif !important;
}
.main .block-container {
    padding: 2rem 2.5rem 3rem !important;
    max-width: 100% !important;
}
section[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: 2px 0 16px rgba(30,50,90,0.07) !important;
}
section[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
    font-family: 'DM Sans', sans-serif !important;
}
section[data-testid="stSidebar"] button,
section[data-testid="stSidebar"] button * {
    color: #ffffff !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: var(--text-muted) !important;
    border-bottom: 1px solid var(--border) !important;
    padding-bottom: 0.5rem !important;
    margin-bottom: 1rem !important;
}
section[data-testid="stSidebar"] input {
    background: var(--bg-base) !important;
    border: 1.5px solid var(--border-strong) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
}
section[data-testid="stSidebar"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(61,107,142,0.12) !important;
}
section[data-testid="stSidebar"] button {
    background: var(--accent) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    transition: all 0.2s !important;
}
section[data-testid="stSidebar"] button:hover {
    background: #2f5472 !important;
    box-shadow: 0 4px 14px rgba(61,107,142,0.28) !important;
}
div[data-baseweb="select"] > div {
    background: var(--bg-base) !important;
    border: 1.5px solid var(--border-strong) !important;
    border-radius: var(--radius-sm) !important;
}
div[data-baseweb="select"] span,
div[data-baseweb="select"] div {
    color: var(--text-primary) !important;
    background: var(--bg-base) !important;
}
ul[role="listbox"] {
    background: #ffffff !important;
    border: 1px solid var(--border-strong) !important;
    box-shadow: var(--shadow) !important;
    border-radius: var(--radius-sm) !important;
}
ul[role="listbox"] li { color: var(--text-primary) !important; }
ul[role="listbox"] li:hover { background: var(--accent-light) !important; }
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    background: var(--accent-light) !important;
    border: 2px dashed var(--accent-mid) !important;
    border-radius: var(--radius) !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {
    color: var(--accent) !important;
    opacity: 1 !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
    background: var(--accent) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    padding: 4px 14px !important;
    opacity: 1 !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button * {
    color: #ffffff !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small,
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] span {
    color: var(--text-secondary) !important;
    opacity: 1 !important;
}
[data-testid="stAlert"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text-secondary) !important;
}
h3 {
    font-family: 'DM Sans', sans-serif !important;
    color: var(--text-primary) !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em;
    margin-top: 2rem !important;
    margin-bottom: 1rem !important;
}
[data-testid="stDataFrame"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow-sm) !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] th {
    background: var(--bg-base) !important;
    color: var(--text-muted) !important;
    font-weight: 700 !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 10px 14px !important;
}
[data-testid="stDataFrame"] td {
    color: var(--text-primary) !important;
    font-size: 0.9rem !important;
    border-bottom: 1px solid var(--border) !important;
    padding: 9px 14px !important;
}
[data-testid="stDataFrame"] tr:hover td { background: var(--accent-light) !important; }
[data-testid="stVegaLiteChart"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow-sm) !important;
    padding: 1.25rem 1.25rem 0.5rem !important;
    overflow: hidden !important;
}
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
}
.page-title {
    font-family: 'DM Sans', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    line-height: 1;
}
.page-title span { color: var(--accent); font-style: italic; }
.page-subtitle { font-size: 0.85rem; color: var(--text-muted); margin-top: 0.35rem; }
.last-updated {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 30px;
    padding: 0.45rem 1.1rem;
    font-size: 0.78rem;
    color: var(--text-secondary);
    box-shadow: var(--shadow-sm);
    white-space: nowrap;
}
.last-updated strong { color: var(--accent); }
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.1rem;
    margin-bottom: 2rem;
}
.kpi-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.4rem 1.6rem 1.2rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    box-shadow: var(--shadow-sm);
}
.kpi-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-hover); border-color: var(--border-strong); }
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: var(--radius) var(--radius) 0 0;
}
.kpi-card.c-accent::before { background: var(--accent); }
.kpi-card.c-green::before  { background: var(--green); }
.kpi-card.c-red::before    { background: var(--red); }
.kpi-card.c-amber::before  { background: var(--amber); }
.kpi-bg-icon {
    position: absolute;
    right: 1.1rem; top: 0.9rem;
    font-size: 2rem;
    opacity: 0.90;
    user-select: none;
    line-height: 1;
    filter: saturate(0.8);
}
.kpi-label {
    font-size: 0.68rem; font-weight: 700;
    letter-spacing: 0.09em; text-transform: uppercase;
    color: var(--text-muted); margin-bottom: 0.55rem;
}
.kpi-value {
    font-family: 'Instrument Serif', serif;
    font-size: 2.3rem; font-weight: 400;
    color: var(--text-primary); line-height: 1; margin-bottom: 0.55rem;
}
.kpi-unit { font-family: 'DM Sans', sans-serif; font-size: 1rem; color: var(--text-secondary); }
.kpi-badge {
    display: inline-block; padding: 3px 10px;
    border-radius: 20px; font-size: 0.72rem; font-weight: 600;
}
.b-accent { background: var(--accent-light); color: var(--accent); }
.b-green  { background: var(--green-light);  color: var(--green); }
.b-red    { background: var(--red-light);     color: var(--red); }
.b-amber  { background: var(--amber-light);   color: var(--amber); }
.lock-badge {
    background: var(--accent-light);
    border: 1px solid var(--accent-mid);
    color: var(--accent);
    border-radius: var(--radius-sm);
    padding: 0.7rem 1rem;
    font-size: 0.85rem; font-weight: 500;
    margin-top: 0.5rem; line-height: 1.6;
}
.section-sep { height: 1px; background: var(--border); margin: 2rem 0; }
</style>
""", unsafe_allow_html=True)


# ─── Google Sheets helpers ────────────────────────────────────────────────────
@st.cache_resource
def connect_to_google():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )


@st.cache_data(ttl=CACHE_TTL, show_spinner="Loading data…")
def load_sheet():
    creds = connect_to_google()
    sheets_api = build("sheets", "v4", credentials=creds, cache_discovery=False)
    result = sheets_api.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE,
    ).execute()
    values = result.get("values", [])
    if len(values) < 2:
        return pd.DataFrame()

    header = [str(h).strip() for h in values[0]]
    n = len(header)
    # Google Sheets drops trailing empty cells -> pad / trim every row to header width
    rows = [(r + [""] * (n - len(r)))[:n] for r in values[1:]]
    return pd.DataFrame(rows, columns=header)


@st.cache_data(ttl=CACHE_TTL)
def get_last_modified_date():
    """Last time the Google Sheet file was modified (IST)."""
    try:
        creds = connect_to_google()
        drive_api = build("drive", "v3", credentials=creds, cache_discovery=False)
        meta = drive_api.files().get(
            fileId=SPREADSHEET_ID, fields="modifiedTime", supportsAllDrives=True
        ).execute()
        ts = pd.to_datetime(meta["modifiedTime"], utc=True).tz_convert("Asia/Kolkata")
        return ts.strftime("%d %b %Y, %H:%M")
    except Exception:
        return "Not available"


def replace_sheet_with(upload_df: pd.DataFrame):
    """Overwrite the whole sheet tab with the uploaded CSV."""
    creds = connect_to_google()
    sheets_api = build("sheets", "v4", credentials=creds, cache_discovery=False)
    upload_df = upload_df.fillna("").astype(str)
    values = [upload_df.columns.tolist()] + upload_df.values.tolist()

    # clear first so leftover old rows don't remain if the new file is shorter
    sheets_api.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID, range=RANGE, body={}
    ).execute()
    sheets_api.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE,
        valueInputOption="RAW",
        body={"values": values},
    ).execute()


def parse_dates(series: pd.Series) -> pd.Series:
    """Parse DD-MM-YYYY first; fall back to day-first parsing for anything else."""
    s = series.astype(str).str.strip()
    parsed = pd.to_datetime(s, format="%d-%m-%Y", errors="coerce")
    missing = parsed.isna() & s.ne("") & s.str.lower().ne("nan")
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(s[missing], dayfirst=True, errors="coerce")
    return parsed


# ─── Load data ────────────────────────────────────────────────────────────────
try:
    df = load_sheet()
except Exception as e:
    st.error(f"Could not load data from Google Sheets: {e}")
    st.stop()

if not df.empty:
    for col in ["Division", "Clients", "Affiliate", "Status"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    df["Date"] = parse_dates(df["Date"])
    df["Year"] = df["Date"].dt.year.astype("Int64")

# ─── Page Header ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align: center; margin-bottom: 1rem;">
    <div style="
        font-family: 'DM Sans', sans-serif;
        font-size: 0.75rem;
        color: #8592a8;
        padding: 0.4rem 1.2rem;
        background: #ffffff;
        border: 1px solid #e2e6ef;
        border-radius: 30px;
        letter-spacing: 0.03em;
        display: inline-block;
    ">
        Created by <strong style="color: #3d6b8e;">Chethan - Data Scientist</strong>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="page-header">
    <div>
        <div class="page-title">RFQ Status Dashboard</div>
        <div class="page-subtitle">Real-time overview of request-for-quotation activity across all divisions</div>
    </div>
    <div class="last-updated">🕐 Last updated: <strong>{get_last_modified_date()}</strong></div>
</div>
""", unsafe_allow_html=True)

# ─── Auth ─────────────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    st.sidebar.markdown("## 🔐 Sign In")
    password_input = st.sidebar.text_input("Password", type="password", placeholder="Enter your password")
    if st.sidebar.button("Sign In", use_container_width=True):
        if hmac.compare_digest(password_input, str(GLOBAL_PASSWORD)):
            st.session_state.authenticated = True
            st.session_state.user_division = None
            st.rerun()
        else:
            matched = [d for d, p in DIVISION_PASSWORDS.items()
                       if hmac.compare_digest(password_input, str(p))]
            if matched:
                st.session_state.authenticated = True
                st.session_state.user_division = matched[0]
                st.rerun()
            else:
                st.sidebar.error("Incorrect password. Please try again.")
    st.stop()

# ─── Empty-data guard ─────────────────────────────────────────────────────────
if df.empty:
    st.warning("⚠️ The Google Sheet has no data yet.")
    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_division = None
        st.rerun()
    st.stop()

# ─── Sidebar Filters ──────────────────────────────────────────────────────────
st.sidebar.markdown("## 🔎 Filters")

if st.session_state.user_division:
    selected_divisions = [st.session_state.user_division]
    st.sidebar.markdown(f"""
    <div class="lock-badge">
        🔒 <strong>Division locked</strong><br>
        <span style="font-size:0.8rem;opacity:0.85">{st.session_state.user_division}</span>
    </div>
    """, unsafe_allow_html=True)
else:
    division_list      = sorted(df['Division'].dropna().unique())
    selected_divisions = st.sidebar.multiselect("Division(s)", options=division_list, default=division_list)

available_years = sorted(int(y) for y in df['Year'].dropna().unique())
selected_year   = st.sidebar.selectbox("Year", options=['All'] + available_years, index=0)

filtered_clients = (
    sorted(df[df['Division'].isin(selected_divisions)]['Clients'].dropna().unique())
    if selected_divisions else sorted(df['Clients'].dropna().unique())
)
selected_client = st.sidebar.selectbox("Client", ["All"] + filtered_clients)

if selected_client == "All":
    filtered_affiliates = sorted(df[df['Division'].isin(selected_divisions)]['Affiliate'].dropna().unique())
else:
    filtered_affiliates = sorted(
        df[(df['Division'].isin(selected_divisions)) & (df['Clients'] == selected_client)]['Affiliate'].dropna().unique()
    )
selected_affiliate = st.sidebar.selectbox("Affiliate", ["All"] + filtered_affiliates)

st.sidebar.markdown("---")

# Upload (global admin only) -> writes to Google Sheets, not to local disk
if st.session_state.user_division is None:
    st.sidebar.markdown("## 📤 Upload Data")
    uploaded_file = st.sidebar.file_uploader("Upload RFQ CSV", type="csv")
    if uploaded_file and st.sidebar.button("✅ Confirm Upload", use_container_width=True):
        try:
            new_df = pd.read_csv(uploaded_file, dtype=str)
            required = {"Division", "Clients", "Affiliate", "Date", "Status"}
            missing_cols = required - set(new_df.columns.str.strip())
            if missing_cols:
                st.sidebar.error(f"Missing columns: {', '.join(sorted(missing_cols))}")
            else:
                replace_sheet_with(new_df)
                st.cache_data.clear()
                st.sidebar.success(f"Sheet replaced with {len(new_df):,} rows")
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Upload failed: {e}")
    st.sidebar.markdown("---")

if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.user_division = None
    st.rerun()

# ─── Apply Filters ────────────────────────────────────────────────────────────
filtered_df = df.copy()
if selected_divisions:
    filtered_df = filtered_df[filtered_df['Division'].isin(selected_divisions)]
if selected_client != "All":
    filtered_df = filtered_df[filtered_df['Clients'] == selected_client]
if selected_affiliate != "All":
    filtered_df = filtered_df[filtered_df['Affiliate'] == selected_affiliate]
if selected_year != "All":
    filtered_df = filtered_df[filtered_df['Year'] == selected_year]

# ─── Chart palette ────────────────────────────────────────────────────────────
CHART_BG = "#ffffff"
AXIS_C   = "#8592a8"
GRID_C   = "#eef0f5"
TEXT_C   = "#485068"
ACCENT   = "#3d6b8e"
GREEN    = "#1a7f5a"
RED      = "#c94030"
AMBER    = "#b86e00"
TEAL     = "#1a7a82"
PURPLE   = "#6b52a1"
SLATE    = "#5c6e8a"
ROSE     = "#a84060"
OLIVE    = "#6b7a3a"

STATUS_COLORS = {
    "Awarded":       GREEN,
    "Submitted":     ACCENT,
    "Declined":      RED,
    "Pending":       AMBER,
    "Lost":          ROSE,
    "Not Submitted": SLATE,
    "Under Process": PURPLE,
    "In Progress":   TEAL,
    "Cancelled":     "#94a3b8",
    "On Hold":       OLIVE,
}


def chart_cfg(c, h=380):
    return (
        c.properties(height=h, background=CHART_BG)
        .configure_view(strokeWidth=0, fill=CHART_BG)
        .configure_axis(
            labelColor=TEXT_C, titleColor=AXIS_C,
            gridColor=GRID_C, domainColor="#e2e6ef",
            tickColor="#e2e6ef", labelFont="DM Sans", titleFont="DM Sans",
            labelFontSize=11, titleFontSize=11, titlePadding=10, labelFontWeight=500
        )
        .configure_legend(
            labelColor=TEXT_C, titleColor=AXIS_C,
            labelFont="DM Sans", titleFont="DM Sans"
        )
    )


# ─── Main Content ─────────────────────────────────────────────────────────────
if not filtered_df.empty:

    status_counts  = filtered_df['Status'].value_counts()
    total_rfqs     = filtered_df.shape[0]
    awarded        = filtered_df[filtered_df['Status'].str.lower() == "awarded"].shape[0]
    submitted      = filtered_df[filtered_df['Status'].str.lower() == "submitted"].shape[0]
    declined       = filtered_df[filtered_df['Status'].str.lower() == "declined"].shape[0]
    awarded_ratio  = (awarded / submitted * 100) if submitted > 0 else 0
    declined_ratio = (declined / total_rfqs * 100) if total_rfqs > 0 else 0

    inactive_base = (
        df[df['Division'].isin(selected_divisions)].dropna(subset=["Date"]).copy()
        if selected_divisions else df.dropna(subset=["Date"]).copy()
    )
    last_rfq_df      = inactive_base.groupby(["Affiliate", "Division"], as_index=False).agg(Last_RFQ_Date=("Date", "max"))
    cutoff_date      = pd.Timestamp.today() - pd.DateOffset(months=6)
    inactive_clients = last_rfq_df[last_rfq_df["Last_RFQ_Date"] < cutoff_date].sort_values("Last_RFQ_Date").copy()
    inactive_clients["Last_RFQ_Date"] = inactive_clients["Last_RFQ_Date"].dt.strftime("%d-%m-%Y")
    inactive_clients = inactive_clients.rename(columns={"Last_RFQ_Date": "Last RFQ Date"})
    inactive_count   = inactive_clients["Affiliate"].nunique()

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card c-accent">
            <div class="kpi-bg-icon">📋</div>
            <div class="kpi-label">Total RFQs</div>
            <div class="kpi-value">{total_rfqs:,}</div>
            <span class="kpi-badge b-accent">All statuses</span>
        </div>
        <div class="kpi-card c-green">
            <div class="kpi-bg-icon">🏆</div>
            <div class="kpi-label">Awarded Ratio</div>
            <div class="kpi-value">{awarded_ratio:.1f}<span class="kpi-unit">%</span></div>
            <span class="kpi-badge b-green">{awarded} of {submitted} submitted</span>
        </div>
        <div class="kpi-card c-red">
            <div class="kpi-bg-icon">📉</div>
            <div class="kpi-label">Declined Ratio</div>
            <div class="kpi-value">{declined_ratio:.1f}<span class="kpi-unit">%</span></div>
            <span class="kpi-badge b-red">{declined} declined</span>
        </div>
        <div class="kpi-card c-amber">
            <div class="kpi-bg-icon">🚫</div>
            <div class="kpi-label">Inactive Clients</div>
            <div class="kpi-value">{inactive_count}</div>
            <span class="kpi-badge b-amber">No RFQ in 6+ months</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Status Breakdown + Top Clients ────────────────────────────────────────
    status_pct = (status_counts / status_counts.sum() * 100)
    result_df = pd.DataFrame({
        "Status":         status_counts.index,
        "RFQ Count":      status_counts.values,
        "Percentage (%)": status_pct.round(2).values
    }).reset_index(drop=True)

    top_base = df[df['Division'].isin(selected_divisions)].copy() if selected_divisions else df.copy()
    if selected_year != "All":
        top_base = top_base[top_base['Year'] == selected_year]
    top_clients_df = (
        top_base.groupby("Clients").size()
        .reset_index(name="RFQ Count")
        .sort_values("RFQ Count", ascending=False)
        .head(10)
    )

    col_left, spacer, col_right = st.columns([0.75, 0.05, 1.2])
    with col_left:
        st.markdown('<h3>📌 RFQ Status Breakdown</h3>', unsafe_allow_html=True)
        st.dataframe(result_df, use_container_width=True, hide_index=True)

    with col_right:
        st.markdown('<h3>🏆 Top 10 Clients by Volume</h3>', unsafe_allow_html=True)
        if not top_clients_df.empty:
            max_count = int(top_clients_df["RFQ Count"].max())
            bars = alt.Chart(top_clients_df).mark_bar(
                color=ACCENT, cornerRadiusTopRight=5,
                cornerRadiusBottomRight=5, opacity=0.88
            ).encode(
                y=alt.Y("Clients:N",
                    sort=alt.SortField(field="RFQ Count", order="descending"),
                    axis=alt.Axis(title=None, labels=False, ticks=False)),
                x=alt.X("RFQ Count:Q",
                    axis=alt.Axis(title="RFQ Count", tickMinStep=1, format="d"),
                    scale=alt.Scale(domain=[0, max_count + max(2, int(max_count * 0.22))], nice=False))
            )
            client_text = alt.Chart(top_clients_df).mark_text(
                align="left", baseline="middle", dx=6,
                fontSize=11, fontWeight="bold", color=TEXT_C
            ).encode(
                y=alt.Y("Clients:N", sort=alt.SortField(field="RFQ Count", order="descending")),
                x=alt.X("RFQ Count:Q"),
                text=alt.Text("Clients:N")
            )
            st.altair_chart(chart_cfg(bars + client_text, h=400), use_container_width=True)

    st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

    # ── Status Distribution ────────────────────────────────────────────────────
    st.markdown('<h3>📊 Status Distribution</h3>', unsafe_allow_html=True)
    actual_statuses = result_df["Status"].tolist()
    actual_colors   = [STATUS_COLORS.get(s, "#94a3b8") for s in actual_statuses]

    bars_status = alt.Chart(result_df).mark_bar(
        cornerRadiusTopLeft=5, cornerRadiusTopRight=5, opacity=0.9
    ).encode(
        x=alt.X("Status:N",
            axis=alt.Axis(labelAngle=-30, title=None),
            sort=alt.SortField(field="RFQ Count", order="descending")),
        y=alt.Y("Percentage (%):Q",
            axis=alt.Axis(title="% of Total RFQs"),
            scale=alt.Scale(zero=True, nice=True)),
        color=alt.Color("Status:N",
            scale=alt.Scale(domain=actual_statuses, range=actual_colors),
            legend=None),
        tooltip=["Status", "RFQ Count", alt.Tooltip("Percentage (%):Q", format=".1f")]
    )
    count_labels = alt.Chart(result_df).mark_text(
        dy=-9, color=TEXT_C, fontSize=11, fontWeight="bold"
    ).encode(
        x=alt.X("Status:N", sort=alt.SortField(field="RFQ Count", order="descending")),
        y=alt.Y("Percentage (%):Q"),
        text=alt.Text("RFQ Count:Q")
    )
    st.altair_chart(chart_cfg(bars_status + count_labels, h=380), use_container_width=True)

    st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

    # ── Trend Chart ───────────────────────────────────────────────────────────
    st.markdown('<h3>📈 RFQ Trend Over Time</h3>', unsafe_allow_html=True)

    trend_df = filtered_df.dropna(subset=['Date']).copy()
    trend_df['YM_key']   = trend_df['Date'].dt.strftime('%Y-%m')
    trend_df['YM_label'] = trend_df['Date'].dt.strftime('%b %Y')

    monthly_counts = (
        trend_df.groupby(['YM_key', 'YM_label'])
        .size()
        .reset_index(name='RFQ Count')
        .sort_values('YM_key')
        .reset_index(drop=True)
    )

    if not monthly_counts.empty:
        x_sort_order = monthly_counts['YM_label'].tolist()

        base_trend = alt.Chart(monthly_counts).encode(
            x=alt.X(
                "YM_label:O",
                sort=x_sort_order,
                title="Month",
                axis=alt.Axis(labelAngle=-35, grid=False, title="Month")
            ),
            y=alt.Y(
                "RFQ Count:Q",
                title="Number of RFQs",
                scale=alt.Scale(zero=True, nice=True),
                axis=alt.Axis(tickMinStep=1, format="d")
            )
        )

        area = base_trend.mark_area(opacity=0.15, color=ACCENT, line=False)
        line = base_trend.mark_line(color=ACCENT, strokeWidth=2.5, interpolate="monotone")
        points = base_trend.mark_circle(
            color=ACCENT, size=70, opacity=1, stroke="#ffffff", strokeWidth=2
        ).encode(
            tooltip=[
                alt.Tooltip("YM_label:N", title="Month"),
                alt.Tooltip("RFQ Count:Q", title="RFQs")
            ]
        )
        labels = base_trend.mark_text(
            dy=-14, fontSize=10, color=TEXT_C, fontWeight="bold"
        ).encode(text=alt.Text("RFQ Count:Q"))

        st.altair_chart(
            chart_cfg(area + line + points + labels, h=380),
            use_container_width=True
        )

    st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

    # ── Client–Affiliate Table ─────────────────────────────────────────────────
    st.markdown('<h3>📋 RFQs by Client & Affiliate</h3>', unsafe_allow_html=True)
    ca_df = (
        filtered_df.groupby(['Clients', 'Affiliate'])
        .size().reset_index(name='RFQ Count')
        .sort_values('RFQ Count', ascending=False)
    )
    if not ca_df.empty:
        st.dataframe(ca_df, use_container_width=True, hide_index=True)
    else:
        st.info("No RFQs found for the selected filters.")

    st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

    # ── Inactive Clients ───────────────────────────────────────────────────────
    st.markdown('<h3>🚫 Inactive Clients — No RFQs in 6+ Months</h3>', unsafe_allow_html=True)
    if not inactive_clients.empty:
        st.dataframe(inactive_clients, use_container_width=True, hide_index=True)
    else:
        st.success("✅ All clients are active — no inactive accounts found.")

else:
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;color:#8592a8">
        <div style="font-size:3rem;margin-bottom:1rem">📭</div>
        <div style="font-size:1.05rem;font-weight:700;color:#485068">No data found</div>
        <div style="font-size:0.88rem;margin-top:0.4rem">Try adjusting your filters to see results.</div>
    </div>
    """, unsafe_allow_html=True)
