import pandas as pd
import numpy as np
from unidecode import unidecode
import streamlit as st
import plotly.graph_objects as go

# ---------------------------
# 0. CONFIGURAÇÃO DE PÁGINA E TEMA
# ---------------------------
st.set_page_config(page_title="Dashboard Saúde", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3a5f 0%, #2d5a8c 100%); padding-top:2rem; }
[data-testid="stSidebar"] .stSelectbox label, .stTextInput label, h2,h3 { color:#fff !important; font-weight:600;}
[data-testid="stMetric"] { background: linear-gradient(135deg,#667eea 0%,#764ba2 100%); padding:1.5rem; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1); border:1px solid rgba(255,255,255,0.1);}
[data-testid="stMetric"] label { color:#fff !important; font-size:0.9rem; font-weight:500; text-transform:uppercase; letter-spacing:0.5px;}
[data-testid="stMetric"] [data-testid="stMetricValue"] { color:#fff !important; font-size:2rem; font-weight:700;}
.stTabs [data-baseweb="tab-list"] { gap:8px; background:#f8f9fa; padding:0.5rem; border-radius:10px;}
.stTabs [data-baseweb="tab"] { height:50px; border-radius:8px; color:#2d5a8c; font-weight:600; padding:0 1.5rem; transition:0.3s;}
.stTabs [data-baseweb="tab"]:hover { background: rgba(102,126,234,0.1);}
.stTabs [aria-selected="true"] { background: linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:white !important;}
.stButton button { border-radius:8px; font-weight:600; padding:0.75rem 2rem; transition:0.3s; background: linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:white; box-shadow:0 4px 15px rgba(102,126,234,0.3);}
.stButton button:hover { transform:translateY(-2px); box-shadow:0 6px 20px rgba(102,126,234,0.4);}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# 1. FUNÇÕES AUXILIARES
# ---------------------------
def format_brl(value):
    if pd.isna(value): return "R$ 0,00"
    value=float(value)
    return "R$ {:,.2f}".format(value).replace(",","TEMP").replace(".",",").replace("TEMP",".")

def style_dataframe_brl(df, value_cols=['Valor']):
    formatters={col:format_brl for col in value_cols if col in df.columns}
    return df.style.format(formatters) if formatters else df

def clean_cols(df):
    df.columns=[unidecode(col).strip().replace(" ","_").replace("-","_") for col in df.columns]
    return df

def normalize_name(s):
    return unidecode(str(s)).strip().upper()

# ---------------------------
# 2. AUTENTICAÇÃO
# ---------------------------
if "logged_in" not in st.session_state: st.session_state.logged_in=False; st.session_state.username=""; st.session_state.role=""
def login():
    st.sidebar.markdown("### 🔐 Login")
    username=st.sidebar.text_input("Usuário")
    password=st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar", use_container_width=True):
        credentials={"usernames":["rh_teste","medico_teste"],"passwords":["senha_rh","senha_med"],"roles":["RH","MEDICO"]}
        if username in credentials["usernames"]:
            idx=credentials["usernames"].index(username)
            if password==credentials["passwords"][idx]:
                st.session_state.logged_in=True
                st.session_state.username=username
                st.session_state.role=credentials["roles"][idx]
                st.success(f"✅ Bem-vindo(a), {username}!")
                st.experimental_rerun()
            else: st.error("❌ Senha incorreta")
        else: st.error("❌ Usuário não encontrado")

if not st.session_state.logged_in:
    login()
else:
    role=st.session_state.role
    # ---------------------------
    # HEADER
    # ---------------------------
    col1,col2=st.columns([3,1])
    with col1: st.title("🏥 Dashboard Plano de Saúde")
    with col2: st.markdown(f"<div style='text-align:right;color:#667eea;font-weight:600'>{role}<br>{st.session_state.username}</div>", unsafe_allow_html=True)

    # ---------------------------
    # UPLOAD
    # ---------------------------
    uploaded_file=st.file_uploader("📁 Escolha o arquivo .xlsx", type="xlsx")
    if uploaded_file:
        sheets=pd.read_excel(uploaded_file, sheet_name=None)
        utilizacao=clean_cols(sheets.get('Utilizacao', pd.DataFrame()))
        cadastro=clean_cols(sheets.get('Cadastro', pd.DataFrame()))

        if 'Valor' in utilizacao.columns:
            utilizacao['Valor']=pd.to_numeric(utilizacao['Valor'].astype(str).str.replace(r'[^\d\.\,]','',regex=True).str.replace(',',''), errors='coerce')
        if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
            utilizacao['Tipo_Beneficiario']=np.where(utilizacao['Nome_Titular']==utilizacao['Nome_do_Associado'],'Titular','Dependente')
        else: utilizacao['Tipo_Beneficiario']='Desconhecido'

        # ---------------------------
        # FILTROS SIDEBAR
        # ---------------------------
        st.sidebar.markdown("### 🎯 Filtros")
        sexo_col=[c for c in cadastro.columns if 'sexo' in c.lower()]
        sexo_filtro=st.sidebar.multiselect("👤 Sexo", options=cadastro[sexo_col[0]].dropna().unique() if sexo_col else [], default=cadastro[sexo_col[0]].dropna().unique() if sexo_col else [])
        tipo_benef_filtro=st.sidebar.multiselect("👥 Tipo Beneficiário", options=utilizacao['Tipo_Beneficiario'].unique(), default=utilizacao['Tipo_Beneficiario'].unique())
        periodo_min=utilizacao['Data_do_Atendimento'].min() if 'Data_do_Atendimento' in utilizacao.columns else pd.Timestamp.today()
        periodo_max=utilizacao['Data_do_Atendimento'].max() if 'Data_do_Atendimento' in utilizacao.columns else pd.Timestamp.today()
        periodo=st.sidebar.date_input("📆 Período", [periodo_min, periodo_max])

        # Aplicar filtros
        utilizacao_filtrada=utilizacao.copy()
        if 'Data_do_Atendimento' in utilizacao_filtrada.columns:
            utilizacao_filtrada=utilizacao_filtrada[(utilizacao_filtrada['Data_do_Atendimento']>=pd.to_datetime(periodo[0])) & (utilizacao_filtrada['Data_do_Atendimento']<=pd.to_datetime(periodo[1]))]
        if tipo_benef_filtro:
            utilizacao_filtrada=utilizacao_filtrada[utilizacao_filtrada['Tipo_Beneficiario'].isin(tipo_benef_filtro)]
        if sexo_col:
            cad_filtrado=cadastro[cadastro[sexo_col[0]].isin(sexo_filtro)]
            if 'Nome_do_Associado' in cad_filtrado.columns:
                utilizacao_filtrada=utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'].isin(cad_filtrado['Nome_do_Associado'])]

        # ---------------------------
        # DASHBOARD TABS
        # ---------------------------
        tabs=["📊 KPIs Gerais","📈 Evolução Temporal","📈 Comparativo","🚨 Alertas","🔍 Busca","📤 Exportação"] if role=="RH" else ["🏥 Análise Médica","🔍 Busca"]
        tab_objs=st.tabs(tabs)

        for i, tab_name in enumerate(tabs):
            with tab_objs[i]:
                if tab_name=="📊 KPIs Gerais":
                    st.markdown("### 📌 Indicadores Principais")
                    custo_total=utilizacao_filtrada['Valor'].sum() if 'Valor' in utilizacao_filtrada.columns else 0
                    volume_total=len(utilizacao_filtrada)
                    num_beneficiarios=utilizacao_filtrada['Nome_do_Associado'].nunique() if 'Nome_do_Associado' in utilizacao_filtrada.columns else 0
                    custo_medio=custo_total/num_beneficiarios if num_beneficiarios>0 else 0
                    c1,c2,c3,c4=st.columns(4)
                    c1.metric("💰 Custo Total", format_brl(custo_total))
                    c2.metric("📋 Atendimentos", f"{volume_total:,}".replace(',','.'))
                    c3.metric("👥 Beneficiários", f"{num_beneficiarios:,}".replace(',','.'))
                    c4.metric("📊 Custo Médio", format_brl(custo_medio))

                elif tab_name=="📈 Evolução Temporal":
                    st.markdown("### 📈 Evolução de Custos Mensal")
                    if 'Data_do_Atendimento' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        df_temp=utilizacao_filtrada.copy()
                        df_temp['Mes_Ano']=df_temp['Data_do_Atendimento'].dt.to_period('M')
                        evolucao=df_temp.groupby('Mes_Ano')['Valor'].sum().reset_index()
                        evolucao['Mes_Ano']=evolucao['Mes_Ano'].astype(str)
                        fig=go.Figure()
                        fig.add_trace(go.Scatter(x=evolucao['Mes_Ano'], y=evolucao['Valor'], mode='lines+markers', line=dict(color='#667eea', width=3), marker=dict(size=8, color='#764ba2'), fill='tozeroy', fillcolor='rgba(102,126,234,0.1)'))
                        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', yaxis=dict(tickprefix="R$ ", tickformat=",.2f"), height=400, hovermode='x unified')
                        st.plotly_chart(fig, use_container_width=True)

                elif tab_name=="📈 Comparativo":
                    st.markdown("### 📊 Comparativo por Plano")
                    plano_col=[c for c in utilizacao_filtrada.columns if 'plano' in c.lower() and 'descricao' in c.lower()]
                    if plano_col and 'Valor' in utilizacao_filtrada.columns:
                        plano_col=plano_col[0]
                        comp=utilizacao_filtrada.groupby(plano_col)['Valor'].sum().reset_index()
                        fig=go.Figure(data=[go.Bar(x=comp[plano_col], y=comp['Valor'], text=comp['Valor'].apply(format_brl), textposition='outside', marker_color='#667eea')])
                        fig.update_layout(title="Custo por Plano", plot_bgcolor='white', paper_bgcolor='white', yaxis=dict(tickprefix="R$ ", tickformat=",.2f"), height=400)
                        st.plotly_chart(fig,use_container_width=True)

                elif tab_name=="🚨 Alertas":
                    st.markdown("### 🚨 Alertas")
                    custo_lim=st.number_input("💰 Limite de custo (R$)", value=5000.00)
                    vol_lim=st.number_input("📊 Limite de atendimentos", value=20)
                    custo_por_benef=utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].sum()
                    top10_volume=utilizacao_filtrada.groupby('Nome_do_Associado').size()
                    alert_custo=custo_por_benef[custo_por_benef>custo_lim]
                    alert_vol=top10_volume[top10_volume>vol_lim]
                    c1,c2=st.columns(2)
                    with c1:
                        if not alert_custo.empty:
                            st.markdown("#### ⚠️ Acima do Limite de Custo")
                            st.dataframe(style_dataframe_brl(alert_custo.reset_index().rename(columns={'Nome_do_Associado':'Beneficiário','Valor':'Valor'})))
                        else: st.success("✅ Nenhum alerta de custo")
                    with c2:
                        if not alert_vol.empty:
                            st.markdown("#### ⚠️ Acima do Limite de Volume")
                            st.dataframe(style_dataframe_brl(alert_vol.reset_index().rename(columns={'Nome_do_Associado':'Beneficiário',0:'Volume'}), value_cols=[]))
                        else: st.success("✅ Nenhum alerta de volume")

                elif tab_name=="🔍 Busca":
                    st.markdown("### 🔍 Busca Beneficiário")
                    search_name=st.text_input("Digite o nome")
                    if search_name:
                        norm_name=normalize_name(search_name)
                        df_result=utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'].apply(lambda x: normalize_name(x)==norm_name)]
                        st.dataframe(style_dataframe_brl(df_result))

                elif tab_name=="📤 Exportação":
                    st.markdown("### 📤 Exportar Dados")
                    st.download_button("⬇️ Exportar Utilização", data=utilizacao_filtrada.to_csv(index=False).encode('utf-8'), file_name='utilizacao_filtrada.csv')
                    st.download_button("⬇️ Exportar Cadastro", data=cadastro.to_csv(index=False).encode('utf-8'), file_name='cadastro.csv')
