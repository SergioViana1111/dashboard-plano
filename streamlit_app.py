import os
import tempfile
import shutil
import pandas as pd
import numpy as np
from unidecode import unidecode
import streamlit as st
import plotly.express as px
from io import BytesIO
from datetime import datetime

# ---------------------------
# Configuração do Streamlit
# ---------------------------
st.set_page_config(page_title="Dashboard Plano de Saúde", layout="wide")
st.title("📊 Dashboard de Utilização do Plano de Saúde")

# --- Senhas via ENV (mude em produção) ---
MEDICO_PASSWORD = os.environ.get("MEDICO_PASSWORD", "medico123")
GESTOR_PASSWORD = os.environ.get("GESTOR_PASSWORD", "gestor123")

# ---------------------------
# Utilitários
# ---------------------------
def clean_cols(df):
    df = df.copy()
    df.columns = [unidecode(str(col)).strip().replace(' ', '_').replace('-', '_') for col in df.columns]
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
    s = str(s) if pd.notna(s) else ""
    if not s or len(s) <= (keep_start + keep_end):
        return "*" * len(s)
    return s[:keep_start] + "*" * (len(s) - keep_start - keep_end) + s[-keep_end:]

# ---------------------------
# Autenticação simples (roles)
# ---------------------------
st.sidebar.header("Acesso")
role = st.sidebar.radio("Entrar como:", ["Visitante (anonimizado)", "Gestor/RH", "Médico (detalhado)"])
user_role = "visitante"
if role == "Visitante (anonimizado)":
    st.sidebar.info("Visão agregada e anonimizada.")
    user_role = "visitante"
elif role == "Gestor/RH":
    pwd = st.sidebar.text_input("Senha Gestor/RH", type="password")
    if pwd:
        if pwd == GESTOR_PASSWORD:
            st.sidebar.success("Acesso Gestor liberado")
            user_role = "gestor"
        else:
            st.sidebar.error("Senha incorreta (Gestor).")
            user_role = "visitante"
elif role == "Médico (detalhado)":
    pwd = st.sidebar.text_input("Senha Médico", type="password")
    if pwd:
        if pwd == MEDICO_PASSWORD:
            st.sidebar.success("Acesso Médico liberado")
            user_role = "medico"
        else:
            st.sidebar.error("Senha incorreta (Médico).")
            user_role = "visitante"

# ---------------------------
# Uploads (robusto para .xltx)
# ---------------------------
st.sidebar.header("Dados / Configurações")
uploaded_file = st.sidebar.file_uploader(
    "Enviar arquivo (xlsx / xls / xltx / csv). Se der problema, peça para salvar como .xlsx ou .csv",
    type=None
)
cids_file = st.sidebar.file_uploader("Upload lista CIDs crônicos (txt/csv) - um por linha (opcional)", type=['txt','csv'])
copart_file = st.sidebar.file_uploader("Upload arquivo Coparticipação (opcional)", type=['xlsx','xls','csv'])

# anonimização toggle (desabilitado para médico)
anon_toggle = st.sidebar.checkbox("Mostrar dados anonimizados (mascarar nomes/CPF)", value=True if user_role!="medico" else False, disabled=(user_role=="medico"))

# processa cids upload
if cids_file:
    try:
        raw = cids_file.read()
        try:
            txt = raw.decode('utf-8')
        except Exception:
            try:
                txt = raw.decode('latin1')
            except Exception:
                txt = str(raw)
        cids_list = [x.strip().upper() for x in txt.splitlines() if x.strip()]
    except Exception:
        cids_list = []
else:
    cids_list = ['E11','I10','J45']  # default (pode ser substituído por upload)

@st.cache_data(ttl=600)
def read_input(file_obj, filename=None):
    sheets = {}
    name = filename or getattr(file_obj, "name", "")
    name = name.lower() if name else ""
    try:
        file_obj.seek(0)
    except Exception:
        pass

    # CSV attempt
    if name.endswith('.csv'):
        try:
            df = pd.read_csv(file_obj)
            sheets['Utilizacao'] = df
            return sheets
        except Exception:
            pass

    # Excel attempt (openpyxl)
    try:
        xls = pd.ExcelFile(file_obj, engine='openpyxl')
        for s in xls.sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=s, engine='openpyxl')
            except Exception:
                df = pd.read_excel(xls, sheet_name=s)
            sheets[s] = df
        return sheets
    except Exception:
        # fallback write temp file then read
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
        except Exception as e:
            st.error("Não foi possível ler o arquivo. Peça ao cliente para salvar como .xlsx ou .csv e reenviar.")
            st.error(f"Erro de leitura: {e}")
            return {}

