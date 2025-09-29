import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
from unidecode import unidecode
import streamlit_authenticator as stauth

# ---------------------------
# 1. Funções auxiliares
# ---------------------------
def init_session():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["role"] = ""

def load_credentials_from_secrets():
    """Carrega credenciais do Streamlit Cloud"""
    usernames = st.secrets["credentials"]["usernames"]
    passwords = st.secrets["credentials"]["passwords"]
    roles = st.secrets["credentials"].get("roles", ["RH","MEDICO"])
    
    credentials = {
        "usernames": {
            u: {"name": u.capitalize(), "password": p, "role": r}
            for u, p, r in zip(usernames, passwords, roles)
        }
    }
    return credentials

def login_authenticator(credentials):
    authenticator = stauth.Authenticate(
        credentials,
        cookie_name="dashboard_cookie",
        key="dashboard_key",
        cookie_expiry_days=1
    )
    
    # Retorno compatível com a versão atual do streamlit_authenticator
    name, authentication_status, username = authenticator.login("Login", location="sidebar")
    
    if authentication_status:
        st.session_state["logged_in"] = True
        st.session_state["username"] = name
        st.session_state["role"] = credentials['usernames'][username]['role']
    elif authentication_status is False:
        st.error("Usuário ou senha inválidos")
    elif authentication_status is None:
        st.warning("Por favor, insira usuário e senha")
    
    return authenticator

def require_login_ui():
    if not st.session_state["logged_in"]:
        st.stop()

def logout(authenticator):
    if st.session_state["logged_in"]:
        authenticator.logout("Logout", "sidebar")
        st.session_state["logged_in"] = False

def clean_cols(df):
    df.columns = [unidecode(col).strip().replace(' ','_').replace('-','_') for col in df.columns]
    return df

def mascarar_pii(df):
    df_masked = df.copy()
    for col in df_masked.select_dtypes(include='object').columns:
        df_masked[col] = df_masked[col].apply(lambda x: unidecode(str(x)[0]) + "***" if pd.notnull(x) else x)
    return df_masked

# ---------------------------
# 2. Inicializar sessão
# ---------------------------
init_session()
st.set_page_config(page_title="Dashboard Plano de Saúde", layout="wide")
st.title("📊 Dashboard de Utilização do Plano de Saúde")

# ---------------------------
# 3. Carregar credentials
# ---------------------------
credentials = load_credentials_from_secrets()

# ---------------------------
# 4. Login
# ---------------------------
authenticator = login_authenticator(credentials)
require_login_ui()
st.sidebar.markdown(f"**Usuário:** {st.session_state['username']}")
st.sidebar.markdown(f"**Papel:** {st.session_state['role']}")
logout(authenticator)

# ---------------------------
# 5. Upload de arquivo
# ---------------------------
uploaded_file = st.file_uploader("Escolha o arquivo .xlsx", type="xlsx")

if uploaded_file is not None:
    utilizacao = pd.read_excel(uploaded_file, sheet_name='Utilizacao')
    cadastro = pd.read_excel(uploaded_file, sheet_name='Cadastro')

    try:
        medicina_trabalho = pd.read_excel(uploaded_file, sheet_name='Medicina_do_Trabalho')
    except:
        medicina_trabalho = pd.DataFrame()

    try:
        atestados = pd.read_excel(uploaded_file, sheet_name='Atestados')
    except:
        atestados = pd.DataFrame()

    # Padronizar colunas
    utilizacao = clean_cols(utilizacao)
    cadastro = clean_cols(cadastro)
    medicina_trabalho = clean_cols(medicina_trabalho)
    atestados = clean_cols(atestados)

    # Dashboard simples de teste
    st.subheader("📌 Dados de Utilização")
    st.dataframe(utilizacao.head())
    st.subheader("📌 Dados de Cadastro")
    st.dataframe(cadastro.head())
else:
    st.info("Aguardando upload do arquivo .xlsx")
