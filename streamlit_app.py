import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
from unidecode import unidecode
import streamlit_authenticator as stauth

# ---------------------------
# 1. Inicializar sessão
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""

# ---------------------------
# 2. Carregar usuários e senhas do secrets
# ---------------------------
usernames = st.secrets["credentials"]["usernames"]
passwords = st.secrets["credentials"]["passwords"]
roles = st.secrets["credentials"].get("roles", ["RH", "MEDICO"])

# Gerar hashes das senhas
hashed_passwords = stauth.Hasher(passwords).generate()

# Criar dict de credenciais compatível com streamlit_authenticator
credentials = {
    "usernames": {
        user: {"name": user.capitalize(), "password": pwd, "role": role}
        for user, pwd, role in zip(usernames, hashed_passwords, roles)
    }
}

# ---------------------------
# 3. Login
# ---------------------------
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
    st.stop()
else:
    st.info("Por favor, insira usuário e senha")
    st.stop()

# ---------------------------
# 4. Sidebar info e logout
# ---------------------------
st.sidebar.markdown(f"**Usuário:** {st.session_state['username']}")
st.sidebar.markdown(f"**Papel:** {st.session_state['role']}")
authenticator.logout("Logout", "sidebar")

# ---------------------------
# 5. Upload de arquivo
# ---------------------------
uploaded_file = st.file_uploader("Escolha o arquivo .xlsx", type="xlsx")
if uploaded_file is None:
    st.info("Aguardando upload do arquivo .xlsx")
    st.stop()

# ---------------------------
# 6. Ler abas
# ---------------------------
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
# 7. Funções auxiliares
# ---------------------------
def clean_cols(df):
    df.columns = [unidecode(col).strip().replace(' ','_').replace('-','_') for col in df.columns]
    return df

def mascarar_pii(df):
    df_masked = df.copy()
    for col in df_masked.select_dtypes(include='object').columns:
        df_masked[col] = df_masked[col].apply(lambda x: unidecode(str(x)[0]) + "***" if pd.notnull(x) else x)
    return df_masked

# ---------------------------
# 8. Padronizar colunas
# ---------------------------
utilizacao = clean_cols(utilizacao)
cadastro = clean_cols(cadastro)
medicina_trabalho = clean_cols(medicina_trabalho)
atestados = clean_cols(atestados)

# ---------------------------
# 9. Conversão de datas
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
# 10. Tipo Beneficiário
# ---------------------------
if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
    utilizacao['Tipo_Beneficiario'] = np.where(
        utilizacao['Nome_Titular'] == utilizacao['Nome_do_Associado'], 'Titular', 'Dependente'
    )
else:
    utilizacao['Tipo_Beneficiario'] = 'Desconhecido'

# ---------------------------
# 11. Filtros Sidebar
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
# 12. Aplicar filtros
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
# 13. Tabs e visualizações
# ---------------------------
# Aqui você pode copiar todas as tabs do seu código original (KPIs, Comparativo de Planos, Alertas, CIDs, Exportação)
# O login já está implementado, então todas as funcionalidades abaixo funcionarão somente após autenticação
st.success("✅ Dashboard carregado com sucesso!")