if uploaded_file is None:
    st.info("Aguardando upload do arquivo (recomendo .xlsx ou .csv).")
    st.stop()

sheets = read_input(uploaded_file, filename=getattr(uploaded_file, "name", None))
if not sheets:
    st.stop()

# ---------------------------
# Extrai abas esperadas
# ---------------------------
utilizacao = sheets.get('Utilizacao', sheets.get('utilizacao', pd.DataFrame())).copy()
cadastro = sheets.get('Cadastro', sheets.get('cadastro', pd.DataFrame())).copy()
medicina_trabalho = sheets.get('Medicina_do_Trabalho', pd.DataFrame()).copy()
atestados = sheets.get('Atestados', pd.DataFrame()).copy()

# ---------------------------
# Padroniza colunas e datas
# ---------------------------
utilizacao = clean_cols(utilizacao)
cadastro = clean_cols(cadastro)
medicina_trabalho = clean_cols(medicina_trabalho)
atestados = clean_cols(atestados)

date_cols_util = ['Data_do_Atendimento','Competencia','Data_de_Nascimento']
date_cols_cad = ['Data_de_Nascimento','Data_de_Admissao_do_Empregado','Data_de_Adesao_ao_Plano','Data_de_Cancelamento']
date_cols_med = ['Data_do_Exame']
date_cols_at = ['Data_do_Afastamento']

utilizacao = ensure_datetime(utilizacao, date_cols_util)
cadastro = ensure_datetime(cadastro, date_cols_cad)
medicina_trabalho = ensure_datetime(medicina_trabalho, date_cols_med)
atestados = ensure_datetime(atestados, date_cols_at)

# garante Valor numérico
if 'Valor' in utilizacao.columns:
    utilizacao['Valor'] = pd.to_numeric(utilizacao['Valor'], errors='coerce').fillna(0.0)
else:
    utilizacao['Valor'] = 0.0

# Tipo Beneficiário
if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
    utilizacao['Tipo_Beneficiario'] = np.where(
        utilizacao['Nome_Titular'].fillna('').str.strip() == utilizacao['Nome_do_Associado'].fillna('').str.strip(),
        'Titular', 'Dependente'
    )
else:
    utilizacao['Tipo_Beneficiario'] = 'Desconhecido'

# ---------------------------
# Sidebar filtros (defaults seguros)
# ---------------------------
st.sidebar.subheader("Filtros")
possible_sexo_cols = [c for c in cadastro.columns if 'sexo' in c.lower()]
sexo_col = possible_sexo_cols[0] if possible_sexo_cols else None
sexo_opts = list(cadastro[sexo_col].dropna().unique()) if sexo_col else []
sexo_filtro = st.sidebar.multiselect("Sexo", options=sexo_opts, default=sexo_opts)

tipo_benef_opts = list(utilizacao['Tipo_Beneficiario'].dropna().unique())
tipo_benef_filtro = st.sidebar.multiselect("Tipo Beneficiário", options=tipo_benef_opts, default=tipo_benef_opts)

municipio_filtro = None
if 'Municipio_do_Participante' in cadastro.columns:
    municipio_opts = list(cadastro['Municipio_do_Participante'].dropna().unique())
    municipio_filtro = st.sidebar.multiselect("Município do Participante", options=municipio_opts, default=municipio_opts)

faixa_etaria = st.sidebar.slider("Faixa Etária", 0, 120, (18,65))

if 'Data_do_Atendimento' in utilizacao.columns and not utilizacao['Data_do_Atendimento'].isna().all():
    periodo_min = utilizacao['Data_do_Atendimento'].min().date()
    periodo_max = utilizacao['Data_do_Atendimento'].max().date()
else:
    periodo_min = datetime.today().date()
    periodo_max = datetime.today().date()
periodo = st.sidebar.date_input("Período (início / fim)", [periodo_min, periodo_max])

st.sidebar.markdown("### Limites de alerta")
custo_lim = st.sidebar.number_input("Limite de custo (R$)", value=5000)
vol_lim = st.sidebar.number_input("Limite de atendimentos", value=20)

