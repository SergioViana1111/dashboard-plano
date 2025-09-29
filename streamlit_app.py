import pandas as pd
import numpy as np
from unidecode import unidecode
import streamlit as st
import plotly.express as px
from io import BytesIO
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

# ---------------------------
# 2. Inicializar sessão e login
# ---------------------------
init_session()
st.set_page_config(page_title="Dashboard Plano de Saúde", layout="wide")
st.title("📊 Dashboard de Utilização do Plano de Saúde")

# Carregar credenciais do secrets
credentials = load_credentials_from_secrets()
authenticator = login_authenticator(credentials)
require_login_ui()
st.sidebar.markdown(f"**Usuário:** {st.session_state['username']}")
st.sidebar.markdown(f"**Papel:** {st.session_state['role']}")
logout(authenticator)

# ---------------------------
# 3. Upload do arquivo
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

    # Padronização de colunas
    utilizacao = clean_cols(utilizacao)
    cadastro = clean_cols(cadastro)
    medicina_trabalho = clean_cols(medicina_trabalho)
    atestados = clean_cols(atestados)

    # Conversão de datas
    date_cols_util = ['Data_do_Atendimento','Competencia','Data_de_Nascimento']
    date_cols_cad = ['Data_de_Nascimento','Data_de_Admissao_do_Empregado','Data_de_Adesao_ao_Plano','Data_de_Cancelamento']
    for col in date_cols_util:
        if col in utilizacao.columns:
            utilizacao[col] = pd.to_datetime(utilizacao[col], errors='coerce')
    for col in date_cols_cad:
        if col in cadastro.columns:
            cadastro[col] = pd.to_datetime(cadastro[col], errors='coerce')

    # Tipo Beneficiário
    if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
        utilizacao['Tipo_Beneficiario'] = np.where(
            utilizacao['Nome_Titular'] == utilizacao['Nome_do_Associado'], 'Titular', 'Dependente'
        )
    else:
        utilizacao['Tipo_Beneficiario'] = 'Desconhecido'

    # ---------------------------
    # 4. Filtros Sidebar
    # ---------------------------
    st.sidebar.subheader("Filtros")
    # Sexo
    possible_sexo_cols = [col for col in cadastro.columns if 'sexo' in col.lower()]
    sexo_col = possible_sexo_cols[0] if possible_sexo_cols else None
    sexo_opts = cadastro[sexo_col].dropna().unique() if sexo_col else []
    sexo_filtro = st.sidebar.multiselect("Sexo", options=sexo_opts, default=sexo_opts)

    # Tipo Beneficiário
    tipo_benef_filtro = st.sidebar.multiselect(
        "Tipo Beneficiário",
        options=utilizacao['Tipo_Beneficiario'].unique(),
        default=utilizacao['Tipo_Beneficiario'].unique()
    )

    # Município
    municipio_filtro = None
    if 'Municipio_do_Participante' in cadastro.columns:
        municipio_opts = cadastro['Municipio_do_Participante'].dropna().unique()
        municipio_filtro = st.sidebar.multiselect("Município do Participante", options=municipio_opts, default=municipio_opts)

    # Faixa etária
    faixa_etaria = st.sidebar.slider("Faixa Etária", 0, 100, (18, 65))

    # Período
    periodo_min = utilizacao['Data_do_Atendimento'].min() if 'Data_do_Atendimento' in utilizacao.columns else pd.Timestamp.today()
    periodo_max = utilizacao['Data_do_Atendimento'].max() if 'Data_do_Atendimento' in utilizacao.columns else pd.Timestamp.today()
    periodo = st.sidebar.date_input("Período", [periodo_min, periodo_max])

    # ---------------------------
    # 5. Aplicar filtros
    # ---------------------------
    cadastro_filtrado = cadastro.copy()
    if 'Data_de_Nascimento' in cadastro_filtrado.columns:
        idade = (pd.Timestamp.today() - cadastro_filtrado['Data_de_Nascimento']).dt.days // 365
        cadastro_filtrado = cadastro_filtrado[(idade >= faixa_etaria[0]) & (idade <= faixa_etaria[1])]
    if sexo_filtro and sexo_col:
        cadastro_filtrado = cadastro_filtrado[cadastro_filtrado[sexo_col].isin(sexo_filtro)]
    if municipio_filtro is not None:
        cadastro_filtrado = cadastro_filtrado[cadastro_filtrado['Municipio_do_Participante'].isin(municipio_filtro)]

    utilizacao_filtrada = utilizacao.copy()
    if tipo_benef_filtro:
        utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Tipo_Beneficiario'].isin(tipo_benef_filtro)]
    if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Nome_do_Associado' in cadastro_filtrado.columns:
        utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'].isin(cadastro_filtrado['Nome_do_Associado'])]
    if 'Data_do_Atendimento' in utilizacao_filtrada.columns:
        utilizacao_filtrada = utilizacao_filtrada[
            (utilizacao_filtrada['Data_do_Atendimento'] >= pd.to_datetime(periodo[0])) &
            (utilizacao_filtrada['Data_do_Atendimento'] <= pd.to_datetime(periodo[1]))
        ]

    # ---------------------------
    # 6. Tabs
    # ---------------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "KPIs Gerais",
        "Comparativo de Planos",
        "Alertas & Inconsistências",
        "CIDs Crônicos & Procedimentos",
        "Exportação"
    ])

    # Exemplo de conteúdo Tab1
    with tab1:
        st.subheader("📌 KPIs Gerais")
        custo_total = utilizacao_filtrada['Valor'].sum() if 'Valor' in utilizacao_filtrada.columns else 0
        st.metric("Custo Total (R$)", f"{custo_total:,.2f}")

    # Exportação simples
    with tab5:
        st.subheader("📤 Exportar Relatório")
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            utilizacao_filtrada.to_excel(writer, sheet_name='Utilizacao', index=False)
            cadastro_filtrado.to_excel(writer, sheet_name='Cadastro', index=False)
            if not medicina_trabalho.empty:
                medicina_trabalho.to_excel(writer, sheet_name='Medicina_do_Trabalho', index=False)
            if not atestados.empty:
                atestados.to_excel(writer, sheet_name='Atestados', index=False)
        st.download_button("📥 Baixar Relatório Completo", buffer, "dashboard_plano_saude.xlsx", "application/vnd.ms-excel")

    st.success("✅ Dashboard carregado com sucesso!")
else:
    st.info("Aguardando upload do arquivo .xlsx")
