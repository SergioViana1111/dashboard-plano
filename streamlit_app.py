import pandas as pd
import numpy as np
from unidecode import unidecode
import streamlit as st
import plotly.express as px
from io import BytesIO
import streamlit_authenticator as stauth

# ---------------------------
# 1. Inicializar sessão
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""

# ---------------------------
# 2. Configuração da página
# ---------------------------
st.set_page_config(page_title="Dashboard Plano de Saúde", layout="wide")
st.title("📊 Dashboard de Utilização do Plano de Saúde")

# ---------------------------
# 3. Carregar credenciais do secrets
# ---------------------------
usernames = st.secrets["credentials"]["usernames"]
passwords = st.secrets["credentials"]["passwords"]
roles = st.secrets["credentials"].get("roles", ["RH","MEDICO"])

# gerar hashes das senhas
hashed_passwords = stauth.Hasher(passwords).hash()

# criar dict compatível com streamlit_authenticator
credentials = {
    "usernames": {
        user: {"name": user.capitalize(), "password": pwd, "role": role}
        for user, pwd, role, pwd in zip(usernames, hashed_passwords, roles, hashed_passwords)
    }
}

# ---------------------------
# 4. Login
# ---------------------------
def login_authenticator(credentials):
    authenticator = stauth.Authenticate(
        credentials,
        cookie_name="dashboard_cookie",
        key="dashboard_key",
        cookie_expiry_days=1
    )
    name, authentication_status, username = authenticator.login("Login", location="sidebar")
    if authentication_status:
        st.session_state["logged_in"] = True
        st.session_state["username"] = name
        st.session_state["role"] = credentials["usernames"][username]["role"]
    elif authentication_status is False:
        st.error("Usuário ou senha inválidos")
    return authenticator

authenticator = login_authenticator(credentials)

if not st.session_state["logged_in"]:
    st.stop()  # interrompe app se não logado

# ---------------------------
# Sidebar info e logout
# ---------------------------
st.sidebar.markdown(f"**Usuário:** {st.session_state['username']}")
st.sidebar.markdown(f"**Papel:** {st.session_state['role']}")
authenticator.logout("Logout", "sidebar")

# ---------------------------
# 5. Upload do arquivo
# ---------------------------
uploaded_file = st.file_uploader("Escolha o arquivo .xlsx", type="xlsx")
if uploaded_file is not None:
    # Leitura das abas
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

    # ---------------------------
    # Funções auxiliares
    # ---------------------------
    def clean_cols(df):
        df.columns = [unidecode(col).strip().replace(' ','_').replace('-','_') for col in df.columns]
        return df

    utilizacao = clean_cols(utilizacao)
    cadastro = clean_cols(cadastro)
    medicina_trabalho = clean_cols(medicina_trabalho)
    atestados = clean_cols(atestados)

    # ---------------------------
    # Conversão de datas
    # ---------------------------
    date_cols_util = ['Data_do_Atendimento','Competencia','Data_de_Nascimento']
    date_cols_cad = ['Data_de_Nascimento','Data_de_Admissao_do_Empregado','Data_de_Adesao_ao_Plano','Data_de_Cancelamento']
    date_cols_med = ['Data_do_Exame']
    date_cols_at = ['Data_do_Afastamento']

    for col in date_cols_util:
        if col in utilizacao.columns:
            utilizacao[col] = pd.to_datetime(utilizacao[col], errors='coerce')
    for col in date_cols_cad:
        if col in cadastro.columns:
            cadastro[col] = pd.to_datetime(cadastro[col], errors='coerce')
    for col in date_cols_med:
        if col in medicina_trabalho.columns:
            medicina_trabalho[col] = pd.to_datetime(medicina_trabalho[col], errors='coerce')
    for col in date_cols_at:
        if col in atestados.columns:
            atestados[col] = pd.to_datetime(atestados[col], errors='coerce')

    # ---------------------------
    # Tipo Beneficiário
    # ---------------------------
    if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
        utilizacao['Tipo_Beneficiario'] = np.where(
            utilizacao['Nome_Titular'] == utilizacao['Nome_do_Associado'], 'Titular', 'Dependente'
        )
    else:
        utilizacao['Tipo_Beneficiario'] = 'Desconhecido'

    # ---------------------------
    # Aqui você continua com filtros, tabs e exportação como antes...
    # ---------------------------

else:
    st.info("Aguardando upload do arquivo .xlsx")