possible_plano_cols = [c for c in utilizacao.columns if 'plano' in c.lower()]
plano_col = possible_plano_cols[0] if possible_plano_cols else None
plano_opts = list(utilizacao[plano_col].dropna().unique()) if plano_col else []
planos_filtro = st.sidebar.multiselect("Planos", options=plano_opts, default=plano_opts)

# ---------------------------
# Aplicar filtros (cópias para evitar SettingWithCopy)
# ---------------------------
cadastro_filtrado = cadastro.copy()
if 'Data_de_Nascimento' in cadastro_filtrado.columns:
    idade = (pd.Timestamp.today() - cadastro_filtrado['Data_de_Nascimento']).dt.days // 365
    cadastro_filtrado = cadastro_filtrado[(idade >= faixa_etaria[0]) & (idade <= faixa_etaria[1])]
if sexo_filtro and sexo_col:
    cadastro_filtrado = cadastro_filtrado[cadastro_filtrado[sexo_col].isin(sexo_filtro)]
if municipio_filtro is not None and 'Municipio_do_Participante' in cadastro_filtrado.columns:
    cadastro_filtrado = cadastro_filtrado[cadastro_filtrado['Municipio_do_Participante'].isin(municipio_filtro)]

utilizacao_filtrada = utilizacao.copy()
if tipo_benef_filtro:
    utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Tipo_Beneficiario'].isin(tipo_benef_filtro)]
if plano_col and planos_filtro:
    utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada[plano_col].isin(planos_filtro)]

# restringe por nomes presentes no cadastro filtrado (se existir coluna)
if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Nome_do_Associado' in cadastro_filtrado.columns:
    nomes_validos = cadastro_filtrado['Nome_do_Associado'].dropna().unique()
    utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'].isin(nomes_validos)]

# filtra por periodo
if 'Data_do_Atendimento' in utilizacao_filtrada.columns:
    util_mask = (utilizacao_filtrada['Data_do_Atendimento'] >= pd.to_datetime(periodo[0])) & \
                (utilizacao_filtrada['Data_do_Atendimento'] <= pd.to_datetime(periodo[1]))
    utilizacao_filtrada = utilizacao_filtrada[util_mask]

# ---------------------------
# Anonimização (aplica conforme toggle/role)
# ---------------------------
def anonymize_df(df, cols_to_mask=['Nome_do_Associado','CPF_Titular','CPF']):
    df = df.copy()
    for c in cols_to_mask:
        if c in df.columns:
            df[c] = df[c].apply(lambda x: mask_string(x,1,1))
    sensitive_cols = [c for c in df.columns if 'cpf' in c.lower() or 'rg' in c.lower()]
    for c in sensitive_cols:
        if c in df.columns and c not in cols_to_mask:
            df[c] = df[c].apply(lambda x: mask_string(x,1,1))
    return df

util_visible = anonymize_df(utilizacao_filtrada) if anon_toggle and user_role!="medico" else utilizacao_filtrada.copy()
cad_visible = anonymize_df(cadastro_filtrado) if anon_toggle and user_role!="medico" else cadastro_filtrado.copy()

# ---------------------------
# Abas
# ---------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "KPIs Gerais",
    "Comparativo de Planos",
    "Alertas & Inconsistências",
    "CIDs Crônicos & Procedimentos",
    "Exportação"
])

