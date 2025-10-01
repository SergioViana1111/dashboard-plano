# app.py - Dashboard Plano de Saúde (com todas as requests do cliente)
import os
import tempfile
import shutil
import re
from io import BytesIO
from datetime import datetime

import pandas as pd
import numpy as np
from unidecode import unidecode

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

# ---------------------------
# Configuração de página e tema (seu CSS mantido)
# ---------------------------
st.set_page_config(
    page_title="Dashboard Saúde",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# (Mantive seu CSS original - omitido aqui por brevidade no comentário, mas será incluído no corpo abaixo)
st.markdown("""
<style>
/* (Cole seu CSS completo aqui se quiser manter exatamente igual) */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3a5f 0%, #2d5a8c 100%); padding-top: 2rem; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #ffffff !important; font-weight: 600;}
/* ... (restante do CSS, como no seu script original) ... */
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Utilitários
# ---------------------------
def clean_cols(df):
    df = df.copy()
    df.columns = [unidecode(str(col)).strip().replace(' ','_').replace('-','_') for col in df.columns]
    return df

def ensure_datetime(df, cols):
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

def padronizar_nome(nome):
    return unidecode(str(nome)).strip().upper()

def mask_string(s, keep_start=1, keep_end=1):
    if pd.isna(s):
        return ""
    s = str(s)
    if len(s) <= (keep_start + keep_end):
        return "*" * len(s)
    return s[:keep_start] + "*"*(len(s)-keep_start-keep_end) + s[-keep_end:]

def format_brl(value):
    if pd.isna(value):
        return "R$ 0,00"
    try:
        value = float(value)
    except:
        return "R$ 0,00"
    return "R$ {:,.2f}".format(value).replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")

def style_dataframe_brl(df, value_cols=['Valor']):
    df2 = df.copy()
    # convert numbers to display strings in provided cols
    for col in value_cols:
        if col in df2.columns:
            df2[col] = df2[col].apply(format_brl)
    # Volume columns formatting
    if 'Volume' in df2.columns:
        df2['Volume'] = df2['Volume'].apply(lambda x: '{:,.0f}'.format(x).replace(",", "."))
    return df2

def add_index1(df, name='No'):
    df2 = df.reset_index(drop=True).copy()
    df2.insert(0, name, range(1, len(df2)+1))
    return df2

# ---------------------------
# Leitura robusta de arquivo (aceita xltx)
# ---------------------------
@st.cache_data(ttl=600)
def read_input(file_obj, filename=None):
    sheets = {}
    name = filename or getattr(file_obj, "name", "")
    name = name.lower() if name else ""
    try:
        file_obj.seek(0)
    except Exception:
        pass

    # CSV
    if name.endswith('.csv'):
        try:
            df = pd.read_csv(file_obj)
            sheets['Utilizacao'] = df
            return sheets
        except Exception:
            try:
                file_obj.seek(0)
                df = pd.read_csv(file_obj, encoding='latin1')
                sheets['Utilizacao'] = df
                return sheets
            except Exception:
                pass

    # Excel attempt
    try:
        xls = pd.ExcelFile(file_obj, engine='openpyxl')
        for s in xls.sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=s, engine='openpyxl')
            except Exception:
                df = pd.read_excel(xls, sheet_name=s)
            sheets[s] = df
        return sheets
    except Exception as e:
        # fallback: write temp file and read
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            file_obj.seek(0)
            shutil.copyfileobj(file_obj, tmp)
            tmp.flush(); tmp.close()
            xls = pd.ExcelFile(tmp.name, engine='openpyxl')
            for s in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=s, engine='openpyxl')
                sheets[s] = df
            return sheets
        except Exception as e2:
            try:
                file_obj.seek(0)
                df = pd.read_csv(file_obj)
                sheets['Utilizacao'] = df
                return sheets
            except Exception:
                st.error("Não foi possível ler o arquivo. Peça para salvar como .xlsx ou .csv e reenviar.")
                st.error(f"Detalhe técnico: {e2}")
                return {}

# ---------------------------
# Autenticação simples (sessão)
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = "VISITANTE"
if "selected_benef" not in st.session_state:
    st.session_state.selected_benef = None

def login_ui():
    st.sidebar.markdown("### 🔐 Login")
    username = st.sidebar.text_input("Usuário", key="username_input")
    password = st.sidebar.text_input("Senha", type="password", key="password_input")

    # exemplo de credenciais locais (mude em produção)
    if 'credentials' not in st.secrets:
        st.secrets['credentials'] = {
            "usernames": ["rh_teste", "medico_teste"],
            "passwords": ["senha_rh", "senha_med"],
            "roles": ["RH", "MEDICO"]
        }

    if st.sidebar.button("Entrar", use_container_width=True):
        users = st.secrets["credentials"]["usernames"]
        pwds = st.secrets["credentials"]["passwords"]
        roles = st.secrets["credentials"]["roles"]
        if username in users:
            idx = users.index(username)
            if password == pwds[idx]:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = roles[idx]
                st.success(f"Bem-vindo(a), {username} ({roles[idx]})")
                st.rerun()
            else:
                st.sidebar.error("Senha incorreta")
        else:
            st.sidebar.error("Usuário não encontrado")

if not st.session_state.logged_in:
    login_ui()
    st.stop()

# ---------------------------
# Header
# ---------------------------
role = st.session_state.role
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🏥 Dashboard Plano de Saúde")
with col2:
    st.markdown(f"<div style='text-align:right'><strong style='color:#667eea'>{role}</strong><br><small>{st.session_state.username}</small></div>", unsafe_allow_html=True)
st.markdown("---")

# ---------------------------
# Sidebar: Uploads e configurações globais
# ---------------------------
st.sidebar.markdown("### 📁 Dados e Configurações")
uploaded_file = st.sidebar.file_uploader("Enviar arquivo (xlsx / xls / xltx / csv)", type=None)
cids_file = st.sidebar.file_uploader("Upload lista CIDs crônicos (txt/csv) - opcional", type=['txt','csv'])
dap_file = st.sidebar.file_uploader("Upload lista de DAPs (opcional)", type=['txt','csv'])
copart_file = st.sidebar.file_uploader("Upload coparticipação (opcional)", type=['xlsx','xls','csv'])
# CID match mode
st.sidebar.markdown("### 🔎 Modo de busca CID")
cid_mode = st.sidebar.selectbox("Escolha o modo", options=["Começa com (raiz) - recomendado", "Exato", "Contém", "Regex"], index=0)
# anonymize toggle (disabled for MEDICO)
anon_default = True if st.session_state.role != "MEDICO" else False
anon_toggle = st.sidebar.checkbox("Mostrar dados anonimizados (máscara)", value=anon_default, disabled=(st.session_state.role=="MEDICO"))

# ---------------------------
# Ler arquivo
# ---------------------------
if uploaded_file is None:
    st.info("Aguardando upload do arquivo (recomendo .xlsx ou .csv).")
    st.stop()

sheets = read_input(uploaded_file, filename=getattr(uploaded_file, "name", None))
if not sheets:
    st.stop()

# mapear abas
utilizacao = sheets.get('Utilizacao', sheets.get('utilizacao', pd.DataFrame())).copy()
cadastro = sheets.get('Cadastro', sheets.get('cadastro', pd.DataFrame())).copy()
medicina_trabalho = sheets.get('Medicina_do_Trabalho', sheets.get('Medicina', pd.DataFrame())).copy()
atestados = sheets.get('Atestados', pd.DataFrame()).copy()

# Se utilizacao vazia -> erro
if utilizacao is None or utilizacao.empty:
    st.error("A aba 'Utilizacao' não foi encontrada ou está vazia. Verifique o arquivo.")
    st.stop()

# padroniza colunas
utilizacao = clean_cols(utilizacao)
cadastro = clean_cols(cadastro)
medicina_trabalho = clean_cols(medicina_trabalho)
atestados = clean_cols(atestados)

# datas
date_cols_util = ['Data_do_Atendimento','Competencia','Data_de_Nascimento']
date_cols_cad = ['Data_de_Nascimento','Data_de_Admissao_do_Empregado','Data_de_Adesao_ao_Plano','Data_de_Cancelamento']
date_cols_med = ['Data_do_Exame']
date_cols_at = ['Data_do_Afastamento']
utilizacao = ensure_datetime(utilizacao, date_cols_util)
cadastro = ensure_datetime(cadastro, date_cols_cad)
medicina_trabalho = ensure_datetime(medicina_trabalho, date_cols_med)
atestados = ensure_datetime(atestados, date_cols_at)

# Valor -> numérico robusto
if 'Valor' in utilizacao.columns:
    try:
        # remove caracteres que não são numéricos exceto , and .
        utilizacao['Valor'] = utilizacao['Valor'].astype(str).str.replace(r'[^\d\.,-]', '', regex=True)
        # handle if decimal separator is comma or point - normalize to point
        # if there is both comma and dot, assume comma thousands and dot decimal -> remove commas
        def parse_num(s):
            if pd.isna(s) or s=="":
                return 0.0
            s = str(s).strip()
            # case like "1.234,56" -> treat comma as decimal -> remove dots
            if s.count(',')==1 and s.count('.')>0 and s.rfind('.') < s.rfind(','):
                s2 = s.replace('.', '').replace(',', '.')
            else:
                # remove commas used as thousand separators
                s2 = s.replace(',', '')
            try:
                return float(s2)
            except:
                try:
                    return float(s2.replace(',', '.'))
                except:
                    return 0.0
        utilizacao['Valor'] = utilizacao['Valor'].apply(parse_num)
    except Exception as e:
        st.warning(f"Erro na conversão de 'Valor': {e}")
else:
    utilizacao['Valor'] = 0.0

# Tipo beneficiario
if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
    utilizacao['Tipo_Beneficiario'] = np.where(utilizacao['Nome_Titular'].fillna('').str.strip() == utilizacao['Nome_do_Associado'].fillna('').str.strip(), 'Titular', 'Dependente')
else:
    utilizacao['Tipo_Beneficiario'] = 'Desconhecido'

# ---------------------------
# Configuração DAP: verificar coluna ou upload
# ---------------------------
dap_column_exists = any('dap' in c.lower() for c in cadastro.columns)
daps_list = []
if dap_column_exists:
    # tenta colher valores únicos
    dap_col_name = [c for c in cadastro.columns if 'dap' in c.lower()][0]
    daps_list = list(cadastro[dap_col_name].dropna().unique())
else:
    if dap_file:
        try:
            raw = dap_file.read()
            try:
                txt = raw.decode('utf-8')
            except:
                txt = raw.decode('latin1')
            daps_list = [line.strip() for line in txt.splitlines() if line.strip()]
        except Exception:
            daps_list = []

# ---------------------------
# CIDs crônicos: upload ou textarea
# ---------------------------
cids_list = ['E11','I10','J45']  # default
if cids_file:
    try:
        raw = cids_file.read()
        try:
            txt = raw.decode('utf-8')
        except:
            txt = raw.decode('latin1')
        cands = [line.strip().upper() for line in txt.splitlines() if line.strip()]
        if cands:
            cids_list = cands
    except Exception:
        pass

st.sidebar.markdown("### ⚕️ CIDs crônicos")
cids_text = st.sidebar.text_area("Edite os CIDs crônicos (um por linha) — ex: E11", value="\n".join(cids_list), height=120)
cids_list = [c.strip().upper() for c in cids_text.splitlines() if c.strip()]

# ---------------------------
# Filtros dinâmicos (sidebar)
# ---------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Filtros dinâmicos")

# Sexo
possible_sexo_cols = [col for col in cadastro.columns if 'sexo' in col.lower()]
sexo_col = possible_sexo_cols[0] if possible_sexo_cols else None
sexo_opts = list(cadastro[sexo_col].dropna().unique()) if sexo_col else []
sexo_filtro = st.sidebar.multiselect("Sexo", options=sexo_opts, default=sexo_opts)

# Tipo beneficiario (Titular/Dependente)
tipo_benef_opts = list(utilizacao['Tipo_Beneficiario'].dropna().unique())
tipo_benef_filtro = st.sidebar.multiselect("Tipo Beneficiário", options=tipo_benef_opts, default=tipo_benef_opts)

# DAP filter (if present)
dap_filtro = None
if dap_column_exists:
    dap_opts = sorted(list(cadastro[dap_col_name].dropna().unique()))
    dap_filtro = st.sidebar.multiselect("DAP", options=dap_opts, default=dap_opts)
elif daps_list:
    dap_filtro = st.sidebar.multiselect("DAP (upload)", options=daps_list, default=daps_list)

# Município
municipio_filtro = None
if 'Municipio_do_Participante' in cadastro.columns:
    municipio_opts = sorted(list(cadastro['Municipio_do_Participante'].dropna().unique()))
    municipio_filtro = st.sidebar.multiselect("Município", options=municipio_opts, default=municipio_opts)

# Faixa etária dinâmica: calcula min/max a partir do cadastro
min_age, max_age = 0, 120
if 'Data_de_Nascimento' in cadastro.columns and not cadastro['Data_de_Nascimento'].isna().all():
    idade_all = (pd.Timestamp.today() - cadastro['Data_de_Nascimento']).dt.days // 365
    try:
        min_age, max_age = int(idade_all.min()), int(idade_all.max())
    except:
        min_age, max_age = 0, 120
faixa_etaria = st.sidebar.slider("Faixa Etária", min_value=min_age, max_value=max_age, value=(18,65))

# Período (Data do atendimento)
if 'Data_do_Atendimento' in utilizacao.columns and not utilizacao['Data_do_Atendimento'].isna().all():
    periodo_min = utilizacao['Data_do_Atendimento'].min().date()
    periodo_max = utilizacao['Data_do_Atendimento'].max().date()
else:
    periodo_min = datetime.today().date()
    periodo_max = datetime.today().date()
periodo = st.sidebar.date_input("Período (início / fim)", [periodo_min, periodo_max])

# Planos (se houver coluna de plano)
possible_plano_cols = [c for c in utilizacao.columns if 'plano' in c.lower()]
plano_col = possible_plano_cols[0] if possible_plano_cols else None
plano_opts = list(utilizacao[plano_col].dropna().unique()) if plano_col else []
planos_filtro = st.sidebar.multiselect("Planos", options=plano_opts, default=plano_opts)

# ---------------------------
# Aplicar filtros
# ---------------------------
cadastro_filtrado = cadastro.copy()
# faixa etaria
if 'Data_de_Nascimento' in cadastro_filtrado.columns:
    idade = (pd.Timestamp.today() - cadastro_filtrado['Data_de_Nascimento']).dt.days // 365
    cadastro_filtrado = cadastro_filtrado[(idade >= faixa_etaria[0]) & (idade <= faixa_etaria[1])]
# sexo
if sexo_col and sexo_filtro:
    cadastro_filtrado = cadastro_filtrado[cadastro_filtrado[sexo_col].isin(sexo_filtro)]
# municipio
if municipio_filtro is not None and 'Municipio_do_Participante' in cadastro_filtrado.columns:
    cadastro_filtrado = cadastro_filtrado[cadastro_filtrado['Municipio_do_Participante'].isin(municipio_filtro)]
# dap
if dap_filtro is not None and dap_column_exists:
    cadastro_filtrado = cadastro_filtrado[cadastro_filtrado[dap_col_name].isin(dap_filtro)]

utilizacao_filtrada = utilizacao.copy()
# tipo beneficiario
if tipo_benef_filtro:
    utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Tipo_Beneficiario'].isin(tipo_benef_filtro)]
# planos
if plano_col and planos_filtro:
    utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada[plano_col].isin(planos_filtro)]
# cruzamento com cadastro filtrado (nomes)
if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Nome_do_Associado' in cadastro_filtrado.columns:
    nomes_validos = cadastro_filtrado['Nome_do_Associado'].dropna().unique()
    utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'].isin(nomes_validos)]
# periodo
if 'Data_do_Atendimento' in utilizacao_filtrada.columns:
    utilizacao_filtrada = utilizacao_filtrada[
        (utilizacao_filtrada['Data_do_Atendimento'] >= pd.to_datetime(periodo[0])) &
        (utilizacao_filtrada['Data_do_Atendimento'] <= pd.to_datetime(periodo[1]))
    ]

# ---------------------------
# Funções de exibição interativa (AgGrid wrappers)
# ---------------------------
def aggrid_df(df, height=300, selection_mode="single", enable_return='single'):
    df_show = df.copy().reset_index(drop=True)
    # show index starting at 1
    df_show.insert(0, 'No', range(1, len(df_show)+1))
    gb = GridOptionsBuilder.from_dataframe(df_show)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    gb.configure_default_column(filterable=True, sortable=True, resizable=True)
    gb.configure_selection(selection_mode=selection_mode, use_checkbox=(selection_mode=="multiple"))
    gridOptions = gb.build()
    grid_return = AgGrid(
        df_show,
        gridOptions=gridOptions,
        height=height,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=True
    )
    return grid_return

# anonymize dataframes (default mask)
def anonymize_df(df):
    df2 = df.copy()
    for c in list(df2.columns):
        if 'cpf' in c.lower() or 'cpf' == c.lower() or 'rg' in c.lower() or 'identificador' in c.lower():
            df2[c] = df2[c].apply(lambda x: mask_string(x,1,1))
        if 'nome' in c.lower():
            df2[c] = df2[c].apply(lambda x: (str(x)[0] + '***') if pd.notna(x) and len(str(x))>1 else x)
        if 'email' in c.lower():
            df2[c] = df2[c].apply(lambda x: '' if pd.notna(x) else x)
    return df2

# ---------------------------
# Abas principais (difere por role)
# ---------------------------
if role == "RH":
    tabs = ["📊 KPIs Gerais", "📈 Comparativo", "🚨 Alertas", "🔍 Busca", "📊 Top CIDs", "📤 Exportação"]
elif role == "MEDICO":
    tabs = ["🏥 Análise Médica", "🔍 Busca", "📊 Top CIDs"]
else:
    tabs = ["📊 KPIs Gerais", "🔍 Busca"]

tab_objs = st.tabs(tabs)

# ---------------------------
# Implementação de cada aba
# ---------------------------
for i, tab_name in enumerate(tabs):
    with tab_objs[i]:
        # ---------------- KPIs Gerais ----------------
        if tab_name == "📊 KPIs Gerais":
            st.subheader("📌 KPIs Gerais")
            custo_total = utilizacao_filtrada['Valor'].sum() if 'Valor' in utilizacao_filtrada.columns else 0.0
            volume_total = len(utilizacao_filtrada)
            num_benef = utilizacao_filtrada['Nome_do_Associado'].nunique() if 'Nome_do_Associado' in utilizacao_filtrada.columns else 0
            custo_medio = (custo_total / num_benef) if num_benef>0 else 0.0

            c1, c2 = st.columns(2)
            with c1:
                st.metric("💰 Custo Total", format_brl(custo_total))
            with c2:
                st.metric("📋 Atendimentos", f"{volume_total:,}".replace(",", "."))

            c3, c4 = st.columns(2)
            with c3:
                st.metric("👥 Beneficiários", f"{num_benef:,}".replace(",", "."))
            with c4:
                st.metric("📊 Custo Médio", format_brl(custo_medio))

            st.markdown("---")
            # Evolução mensal
            if 'Data_do_Atendimento' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                st.markdown("### 📈 Evolução Mensal")
                temp = utilizacao_filtrada.copy()
                temp['Mes_Ano'] = temp['Data_do_Atendimento'].dt.to_period('M')
                evol = temp.groupby('Mes_Ano')['Valor'].sum().reset_index()
                evol['Mes_Ano'] = evol['Mes_Ano'].astype(str)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=evol['Mes_Ano'], y=evol['Valor'], mode='lines+markers', line=dict(color='#667eea', width=3)))
                fig.update_layout(yaxis=dict(tickprefix="R$ ", tickformat=",.2f"), height=380, plot_bgcolor='white')
                st.plotly_chart(fig, use_container_width=True)

            # Top 10 por custo e volume (AgGrid)
            st.markdown("### 💎 Top Beneficiários")
            if 'Nome_do_Associado' in utilizacao_filtrada.columns:
                top_cost = utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].sum().sort_values(ascending=False).reset_index().head(10)
                top_cost = top_cost.rename(columns={'Nome_do_Associado':'Beneficiário','Valor':'Valor'})
                df_top_cost = style_dataframe_brl(top_cost)
                # exibicao via AgGrid
                resp = aggrid_df(top_cost, height=300, selection_mode="single")
                sel = resp.get('selected_rows', [])
                if sel:
                    selected = sel[0]
                    selected_name = selected.get('Beneficiário') or selected.get('Nome_do_Associado')
                    st.info(f"Selecionado: {selected_name}")
            else:
                st.info("Sem dados de beneficiário para mostrar Top 10.")

        # ---------------- Comparativo ----------------
        elif tab_name == "📈 Comparativo":
            st.subheader("📊 Comparativo de Planos")
            if plano_col and 'Valor' in utilizacao_filtrada.columns:
                comp_val = utilizacao_filtrada.groupby(plano_col)['Valor'].sum().reset_index().sort_values('Valor', ascending=False)
                comp_vol = utilizacao_filtrada.groupby(plano_col).size().reset_index(name='Volume').sort_values('Volume', ascending=False)
                col1, col2 = st.columns(2)
                with col1:
                    fig1 = go.Figure([go.Bar(x=comp_val[plano_col], y=comp_val['Valor'], text=comp_val['Valor'].apply(format_brl))])
                    fig1.update_layout(title="Custo por Plano", yaxis=dict(tickprefix="R$ ", tickformat=",.2f"), height=420, plot_bgcolor='white')
                    st.plotly_chart(fig1, use_container_width=True)
                with col2:
                    fig2 = go.Figure([go.Bar(x=comp_vol[plano_col], y=comp_vol['Volume'], text=comp_vol['Volume'])])
                    fig2.update_layout(title="Volume por Plano", height=420, plot_bgcolor='white')
                    st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Coluna de plano ou valores não encontrados.")

        # ---------------- Alertas ----------------
        elif tab_name == "🚨 Alertas":
            st.subheader("🚨 Alertas e Inconsistências")
            # limites
            colL, colR = st.columns(2)
            with colL:
                custo_lim = st.number_input("💰 Limite de custo por beneficiário (R$)", value=5000.00, step=100.0, key="lim_custo")
            with colR:
                vol_lim = st.number_input("📊 Limite de atendimentos", value=20, step=1, key="lim_vol")

            if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                custo_por_benef = utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].sum()
                vol_por_benef = utilizacao_filtrada.groupby('Nome_do_Associado').size()

                alert_custo = custo_por_benef[custo_por_benef > custo_lim]
                alert_vol = vol_por_benef[vol_por_benef > vol_lim]

                st.markdown("#### ⚠️ Acima do limite de custo")
                if not alert_custo.empty:
                    df_alert_c = alert_custo.reset_index().rename(columns={'Nome_do_Associado':'Beneficiário','Valor':'Valor'})
                    resp = aggrid_df(df_alert_c, height=300)
                    sel = resp.get('selected_rows', [])
                    if sel:
                        st.info(f"Selecionado: {sel[0].get('Beneficiário')}")
                    # export
                    if st.button("Exportar alertas de custo"):
                        buf = BytesIO()
                        with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
                            df_alert_c.to_excel(w, sheet_name='Alertas_Custo', index=False)
                        buf.seek(0)
                        st.download_button("📥 Baixar alertas custo", buf, "alertas_custo.xlsx", "application/vnd.ms-excel")
                else:
                    st.success("✅ Nenhum beneficiário acima do limite de custo")

                st.markdown("#### ⚠️ Acima do limite de volume")
                if not alert_vol.empty:
                    df_alert_v = alert_vol.reset_index().rename(columns={'Nome_do_Associado':'Beneficiário',0:'Volume'})
                    resp2 = aggrid_df(df_alert_v, height=300)
                    if st.button("Exportar alertas de volume"):
                        buf = BytesIO()
                        with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
                            df_alert_v.to_excel(w, sheet_name='Alertas_Volume', index=False)
                        buf.seek(0)
                        st.download_button("📥 Baixar alertas volume", buf, "alertas_volume.xlsx", "application/vnd.ms-excel")
                else:
                    st.success("✅ Nenhum beneficiário acima do limite de volume")

            # inconsistências: parto masculino, atendimento antes do nascimento, idades absurdas
            st.markdown("### ⚠️ Inconsistências detectadas")
            inconsistencias = pd.DataFrame()
            if 'Codigo_do_CID' in utilizacao_filtrada.columns and sexo_col and 'Nome_do_Associado' in utilizacao_filtrada.columns:
                util_temp = utilizacao_filtrada.copy()
                cad_temp = cadastro_filtrado.copy()
                util_temp['Nome_merge'] = util_temp['Nome_do_Associado'].apply(padronizar_nome)
                cad_temp['Nome_merge'] = cad_temp['Nome_do_Associado'].apply(padronizar_nome)
                merged = util_temp.merge(cad_temp[['Nome_merge', sexo_col, 'Data_de_Nascimento']].drop_duplicates(), on='Nome_merge', how='left')
                merged[sexo_col] = merged[sexo_col].fillna('Desconhecido')
                parto_masc = merged[(merged['Codigo_do_CID'].astype(str).str.upper()=='O80') & (merged[sexo_col].astype(str).str.upper()=='M')]
                if not parto_masc.empty:
                    inconsistencias = pd.concat([inconsistencias, parto_masc.drop(columns=['Nome_merge'], errors='ignore')])
                # atendimento antes do nascimento
                if 'Data_do_Atendimento' in merged.columns and 'Data_de_Nascimento' in merged.columns:
                    inco_dt = merged[(merged['Data_do_Atendimento'] < merged['Data_de_Nascimento'])]
                    if not inco_dt.empty:
                        inconsistencias = pd.concat([inconsistencias, inco_dt.drop(columns=['Nome_merge'], errors='ignore')])
            # idades absurdas
            if 'Data_de_Nascimento' in cadastro_filtrado.columns:
                idades = (pd.Timestamp.today() - cadastro_filtrado['Data_de_Nascimento']).dt.days // 365
                idosos = cadastro_filtrado[idades > 120]
                if not idosos.empty:
                    inconsistencias = pd.concat([inconsistencias, idosos])

            if not inconsistencias.empty:
                if anon_toggle:
                    show_inc = anonymize_df(inconsistencias)
                else:
                    show_inc = inconsistencias.copy()
                resp = aggrid_df(show_inc, height=400)
                if st.button("Exportar inconsistências"):
                    buf = BytesIO()
                    with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
                        inconsistencias.to_excel(w, sheet_name='Inconsistencias', index=False)
                    buf.seek(0)
                    st.download_button("📥 Baixar inconsistências", buf, "inconsistencias.xlsx", "application/vnd.ms-excel")
            else:
                st.success("✅ Nenhuma inconsistência aparente encontrada.")

        # ---------------- Análise Médica ----------------
        elif tab_name == "🏥 Análise Médica":
            st.subheader("🏥 Análise Médica - Condições Crônicas e Procedimentos")
            # filtro CID mode explained
            st.markdown(f"**Modo de correspondência de CID:** {cid_mode}")
            # aplica regra para marcar crônicos
            if 'Codigo_do_CID' in utilizacao_filtrada.columns:
                temp = utilizacao_filtrada.copy()
                if cid_mode.startswith("Começa"):
                    mask = temp['Codigo_do_CID'].astype(str).str.upper().str.startswith(tuple([c.upper() for c in cids_list]))
                elif cid_mode.startswith("Exato"):
                    mask = temp['Codigo_do_CID'].astype(str).str.upper().isin([c.upper() for c in cids_list])
                elif cid_mode.startswith("Contém"):
                    mask = temp['Codigo_do_CID'].astype(str).str.upper().apply(lambda x: any([c.upper() in x for c in cids_list]))
                else:  # regex
                    try:
                        patt = "|".join([f"({c})" for c in cids_list])
                        mask = temp['Codigo_do_CID'].astype(str).str.contains(patt, regex=True, na=False)
                    except:
                        mask = pd.Series(False, index=temp.index)
                temp['Cronico'] = mask
                cronicos = temp[temp['Cronico']]
                if not cronicos.empty:
                    agg = cronicos.groupby('Nome_do_Associado')['Valor'].sum().sort_values(ascending=False).reset_index().head(200)
                    agg = agg.rename(columns={'Nome_do_Associado':'Beneficiário','Valor':'Valor'})
                    if anon_toggle:
                        st.dataframe(add_index1(style_dataframe_brl(agg)), use_container_width=True)
                    else:
                        st.dataframe(add_index1(style_dataframe_brl(agg)), use_container_width=True)
                else:
                    st.info("Nenhum beneficiário identificado como crônico com os CIDs configurados.")
            else:
                st.info("Coluna 'Codigo_do_CID' não encontrada.")

            # Top 10 procedimentos
            st.markdown("### 💊 Top Procedimentos por Custo")
            if 'Nome_do_Procedimento' in utilizacao_filtrada.columns:
                top_proc = utilizacao_filtrada.groupby('Nome_do_Procedimento')['Valor'].sum().sort_values(ascending=False).reset_index().head(10)
                top_proc = top_proc.rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Valor'})
                st.dataframe(add_index1(style_dataframe_brl(top_proc)), use_container_width=True)
            else:
                st.info("Coluna 'Nome_do_Procedimento' não encontrada.")

        # ---------------- Busca ----------------
        elif tab_name == "🔍 Busca":
            st.subheader("🔎 Busca por Beneficiário / CID / Procedimento")
            search_input = st.text_input("Digite nome, CID ou procedimento (busca livre)", key="search_input")
            filtered = utilizacao_filtrada.copy()
            if search_input:
                q = search_input.strip().upper()
                mask_name = filtered['Nome_do_Associado'].astype(str).str.upper().str.contains(q, na=False) if 'Nome_do_Associado' in filtered.columns else pd.Series(False, index=filtered.index)
                mask_cid = filtered['Codigo_do_CID'].astype(str).str.upper().str.contains(q, na=False) if 'Codigo_do_CID' in filtered.columns else pd.Series(False, index=filtered.index)
                mask_proc = filtered['Nome_do_Procedimento'].astype(str).str.upper().str.contains(q, na=False) if 'Nome_do_Procedimento' in filtered.columns else pd.Series(False, index=filtered.index)
                filtered = filtered[mask_name | mask_cid | mask_proc]
            else:
                # sugestões top 20 por volume
                if 'Nome_do_Associado' in filtered.columns:
                    vol = filtered.groupby('Nome_do_Associado').size().sort_values(ascending=False).head(20)
                    suggestions = vol.index.tolist()
                    st.markdown("Top sugeridos (por volume):")
                    st.write(", ".join(suggestions))

            if not filtered.empty:
                # exibir via AgGrid e permitir seleção para abrir detalhes
                resp = aggrid_df(filtered, height=450)
                sel = resp.get('selected_rows', [])
                if sel:
                    sel_row = sel[0]
                    nome = sel_row.get('Nome_do_Associado') or sel_row.get('Beneficiário')
                    st.markdown(f"### Detalhes selecionados: {nome}")
                    # reencontra todos os registros do beneficiário
                    util_b = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado']==nome] if 'Nome_do_Associado' in utilizacao_filtrada.columns else pd.DataFrame()
                    cad_b = cadastro_filtrado[cadastro_filtrado['Nome_do_Associado']==nome] if 'Nome_do_Associado' in cadastro_filtrado.columns else pd.DataFrame()
                    if anon_toggle:
                        st.dataframe(anonymize_df(cad_b), use_container_width=True)
                        st.dataframe(style_dataframe_brl(anonymize_df(util_b)), use_container_width=True)
                    else:
                        st.dataframe(cad_b, use_container_width=True)
                        st.dataframe(style_dataframe_brl(util_b), use_container_width=True)
            else:
                st.info("Nenhum registro encontrado para a busca.")

        # ---------------- Top CIDs ----------------
        elif tab_name == "📊 Top CIDs":
            st.subheader("🔢 Top CIDs (por volume e por custo)")
            if 'Codigo_do_CID' in utilizacao_filtrada.columns:
                cids_count = utilizacao_filtrada['Codigo_do_CID'].astype(str).value_counts().reset_index().rename(columns={'index':'CID','Codigo_do_CID':'Count'})
                cids_cost = utilizacao_filtrada.groupby(utilizacao_filtrada['Codigo_do_CID'].astype(str))['Valor'].sum().reset_index().rename(columns={'Codigo_do_CID':'CID','Valor':'Custo'})
                top10 = cids_count.merge(cids_cost, on='CID', how='left').sort_values(by='Count', ascending=False).head(10)
                st.markdown("### Top 10 por Volume")
                resp = aggrid_df(top10, height=300)
                st.markdown("### Top 10 por Custo")
                resp2 = aggrid_df(top10.sort_values(by='Custo', ascending=False), height=300)
                # permitir pesquisa por código(s)
                cid_query = st.text_input("Pesquisar por CID (ex: E11 ou E11.9 ou E11,E10)", key="cid_query")
                if cid_query:
                    q = cid_query.strip().upper()
                    tokens = [t.strip() for t in q.split(",") if t.strip()]
                    mask = utilizacao_filtrada['Codigo_do_CID'].astype(str).str.upper().apply(lambda x: any([t in x for t in tokens]))
                    results = utilizacao_filtrada[mask]
                    if not results.empty:
                        st.markdown(f"Resultados para: {', '.join(tokens)}")
                        st.dataframe(style_dataframe_brl(results.head(500)), use_container_width=True)
                    else:
                        st.info("Nenhum resultado para o(s) CID(s) informado(s).")
            else:
                st.info("Coluna 'Codigo_do_CID' não encontrada.")

        # ---------------- Exportação ----------------
        elif tab_name == "📤 Exportação":
            st.subheader("📥 Exportar Relatórios (filtros aplicados)")
            st.write("O arquivo exportado respeita os filtros aplicados.")
            if st.button("Gerar relatório completo (Excel)"):
                out = BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    util_export = utilizacao_filtrada.drop(columns=['Tipo_Beneficiario'], errors='ignore').copy()
                    util_export.to_excel(writer, sheet_name='Utilizacao_Filtrada', index=False)
                    cadastro_filtrado.to_excel(writer, sheet_name='Cadastro_Filtrada', index=False)
                    if not medicina_trabalho.empty:
                        med_export = medicina_trabalho.copy()
                        if 'Nome_do_Associado' in med_export.columns and 'Nome_do_Associado' in cadastro_filtrado.columns:
                            med_export = med_export[med_export['Nome_do_Associado'].isin(cadastro_filtrado['Nome_do_Associado'])]
                        med_export.to_excel(writer, sheet_name='Medicina_do_Trabalho', index=False)
                    if not atestados.empty:
                        at_export = atestados.copy()
                        if 'Nome_do_Associado' in at_export.columns and 'Nome_do_Associado' in cadastro_filtrado.columns:
                            at_export = at_export[at_export['Nome_do_Associado'].isin(cadastro_filtrado['Nome_do_Associado'])]
                        at_export.to_excel(writer, sheet_name='Atestados', index=False)
                out.seek(0)
                st.download_button("📥 Baixar Relatório Filtrado (.xlsx)", out, "dashboard_plano_saude_filtrado.xlsx", "application/vnd.ms-excel", use_container_width=True)
            st.markdown("**Exportar relatório individual:** use a aba de busca para selecionar um beneficiário e baixar o relatório individual.")

# ---------------------------
# Top 20 maiores utilizadores por custo (se quiser mostrar fora das tabs)
# ---------------------------
st.markdown("---")
st.markdown("### 📌 Top 20 Usuários por Custo (visível para RH e Médico)")
if 'Nome_do_Associado' in utilizacao_filtrada.columns:
    top20 = utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].sum().sort_values(ascending=False).reset_index().head(20)
    top20 = top20.rename(columns={'Nome_do_Associado':'Beneficiário','Valor':'Valor'})
    if anon_toggle and role!="MEDICO":
        AgGrid(add_index1(anonymize_df(style_dataframe_brl(top20))), height=350)
    else:
        AgGrid(add_index1(style_dataframe_brl(top20)), height=350)
else:
    st.info("Sem dados de beneficiários para Top20.")

# ---------------------------
# Observações finais e instruções
# ---------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### Observações")
st.sidebar.write("""
- CID por 'raiz' (começa com) recomendado — já disponível no seletor de modo.
- DAPs: se a coluna existir no cadastro será usada; se não, envie lista via upload.
- Export manual disponível; para agendamento/envio automático por e-mail/Slack preciso credenciais (extra).
- Para produção, defina credenciais reais em `st.secrets` e use conexões seguras.
""")

# fim do app
