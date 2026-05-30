import streamlit as st
from database import init_db

st.set_page_config(
    page_title="Trading Performance Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# Custom CSS
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0f0f1a; }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #2d2d44;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 4px 0;
    }
    .metric-label { font-size: 12px; color: #8892a4; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-value { font-size: 24px; font-weight: 700; color: #ffffff; }
    .metric-sub { font-size: 13px; color: #6c7a8a; margin-top: 2px; }
    .positive { color: #22c55e !important; }
    .negative { color: #ef4444 !important; }
    div[data-testid="stMetric"] {
        background: #1a1a2e;
        border: 1px solid #2d2d44;
        border-radius: 10px;
        padding: 14px;
    }
    .stButton > button {
        border-radius: 8px;
        border: 1px solid #3d3d5c;
        background: #1a1a2e;
        color: #e0e0e0;
    }
    .stButton > button:hover { background: #2d2d44; border-color: #5a5aff; }
    .page-header {
        font-size: 28px; font-weight: 700; color: #ffffff;
        border-bottom: 2px solid #2d2d44;
        padding-bottom: 12px; margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

pg = st.navigation([
    st.Page("pages/dashboard.py", title="Dashboard", icon="📊", default=True),
    st.Page("pages/trade_entry.py", title="Add Trade", icon="➕"),
    st.Page("pages/trade_history.py", title="Trade History", icon="📋"),
    st.Page("pages/analytics.py", title="Analytics", icon="📈"),
    st.Page("pages/reports.py", title="Reports", icon="📄"),
    st.Page("pages/settings.py", title="Settings", icon="⚙️"),
])
pg.run()