# ---------------------------
# Tab1 - KPIs
# ---------------------------
with tab1:
    st.subheader("📌 KPIs Gerais")
    custo_total = util_visible['Valor'].sum() if 'Valor' in util_visible.columns else 0.0
    n_atend = len(util_visible)
    n_benef = util_visible['Nome_do_Associado'].nunique() if 'Nome_do_Associado' in util_visible.columns else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Custo Total (R$)", f"{custo_total:,.2f}")
    c2.metric("Nº Atendimentos", f"{n_atend:,}")
    c3.metric("Beneficiários distintos", f"{n_benef:,}")

    if 'Nome_do_Associado' in util_visible.columns:
        custo_por_benef = util_visible.groupby('Nome_do_Associado')['Valor'].sum().sort_values(ascending=False).reset_index()
        st.write("**Top 10 Beneficiários por Custo**")
        st.dataframe(custo_por_benef.head(10).rename(columns={'Nome_do_Associado':'Nome do Associado','Valor':'Valor (R$)'}))

    if 'Data_do_Atendimento' in util_visible.columns:
        df_evol = util_visible.copy()
        df_evol['Mes_Ano'] = df_evol['Data_do_Atendimento'].dt.to_period('M').astype(str)
        evol = df_evol.groupby('Mes_Ano')['Valor'].sum().reset_index().sort_values('Mes_Ano')
        fig = px.bar(evol, x='Mes_Ano', y='Valor', text='Valor', labels={'Mes_Ano':'Mês/Ano','Valor':'R$'})
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# Tab2 - Comparativo de Planos
# ---------------------------
with tab2:
    st.subheader("📊 Comparativo de Planos")
    if plano_col:
        comp_value = util_visible.groupby(plano_col)['Valor'].sum().reset_index().sort_values('Valor', ascending=False)
        comp_vol = util_visible.groupby(plano_col).size().reset_index(name='Volume').sort_values('Volume', ascending=False)
        st.write("Valor por Plano")
        st.plotly_chart(px.bar(comp_value, x=plano_col, y='Valor', text='Valor'), use_container_width=True)
        st.write("Volume por Plano")
        st.plotly_chart(px.bar(comp_vol, x=plano_col, y='Volume', text='Volume'), use_container_width=True)
    else:
        st.info("Coluna de plano não encontrada. Verifique o arquivo.")

# ---------------------------
# Tab3 - Alertas & Inconsistências
# ---------------------------
with tab3:
    st.subheader("🚨 Alertas")
    if 'Nome_do_Associado' in util_visible.columns:
        custo_por_benef = util_visible.groupby('Nome_do_Associado')['Valor'].sum()
        vol_por_benef = util_visible.groupby('Nome_do_Associado').size()

        alert_custo = custo_por_benef[custo_por_benef > custo_lim].sort_values(ascending=False)
        alert_vol = vol_por_benef[vol_por_benef > vol_lim].sort_values(ascending=False)

        if not alert_custo.empty:
            st.write("**Beneficiários acima do limite de custo**")
            st.dataframe(alert_custo.reset_index().rename(columns={'Nome_do_Associado':'Nome','Valor':'Valor (R$)'}))
        else:
            st.write("Nenhum beneficiário acima do limite de custo.")

        if not alert_vol.empty:
            st.write("**Beneficiários acima do limite de volume**")
            st.dataframe(alert_vol.reset_index().rename(columns={'Nome_do_Associado':'Nome',0:'Volume'}))
        else:
            st.write("Nenhum beneficiário acima do limite de volume.")

        if st.button("Exportar alertas"):
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
                if not alert_custo.empty:
                    alert_custo.reset_index().to_excel(w, sheet_name='Alertas_Custo', index=False)
                if not alert_vol.empty:
                    alert_vol.reset_index().to_excel(w, sheet_name='Alertas_Volume', index=False)
            buf.seek(0)
            st.download_button("📥 Baixar Alertas", buf, "alertas.xlsx", "application/vnd.ms-excel")

    st.subheader("⚠️ Inconsistências")
    inconsistencias = pd.DataFrame()
    if sexo_col and 'Codigo_do_CID' in utilizacao.columns:
        util_copy = utilizacao_filtrada.copy()
        if 'Nome_do_Associado' in util_copy.columns and 'Nome_do_Associado' in cadastro_filtrado.columns:
            util_copy['Nome_merge'] = util_copy['Nome_do_Associado'].apply(padronizar_nome)
            cadastro_filtrado['Nome_merge'] = cadastro_filtrado['Nome_do_Associado'].apply(padronizar_nome)
            merged = util_copy.merge(cadastro_filtrado[['Nome_merge', sexo_col, 'Data_de_Nascimento']].drop_duplicates(), on='Nome_merge', how='left')
            merged[sexo_col] = merged[sexo_col].fillna('Desconhecido')
            parto_masc = merged[(merged['Codigo_do_CID'].astype(str).str.upper() == 'O80') & (merged[sexo_col].astype(str).str.upper() == 'M')]
            if not parto_masc.empty:
                inconsistencias = pd.concat([inconsistencias, parto_masc])
            if 'Data_do_Atendimento' in merged.columns and 'Data_de_Nascimento' in merged.columns:
                inco_dt = merged[(merged['Data_do_Atendimento'] < merged['Data_de_Nascimento'])]
                if not inco_dt.empty:
                    inconsistencias = pd.concat([inconsistencias, inco_dt])
    # idade absurda no cadastro
    if 'Data_de_Nascimento' in cadastro_filtrado.columns:
        idade = (pd.Timestamp.today() - cadastro_filtrado['Data_de_Nascimento']).dt.days // 365
        idosos = cadastro_filtrado[idade > 120]
        if not idosos.empty:
            inconsistencias = pd.concat([inconsistencias, idosos])

    if not inconsistencias.empty:
        show_inc = anonymize_df(inconsistencias) if anon_toggle and user_role!="medico" else inconsistencias
        st.dataframe(show_inc.head(300))
        if st.button("Exportar inconsistências"):
            b = BytesIO()
            with pd.ExcelWriter(b, engine='xlsxwriter') as w:
                inconsistencias.to_excel(w, sheet_name='Inconsistencias', index=False)
            b.seek(0)
            st.download_button("📥 Baixar Inconsistências", b, "inconsistencias.xlsx", "application/vnd.ms-excel")
    else:
        st.write("Nenhuma inconsistência encontrada.")

