import streamlit as st
import pandas as pd
import numpy as np
from unidecode import unidecode
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
# 2. Carregar credenciais do secrets
# ---------------------------
# Estrutura do st.secrets:
# [credentials]
# usernames = ["gestor", "medico"]
# passwords = ["rh123", "med123"]
# roles = ["RH", "MEDICO"]

usernames = st.secrets["credentials"]["usernames"]
passwords = st.secrets["credentials"]["passwords"]
roles = st.secrets["credentials"].get("roles", ["RH", "MEDICO"])

# Gerar hash das senhas (necessário para streamlit_authenticator)
hashed_passwords = stauth.Hasher(passwords).generate()

# Construir dicionário compatível com streamlit_authenticator
credentials = {
    "usernames": {
        u: {"name": u.capitalize(), "password": p}
        for u, p in zip(usernames, hashed_passwords)
    }
}

# Mapear roles separadamente
roles_map = dict(zip(usernames, roles))

# ---------------------------
# 3. Login
# ---------------------------
def login():
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
        st.session_state["role"] = roles_map.get(username, "")
    elif authentication_status is False:
        st.error("Usuário ou senha inválidos")
    return authenticator

authenticator = login()

if not st.session_state["logged_in"]:
    st.stop()  # Impede que o dashboard carregue antes do login

# Sidebar info e logout
st.sidebar.markdown(f"**Usuário:** {st.session_state['username']}")
st.sidebar.markdown(f"**Papel:** {st.session_state['role']}")
authenticator.logout("Logout", "sidebar")

# ---------------------------
# 4. Dashboard
# ---------------------------
st.title("📊 Dashboard de Utilização do Plano de Saúde")

uploaded_file = st.file_uploader("Escolha o arquivo .xlsx", type="xlsx")

if uploaded_file:
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

    # Padronizar colunas
    def clean_cols(df):
        df.columns = [unidecode(col).strip().replace(' ','_').replace('-','_') for col in df.columns]
        return df
    utilizacao = clean_cols(utilizacao)
    cadastro = clean_cols(cadastro)
    medicina_trabalho = clean_cols(medicina_trabalho)
    atestados = clean_cols(atestados)

    # Tipo beneficiário
    if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
        utilizacao['Tipo_Beneficiario'] = np.where(
            utilizacao['Nome_Titular']==utilizacao['Nome_do_Associado'], 'Titular', 'Dependente'
        )
    else:
        utilizacao['Tipo_Beneficiario'] = 'Desconhecido'

    # Sidebar filtros
    st.sidebar.subheader("Filtros")
    # Sexo
    possible_sexo_cols = [c for c in cadastro.columns if 'sexo' in c.lower()]
    sexo_col = possible_sexo_cols[0] if possible_sexo_cols else None
    sexo_opts = cadastro[sexo_col].dropna().unique() if sexo_col else []
    sexo_filtro = st.sidebar.multiselect("Sexo", sexo_opts, default=sexo_opts)
    # Tipo Beneficiário
    tipo_benef_filtro = st.sidebar.multiselect(
        "Tipo Beneficiário", utilizacao['Tipo_Beneficiario'].unique(), default=utilizacao['Tipo_Beneficiario'].unique()
    )
    # Município
    municipio_filtro = None
    if 'Municipio_do_Participante' in cadastro.columns:
        municipio_opts = cadastro['Municipio_do_Participante'].dropna().unique()
        municipio_filtro = st.sidebar.multiselect("Município", municipio_opts, default=municipio_opts)
    # Faixa etária
    faixa_etaria = st.sidebar.slider("Faixa Etária", 0, 100, (18,65))
    # Período
    periodo_min = utilizacao['Data_do_Atendimento'].min() if 'Data_do_Atendimento' in utilizacao.columns else pd.Timestamp.today()
    periodo_max = utilizacao['Data_do_Atendimento'].max() if 'Data_do_Atendimento' in utilizacao.columns else pd.Timestamp.today()
    periodo = st.sidebar.date_input("Período", [periodo_min, periodo_max])

    # Aplicar filtros (exemplo simplificado)
    cadastro_filtrado = cadastro.copy()
    if sexo_filtro and sexo_col:
        cadastro_filtrado = cadastro_filtrado[cadastro_filtrado[sexo_col].isin(sexo_filtro)]
    if municipio_filtro is not None:
        cadastro_filtrado = cadastro_filtrado[cadastro_filtrado['Municipio_do_Participante'].isin(municipio_filtro)]
    utilizacao_filtrada = utilizacao[utilizacao['Tipo_Beneficiario'].isin(tipo_benef_filtro)]
    
    st.write("✅ Arquivo carregado e filtros aplicados com sucesso!")
else:
    st.info("Aguardando upload do arquivo .xlsx")
