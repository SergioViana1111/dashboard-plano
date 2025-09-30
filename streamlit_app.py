import pandas as pd
import numpy as np
from unidecode import unidecode
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import re

# ---------------------------
# 0. CONFIGURAÇÃO DE PÁGINA E TEMA
# ---------------------------
st.set_page_config(
    page_title="Dashboard Saúde",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para visual moderno
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }

    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3a5f 0%, #2d5a8c 100%); padding-top: 2rem; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: #ffffff !important; font-weight: 600; }

    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.1);
    }
    [data-testid="stMetric"] label { color: #ffffff !important; font-size: 0.9rem !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: 0.5px; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { color: #ffffff !important; font-size: 2rem !important; font-weight: 700 !important; }

    h1 { color: #1e3a5f; font-weight: 700; padding-bottom: 1rem; border-bottom: 3px solid #667eea; margin-bottom: 2rem; }
    h2, h3 { color: #2d5a8c; font-weight: 600; margin-top: 2rem; }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #f8f9fa; padding: 0.5rem; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: transparent; border-radius: 8px; color: #2d5a8c; font-weight: 600; padding: 0 1.5rem; transition: all 0.3s ease; }
    .stTabs [data-baseweb="tab"]:hover { background-color: rgba(102, 126, 234, 0.1); }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; }

    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }

    .stButton button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; padding: 0.75rem 2rem; font-weight: 600; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3); }
    .stButton button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4); }
    .stDownloadButton button { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; border: none; border-radius: 8px; padding: 0.75rem 2rem; font-weight: 600; transition: all 0.3s ease; }

    [data-testid="stExpander"] { background-color: #f8f9fa; border-radius: 10px; border: 1px solid #e9ecef; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }

    .stTextInput input, .stNumberInput input { border-radius: 8px; border: 2px solid #e9ecef; padding: 0.75rem; transition: all 0.3s ease; }
    .stTextInput input:focus, .stNumberInput input:focus { border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# 1. FUNÇÕES DE FORMATAÇÃO
# ---------------------------
def format_brl(value):
    if pd.isna(value):
        return "R$ 0,00"
    value = float(value)
    return "R$ {:,.2f}".format(value).replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")

def style_dataframe_brl(df, value_cols=['Valor']):
    formatters = {}
    for col in value_cols:
        if col in df.columns:
            formatters[col] = format_brl
    if 'Volume' in df.columns and 'Volume' not in formatters:
        formatters['Volume'] = lambda x: '{:,.0f}'.format(x).replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    if 0 in df.columns and 0 not in formatters:
        formatters[0] = lambda x: '{:,.0f}'.format(x).replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    if formatters:
        return df.style.format(formatters)
    return df

# ---------------------------
# 2. AUTENTICAÇÃO
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

if "selected_benef" not in st.session_state:
    st.session_state.selected_benef = None

def login():
    if "username_input" not in st.session_state:
        st.session_state.username_input = ""
    if "password_input" not in st.session_state:
        st.session_state.password_input = ""

    st.sidebar.markdown("### 🔐 Login")
    st.session_state.username_input = st.sidebar.text_input("Usuário", st.session_state.username_input)
    st.session_state.password_input = st.sidebar.text_input("Senha", st.session_state.password_input, type="password")

    # Credenciais fixas
    usernames = ["rh_teste", "medico_teste"]
    passwords = ["senha_rh", "senha_med"]
    roles = ["RH", "MEDICO"]

    if st.sidebar.button("Entrar", use_container_width=True):
        if st.session_state.username_input in usernames:
            idx = usernames.index(st.session_state.username_input)
            if st.session_state.password_input == passwords[idx]:
                st.session_state.logged_in = True
                st.session_state.username = st.session_state.username_input
                st.session_state.role = roles[idx]
                st.success(f"✅ Bem-vindo(a), {st.session_state.username}!")
                st.experimental_rerun()
            else:
                st.error("❌ Senha incorreta")
        else:
            st.error("❌ Usuário não encontrado")

login()

# ---------------------------
# 3. DASHBOARD PRINCIPAL
# ---------------------------
if st.session_state.logged_in:
    role = st.session_state.role  # CORREÇÃO: define role antes de usar

    # Header moderno
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"🏥 Dashboard Plano de Saúde")
    with col2:
        st.markdown(
            f"<div style='text-align:right;color:#667eea;font-weight:600'>{role}<br>{st.session_state.username}</div>", 
            unsafe_allow_html=True
        )

    st.markdown("### Bem-vindo(a) ao Dashboard!")