# ---------------------------
# Tab4 - CIDs crônicos & procedimentos
# ---------------------------
with tab4:
    st.subheader("🏥 Beneficiários Crônicos")
    if 'Codigo_do_CID' in utilizacao_filtrada.columns:
        dfc = utilizacao_filtrada.copy()
        dfc['Codigo_do_CID'] = dfc['Codigo_do_CID'].astype(str).str.upper().str.strip()
        dfc['Cronico'] = dfc['Codigo_do_CID'].isin([c.upper() for c in cids_list])
        cronicos = dfc[dfc['Cronico']].groupby('Nome_do_Associado')['Valor'].sum().sort_values(ascending=False).reset_index()
        show_cron = anonymize_df(cronicos) if anon_toggle and user_role!="medico" else cronicos
        st.dataframe(show_cron.head(200))
    else:
        st.info("Coluna Codigo_do_CID não encontrada.")

    st.subheader("💊 Top Procedimentos")
    if 'Nome_do_Procedimento' in utilizacao_filtrada.columns:
        top_proc = utilizacao_filtrada.groupby('Nome_do_Procedimento')['Valor'].sum().sort_values(ascending=False).head(10).reset_index()
        st.dataframe(top_proc.rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Valor (R$)'}))
    else:
        st.info("Coluna Nome_do_Procedimento não encontrada.")

# ---------------------------
# Tab5 - Exportação
# ---------------------------
with tab5:
    st.subheader("📤 Exportar Relatórios (filtros aplicados)")
    if st.button("Gerar relatório completo (Excel)"):
        out = BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            util_visible.to_excel(writer, sheet_name='Utilizacao', index=False)
            cad_visible.to_excel(writer, sheet_name='Cadastro', index=False)
            if not medicina_trabalho.empty:
                medicina_trabalho.to_excel(writer, sheet_name='Medicina_do_Trabalho', index=False)
            if not atestados.empty:
                atestados.to_excel(writer, sheet_name='Atestados', index=False)
        out.seek(0)
        st.download_button("📥 Baixar Relatório (Excel)", out, "dashboard_plano_saude.xlsx", "application/vnd.ms-excel")

    st.markdown("**Exportação para PDF:** use imprimir/salvar como PDF do navegador ou solicite geração automática por biblioteca adicional.")

    if copart_file:
        try:
            cp_sheets = read_input(copart_file)
            st.write("Arquivo de coparticipação recebido — visualização rápida")
            first = next(iter(cp_sheets))
            st.dataframe(cp_sheets[first].head(20))
        except Exception as e:
            st.error("Erro ao ler coparticipação: " + str(e))

# ---------------------------
# Observações de segurança / deploy
# ---------------------------
st.sidebar.markdown("### Segurança & Deploy")
st.sidebar.write("""
- Em produção, defina senhas fortes nas variáveis MEDICO_PASSWORD e GESTOR_PASSWORD.
- Hospede no Streamlit Cloud ou VPS com HTTPS.
- Para ingestão automática, disponibilize CSVs em um bucket (S3/Drive) e adapte read_input.
""")
