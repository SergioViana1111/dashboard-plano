import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
from unidecode import unidecode
import streamlit_authenticator as stauth
import toml
import os

# ---------------------------
# 1. Funções auxiliares
# ---------------------------
def init_session():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["role"] = ""

def load_credentials():
    """Carrega credenciais do Streamlit Cloud ou do arquivo local secrets.toml"""
    if hasattr(st, "secrets"):
        # Streamlit Cloud
        credentials = {
            "usernames": {
                user: {"name": user.capitalize(), "password": pwd, "role": role}
                for user, pwd, role in zip(
                    st.secrets["credentials"]["usernames"],
                    st.secrets["credentials"]["passwords"],
                    st.secrets["credentials"].get("roles", ["RH", "MEDICO"])
                )
            }
        }
    else:
        # Local
        path = os.path.join(os.getcwd(), "secrets.toml")
        data = toml.load(path)
        credentials = {
            "usernames": {
                user: {"name": user.capitalize(), "password": pwd, "role": role}
                for user, pwd, role in zip(
                    data["credentials"]["usernames"],
                    data["credentials"]["passwords"],
                    data["credentials"].get("roles", ["RH", "MEDICO"])
                )
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

    # Ajuste: capturar apenas 2 valores
    name, authentication_status = authenticator.login("Login", location="sidebar")

    if authentication_status:
        st.session_state["logged_in"] = True
        st.session_state["username"] = name  # 'name' é o username aqui
        st.session_state["role"] = credentials['usernames'][name]['role']
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
# 3. Carregar secrets
# ---------------------------
credentials = load_credentials()

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
    # Padronização de colunas
    utilizacao = clean_cols(utilizacao)
    cadastro = clean_cols(cadastro)
    medicina_trabalho = clean_cols(medicina_trabalho)
    atestados = clean_cols(atestados)

    # ---------------------------
    # Conversão de datas
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
    if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
        utilizacao['Tipo_Beneficiario'] = np.where(
            utilizacao['Nome_Titular'] == utilizacao['Nome_do_Associado'], 'Titular', 'Dependente'
        )
    else:
        utilizacao['Tipo_Beneficiario'] = 'Desconhecido'

    # ---------------------------
    # Filtros Sidebar
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
    # Aplicar filtros
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
        utilizacao_filtrada = utilizacao_filtrada[
            utilizacao_filtrada['Nome_do_Associado'].isin(cadastro_filtrado['Nome_do_Associado'])
        ]
    if 'Data_do_Atendimento' in utilizacao_filtrada.columns:
        utilizacao_filtrada = utilizacao_filtrada[
            (utilizacao_filtrada['Data_do_Atendimento'] >= pd.to_datetime(periodo[0])) &
            (utilizacao_filtrada['Data_do_Atendimento'] <= pd.to_datetime(periodo[1]))
        ]

    # ---------------------------
    # Mascaramento se RH
    if st.session_state.get("role") == "RH":
        utilizacao_display = mascarar_pii(utilizacao_filtrada)
        cadastro_display = mascarar_pii(cadastro_filtrado)
    else:
        utilizacao_display = utilizacao_filtrada.copy()
        cadastro_display = cadastro_filtrado.copy()

    # ---------------------------
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "KPIs Gerais",
        "Comparativo de Planos",
        "Alertas & Inconsistências",
        "CIDs Crônicos & Procedimentos",
        "Exportação"
    ])

    # ---------------------------
    # Tab1: KPIs Gerais
    with tab1:
        st.subheader("📌 KPIs Gerais")
        custo_total = utilizacao_display['Valor'].sum() if 'Valor' in utilizacao_display.columns else 0
        st.metric("Custo Total (R$)", f"{custo_total:,.2f}")

        if 'Nome_do_Associado' in utilizacao_display.columns and 'Valor' in utilizacao_display.columns:
            custo_por_benef = utilizacao_display.groupby('Nome_do_Associado')['Valor'].sum().sort_values(ascending=False)
            top10_volume = utilizacao_display.groupby('Nome_do_Associado').size().sort_values(ascending=False)

            st.write("**Top 10 Beneficiários por Custo**")
            st.dataframe(custo_por_benef.head(10).reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado','Valor':'Valor'}))

            st.write("**Top 10 Beneficiários por Volume**")
            st.dataframe(top10_volume.head(10).reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado',0:'Volume'}))

            if 'Data_do_Atendimento' in utilizacao_display.columns:
                utilizacao_display['Mes_Ano'] = utilizacao_display['Data_do_Atendimento'].dt.to_period('M')
                evolucao = utilizacao_display.groupby('Mes_Ano')['Valor'].sum().reset_index()
                evolucao['Mes_Ano'] = evolucao['Mes_Ano'].astype(str)
                fig = px.bar(
                    evolucao, x='Mes_Ano', y='Valor', color='Valor', text='Valor',
                    labels={'Mes_Ano':'Mês/Ano','Valor':'R$'}, height=400
                )
                st.plotly_chart(fig, use_container_width=True)

    # ---------------------------
    # Tab2: Comparativo de Planos
    with tab2:
        possible_cols = [col for col in utilizacao_display.columns if 'plano' in col.lower() and 'descricao' in col.lower()]
        if possible_cols:
            plano_col = possible_cols[0]
            st.subheader("📊 Comparativo de Planos")
            comp = utilizacao_display.groupby(plano_col)['Valor'].sum().reset_index()
            fig = px.bar(comp, x=plano_col, y='Valor', color=plano_col, text='Valor', height=400)
            st.plotly_chart(fig, use_container_width=True)
            comp_volume = utilizacao_display.groupby(plano_col).size().reset_index(name='Volume')
            fig2 = px.bar(comp_volume, x=plano_col, y='Volume', color=plano_col, text='Volume', height=400)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Coluna de plano não encontrada. Verifique o arquivo ou nomes das colunas.")

    # ---------------------------
    # Tab3: Alertas & Inconsistências
    with tab3:
        st.subheader("🚨 Alertas")
        custo_lim = st.number_input("Limite de custo (R$)", value=5000)
        vol_lim = st.number_input("Limite de atendimentos", value=20)
        if 'Nome_do_Associado' in utilizacao_display.columns and 'Valor' in utilizacao_display.columns:
            custo_por_benef = utilizacao_display.groupby('Nome_do_Associado')['Valor'].sum()
            top10_volume = utilizacao_display.groupby('Nome_do_Associado').size()
            alert_custo = custo_por_benef[custo_por_benef > custo_lim]
            alert_vol = top10_volume[top10_volume > vol_lim]
            if not alert_custo.empty:
                st.write("**Beneficiários acima do limite de custo:**")
                st.dataframe(alert_custo.reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado','Valor':'Valor'}))
            if not alert_vol.empty:
                st.write("**Beneficiários acima do limite de volume:**")
                st.dataframe(alert_vol.reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado',0:'Volume'}))
        st.subheader("⚠️ Inconsistências")
        inconsistencias = pd.DataFrame()
        if sexo_col and 'Codigo_do_CID' in utilizacao_display.columns:
            def padronizar_nome(nome):
                return unidecode(str(nome)).strip().upper()
            utilizacao_display['Nome_merge'] = utilizacao_display['Nome_do_Associado'].apply(padronizar_nome)
            cadastro_display['Nome_merge'] = cadastro_display['Nome_do_Associado'].apply(padronizar_nome)
            utilizacao_merge = utilizacao_display.merge(
                cadastro_display[['Nome_merge', sexo_col]].drop_duplicates(),
                on='Nome_merge', how='left'
            )
            if sexo_col not in utilizacao_merge.columns:
                utilizacao_merge[sexo_col] = 'Desconhecido'
            else:
                utilizacao_merge[sexo_col] = utilizacao_merge[sexo_col].fillna('Desconhecido')
            parto_masc = utilizacao_merge[(utilizacao_merge['Codigo_do_CID']=='O80') & (utilizacao_merge[sexo_col]=='M')]
            if not parto_masc.empty:
                inconsistencias = pd.concat([inconsistencias, parto_masc])
        if not inconsistencias.empty:
            st.dataframe(inconsistencias)
        else:
            st.write("Nenhuma inconsistência encontrada.")

    # ---------------------------
    # Tab4: CIDs Crônicos & Procedimentos
    with tab4:
        st.subheader("🏥 Beneficiários Crônicos")
        cids_cronicos = ['E11','I10','J45']
        if 'Codigo_do_CID' in utilizacao_display.columns:
            utilizacao_display['Cronico'] = utilizacao_display['Codigo_do_CID'].isin(cids_cronicos)
            beneficiarios_cronicos = utilizacao_display[utilizacao_display['Cronico']].groupby('Nome_do_Associado')['Valor'].sum()
            st.dataframe(beneficiarios_cronicos.reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado','Valor':'Valor'}))
        st.subheader("💊 Top Procedimentos")
        if 'Nome_do_Procedimento' in utilizacao_display.columns:
            top_proc = utilizacao_display.groupby('Nome_do_Procedimento')['Valor'].sum().sort_values(ascending=False).head(10)
            st.dataframe(top_proc.reset_index().rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Valor'}))

    # ---------------------------
    # Tab5: Exportação
    with tab5:
        st.subheader("📤 Exportar Relatório")
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            if st.session_state.get("role") == "RH":
                if 'Mes_Ano' in utilizacao_display.columns:
                    agg = utilizacao_display.groupby('Mes_Ano').agg({'Valor':'sum'}).reset_index()
                    agg.to_excel(writer, sheet_name='Resumo_Agr', index=False)
                cadastro_display.to_excel(writer, sheet_name='Cadastro', index=False)
            else:
                utilizacao_display.to_excel(writer, sheet_name='Utilizacao', index=False)
                cadastro_display.to_excel(writer, sheet_name='Cadastro', index=False)
            if not medicina_trabalho.empty:
                medicina_trabalho.to_excel(writer, sheet_name='Medicina_do_Trabalho', index=False)
            if not atestados.empty:
                atestados.to_excel(writer, sheet_name='Atestados', index=False)
        st.download_button("📥 Baixar Relatório Completo", buffer, "dashboard_plano_saude.xlsx", "application/vnd.ms-excel")

    st.success("✅ Dashboard carregado com sucesso!")
else:
    st.info("Aguardando upload do arquivo .xlsx")
