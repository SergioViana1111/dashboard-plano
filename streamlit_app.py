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
    /* Importar fonte moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Reset de estilos gerais */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar moderna */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a5f 0%, #2d5a8c 100%);
        padding-top: 2rem;
    }
    
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-weight: 600;
    }
    
    /* Cards de métricas modernos */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    [data-testid="stMetric"] label {
        color: #ffffff !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }
    
    /* Títulos das seções */
    h1 {
        color: #1e3a5f;
        font-weight: 700;
        padding-bottom: 1rem;
        border-bottom: 3px solid #667eea;
        margin-bottom: 2rem;
    }
    
    h2, h3 {
        color: #2d5a8c;
        font-weight: 600;
        margin-top: 2rem;
    }
    
    /* Tabs modernas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 0.5rem;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent;
        border-radius: 8px;
        color: #2d5a8c;
        font-weight: 600;
        padding: 0 1.5rem;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(102, 126, 234, 0.1);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* Dataframes estilizados */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* Botões modernos */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Download button */
    .stDownloadButton button {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    /* Expanders modernos */
    [data-testid="stExpander"] {
        background-color: #f8f9fa;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* Input fields */
    .stTextInput input, .stNumberInput input {
        border-radius: 8px;
        border: 2px solid #e9ecef;
        padding: 0.75rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Alertas e mensagens */
    .stAlert {
        border-radius: 10px;
        border-left: 4px solid;
    }
    
    /*Scrollbar customizada */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #764ba2;
    }
    
    /* Cards customizados para KPIs */
    .kpi-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        transition: all 0.3s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# 1. FUNÇÕES DE FORMATAÇÃO E UTILIDADE
# ---------------------------
def format_brl(value):
    """Formata um float ou int para string no padrão monetário brasileiro (R$ 1.234,56)"""
    if pd.isna(value) or value is None:
        return "R$ 0,00"
    try:
        value = float(value)
    except:
        return "R$ 0,00"
    return "R$ {:,.2f}".format(value).replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")

def style_dataframe_brl(df, value_cols=['Valor']):
    """Aplica formatação monetária BR em colunas específicas de um DataFrame."""
    formatters = {}
    for col in value_cols:
        if col in df.columns:
            # Garante que a formatação BRL seja aplicada
            formatters[col] = format_brl
    
    # Formata Volume e outras colunas numéricas sem BRL
    if 'Volume' in df.columns and 'Volume' not in formatters:
        formatters['Volume'] = lambda x: '{:,.0f}'.format(x).replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    
    if formatters:
        return df.style.format(formatters)
    return df

def normalize_name(s):
    """Normaliza o nome para busca (remove acentos, espaços e converte para maiúsculas)"""
    return unidecode(str(s)).strip().upper()

# ---------------------------
# 2. AUTENTICAÇÃO E ESTADO DA SESSÃO
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
    st.session_state.username_input = st.sidebar.text_input(
        "Usuário", st.session_state.username_input
    )
    st.session_state.password_input = st.sidebar.text_input(
        "Senha", st.session_state.password_input, type="password"
    )
    
    # Credenciais de teste
    if 'credentials' not in st.secrets:
        st.secrets['credentials'] = {
            "usernames": ["rh_teste", "medico_teste"],
            "passwords": ["senha_rh", "senha_med"],
            "roles": ["RH", "MEDICO"]
        }

    if st.sidebar.button("Entrar", use_container_width=True):
        usernames = st.secrets["credentials"]["usernames"]
        passwords = st.secrets["credentials"]["passwords"]
        roles = st.secrets["credentials"]["roles"]
        
        if st.session_state.username_input in usernames:
            idx = usernames.index(st.session_state.username_input)
            if st.session_state.password_input == passwords[idx]:
                st.session_state.logged_in = True
                st.session_state.username = st.session_state.username_input
                st.session_state.role = roles[idx]
                st.session_state.selected_benef = None # Limpa o beneficiário selecionado no login
                st.success(f"✅ Bem-vindo(a), {st.session_state.username}!")
                # Substituição de st.experimental_rerun() por st.rerun()
                st.rerun() 
            else:
                st.error("❌ Senha incorreta")
        else:
            st.error("❌ Usuário não encontrado")

login()

# ---------------------------
# 3. DASHBOARD PRINCIPAL
# ---------------------------
if st.session_state.logged_in:
    role = st.session_state.role
    
    # Header moderno
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"🏥 Dashboard Plano de Saúde")
    with col2:
        st.markdown(f"""
        <div style='text-align: right; padding: 1rem;'>
            <p style='color: #667eea; font-weight: 600; margin: 0;'>{role}</p>
            <p style='color: #6c757d; font-size: 0.9rem; margin: 0;'>{st.session_state.username}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Upload de arquivo
    st.markdown("---")
    uploaded_file = st.file_uploader("📁 Escolha o arquivo .xltx", type=["xltx", "xlsx"]) # Adiciona .xlsx para compatibilidade
    
    if uploaded_file is not None:
        # Leitura das abas
        try:
            utilizacao = pd.read_excel(uploaded_file, sheet_name='Utilizacao')
            cadastro = pd.read_excel(uploaded_file, sheet_name='Cadastro')
        except ValueError as e:
            st.error(f"❌ Erro ao ler abas 'Utilizacao' ou 'Cadastro'. Verifique os nomes das abas no arquivo. Detalhe: {e}")
            st.stop()

        try:
            medicina_trabalho = pd.read_excel(uploaded_file, sheet_name='Medicina_do_Trabalho')
        except:
            medicina_trabalho = pd.DataFrame()
        try:
            atestados = pd.read_excel(uploaded_file, sheet_name='Atestados')
        except:
            atestados = pd.DataFrame()

        # ---------------------------
        # 4. PROCESSAMENTO DOS DADOS
        # ---------------------------
        @st.cache_data
        def clean_and_process(utilizacao, cadastro, medicina_trabalho, atestados):
            
            def clean_cols(df):
                df.columns = [unidecode(col).strip().replace(' ','_').replace('-','_').replace('(','').replace(')','').replace('/','_') for col in df.columns]
                return df
            
            utilizacao = clean_cols(utilizacao)
            cadastro = clean_cols(cadastro)
            medicina_trabalho = clean_cols(medicina_trabalho)
            atestados = clean_cols(atestados)

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

            # Conversão de valores
            if 'Valor' in utilizacao.columns:
                try:
                    if utilizacao['Valor'].dtype == 'object' or utilizacao['Valor'].dtype == np.dtype('object'):
                        # Remove tudo que não for dígito, ponto ou vírgula. Substitui vírgula por ponto.
                        utilizacao.loc[:, 'Valor'] = (utilizacao['Valor']
                                                      .astype(str)
                                                      .str.replace(r'[^\d\.\,]', '', regex=True)
                                                      .str.replace(',', '.', regex=False))
                    utilizacao.loc[:, 'Valor'] = pd.to_numeric(utilizacao['Valor'], errors='coerce')
                except Exception as e:
                    st.warning(f"⚠️ Erro ao converter a coluna 'Valor': {e}")

            # Tipo Beneficiário
            if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
                utilizacao['Tipo_Beneficiario'] = np.where(
                    utilizacao['Nome_Titular'] == utilizacao['Nome_do_Associado'],
                    'Titular', 'Dependente'
                )
            else:
                utilizacao['Tipo_Beneficiario'] = 'Desconhecido'
            
            return utilizacao, cadastro, medicina_trabalho, atestados
        
        utilizacao, cadastro, medicina_trabalho, atestados = clean_and_process(utilizacao, cadastro, medicina_trabalho, atestados)

        # ---------------------------
        # 5. FILTROS SIDEBAR
        # ---------------------------
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎯 Filtros")
        
        # Sexo
        possible_sexo_cols = [col for col in cadastro.columns if 'sexo' in col.lower()]
        sexo_col = possible_sexo_cols[0] if possible_sexo_cols else None
        sexo_opts = cadastro[sexo_col].dropna().unique() if sexo_col else []
        sexo_filtro = st.sidebar.multiselect("👤 Sexo", options=sexo_opts, default=sexo_opts)

        # Tipo Beneficiário
        tipo_benef_filtro = st.sidebar.multiselect(
            "👥 Tipo Beneficiário",
            options=utilizacao['Tipo_Beneficiario'].unique(),
            default=utilizacao['Tipo_Beneficiario'].unique()
        )

        # Município
        municipio_filtro = None
        if 'Municipio_do_Participante' in cadastro.columns:
            municipio_opts = cadastro['Municipio_do_Participante'].dropna().unique()
            municipio_filtro = st.sidebar.multiselect("📍 Município", options=municipio_opts, default=municipio_opts)

        # Faixa etária
        idade_max = int((pd.Timestamp.today() - cadastro['Data_de_Nascimento'].min()).days // 365) if 'Data_de_Nascimento' in cadastro.columns and not cadastro['Data_de_Nascimento'].empty else 100
        faixa_etaria = st.sidebar.slider("📅 Faixa Etária", 0, idade_max, (18, 65))

        # Período
        periodo_min = utilizacao['Data_do_Atendimento'].min() if 'Data_do_Atendimento' in utilizacao.columns and not utilizacao['Data_do_Atendimento'].empty else pd.Timestamp.today()
        periodo_max = utilizacao['Data_do_Atendimento'].max() if 'Data_do_Atendimento' in utilizacao.columns and not utilizacao['Data_do_Atendimento'].empty else pd.Timestamp.today()
        
        try:
            periodo = st.sidebar.date_input("📆 Período", [periodo_min, periodo_max])
            if len(periodo) == 2:
                data_inicio, data_fim = periodo
            else:
                data_inicio, data_fim = periodo[0], periodo[0]
        except:
            st.sidebar.warning("Datas inválidas. Resetando para hoje.")
            data_inicio, data_fim = pd.Timestamp.today().date(), pd.Timestamp.today().date()


        # ---------------------------
        # 6. APLICAR FILTROS
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
            # Filtra utilização apenas para beneficiários que passaram pelos filtros de cadastro
            utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'].isin(cadastro_filtrado['Nome_do_Associado'])]
            
        if 'Data_do_Atendimento' in utilizacao_filtrada.columns:
            utilizacao_filtrada = utilizacao_filtrada[
                (utilizacao_filtrada['Data_do_Atendimento'] >= pd.to_datetime(data_inicio)) &
                (utilizacao_filtrada['Data_do_Atendimento'] <= pd.to_datetime(data_fim))
            ]

        # ---------------------------
        # 7. PREPARAR BUSCA (Nomes Possíveis)
        # ---------------------------
        nomes_from_cad = set()
        if 'Nome_do_Associado' in cadastro_filtrado.columns:
            nomes_from_cad = set(cadastro_filtrado['Nome_do_Associado'].dropna().unique())
        nomes_from_util = set()
        if 'Nome_do_Associado' in utilizacao_filtrada.columns:
            nomes_from_util = set(utilizacao_filtrada['Nome_do_Associado'].dropna().unique())

        nomes_possiveis = sorted(list(nomes_from_cad.union(nomes_from_util)))
        
        # ---------------------------
        # 8. DASHBOARD TABS
        # ---------------------------
        if role == "RH":
            tabs = ["📊 KPIs Gerais", "📈 Comparativo", "🚨 Alertas", "🔍 Busca", "📤 Exportação"]
        elif role == "MEDICO":
            tabs = ["🏥 Análise Médica", "🔍 Busca"]
        else:
            tabs = []

        if not tabs:
            st.error("❌ Usuário sem perfil definido para visualização do dashboard.")
            st.stop()
            
        tab_objects = st.tabs(tabs)
        
        # ---------------------------
        # 9. CONTEÚDO DAS TABS
        # ---------------------------
        for i, tab_name in enumerate(tabs):
            with tab_objects[i]:
                
                # --- TAB 1: KPIs Gerais (RH ONLY) ---
                if tab_name == "📊 KPIs Gerais":
                    st.markdown("### 📌 Indicadores Principais")
                    
                    # Métricas em cards
                    custo_total = utilizacao_filtrada['Valor'].sum() if 'Valor' in utilizacao_filtrada.columns else 0
                    volume_total = len(utilizacao_filtrada)
                    num_beneficiarios = utilizacao_filtrada['Nome_do_Associado'].nunique() if 'Nome_do_Associado' in utilizacao_filtrada.columns else 0
                    custo_medio = custo_total / num_beneficiarios if num_beneficiarios > 0 else 0
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("💰 Custo Total", format_brl(custo_total))
                    with col2:
                        st.metric("📋 Atendimentos", f"{volume_total:,.0f}".replace(",", "."))
                    with col3:
                        st.metric("👥 Beneficiários", f"{num_beneficiarios:,.0f}".replace(",", "."))
                    with col4:
                        st.metric("📊 Custo Médio (p/ Benef.)", format_brl(custo_medio))
                    
                    st.markdown("---")
                    
                    # Gráfico de evolução temporal
                    if 'Data_do_Atendimento' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        st.markdown("### 📈 Evolução de Custos por Mês")
                        utilizacao_filtrada_temp = utilizacao_filtrada.copy()
                        utilizacao_filtrada_temp['Mes_Ano'] = utilizacao_filtrada_temp['Data_do_Atendimento'].dt.to_period('M')
                        evolucao = utilizacao_filtrada_temp.groupby('Mes_Ano')['Valor'].sum().reset_index()
                        evolucao['Mes_Ano'] = evolucao['Mes_Ano'].astype(str)
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=evolucao['Mes_Ano'],
                            y=evolucao['Valor'],
                            mode='lines+markers',
                            name='Custo',
                            line=dict(color='#667eea', width=3),
                            marker=dict(size=8, color='#764ba2'),
                            fill='tozeroy',
                            fillcolor='rgba(102, 126, 234, 0.1)'
                        ))
                        
                        fig.update_layout(
                            plot_bgcolor='white',
                            paper_bgcolor='white',
                            xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
                            yaxis=dict(showgrid=True, gridcolor='#f0f0f0', tickprefix="R$ ", tickformat=",.2f"),
                            hovermode='x unified',
                            height=400
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Top 10 beneficiários
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                            st.markdown("### 💎 Top 10 por Custo")
                            custo_por_benef = utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].sum().sort_values(ascending=False)
                            df_custo = custo_por_benef.head(10).reset_index().rename(columns={'Nome_do_Associado':'Beneficiário','Valor':'Valor'})
                            st.dataframe(style_dataframe_brl(df_custo), use_container_width=True, height=400)
                    
                    with col2:
                        if 'Nome_do_Associado' in utilizacao_filtrada.columns:
                            st.markdown("### 📊 Top 10 por Volume")
                            top10_volume = utilizacao_filtrada.groupby('Nome_do_Associado').size().sort_values(ascending=False)
                            df_volume = top10_volume.head(10).reset_index().rename(columns={'Nome_do_Associado':'Beneficiário',0:'Volume'})
                            st.dataframe(style_dataframe_brl(df_volume, value_cols=[]), use_container_width=True, height=400)

                # --- TAB 2: Comparativo (RH ONLY) ---
                elif tab_name == "📈 Comparativo":
                    possible_cols = [col for col in utilizacao_filtrada.columns if 'plano' in col.lower() and 'descricao' in col.lower()]
                    if possible_cols and 'Valor' in utilizacao_filtrada.columns:
                        plano_col = possible_cols[0]
                        st.markdown("### 📊 Análise por Plano")
                        
                        comp = utilizacao_filtrada.groupby(plano_col)['Valor'].sum().reset_index()
                        comp_volume = utilizacao_filtrada.groupby(plano_col).size().reset_index(name='Volume')
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            fig = go.Figure(data=[go.Bar(
                                x=comp[plano_col],
                                y=comp['Valor'],
                                marker=dict(
                                    color=comp['Valor'],
                                    colorscale='Viridis',
                                    showscale=True
                                ),
                                text=comp['Valor'].apply(format_brl),
                                textposition='outside'
                            )])
                            fig.update_layout(
                                title="Custo por Plano",
                                plot_bgcolor='white',
                                paper_bgcolor='white',
                                yaxis=dict(tickprefix="R$ ", tickformat=",.2f"),
                                height=400
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            fig2 = go.Figure(data=[go.Bar(
                                x=comp_volume[plano_col],
                                y=comp_volume['Volume'],
                                marker=dict(
                                    color=comp_volume['Volume'],
                                    colorscale='Blues',
                                    showscale=True
                                ),
                                text=comp_volume['Volume'],
                                textposition='outside'
                            )])
                            fig2.update_layout(
                                title="Volume por Plano",
                                plot_bgcolor='white',
                                paper_bgcolor='white',
                                height=400
                            )
                            st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("ℹ️ Coluna de plano ou valor não encontrada.")

                # --- TAB 3: Alertas (RH ONLY) ---
                elif tab_name == "🚨 Alertas":
                    st.markdown("### 🚨 Alertas e Inconsistências de Uso")
                    
                    col_lim_1, col_lim_2 = st.columns(2)
                    with col_lim_1:
                        custo_lim = st.number_input("💰 Limite de Custo Individual (R$)", value=5000.00, step=100.00)
                    with col_lim_2:
                        vol_lim = st.number_input("📊 Limite de Atendimentos (Volume)", value=20)

                    if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        custo_por_benef = utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].sum()
                        top10_volume = utilizacao_filtrada.groupby('Nome_do_Associado').size()
                        alert_custo = custo_por_benef[custo_por_benef > custo_lim]
                        alert_vol = top10_volume[top10_volume > vol_lim]

                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### ⚠️ Acima do Limite de Custo")
                            if not alert_custo.empty:
                                df_alert_custo = alert_custo.reset_index().rename(columns={'Nome_do_Associado':'Beneficiário','Valor':'Valor'})
                                st.dataframe(style_dataframe_brl(df_alert_custo), use_container_width=True)
                            else:
                                st.success("✅ Nenhum alerta de custo detectado.")
                        
                        with col2:
                            st.markdown("#### ⚠️ Acima do Limite de Volume")
                            if not alert_vol.empty:
                                df_alert_vol = alert_vol.reset_index().rename(columns={'Nome_do_Associado':'Beneficiário',0:'Volume'})
                                st.dataframe(style_dataframe_brl(df_alert_vol, value_cols=[]), use_container_width=True)
                            else:
                                st.success("✅ Nenhum alerta de volume detectado.")
                    else:
                        st.info("ℹ️ Dados de custo ou beneficiário ausentes para análise de alertas.")
                        
                # --- TAB 4/2: Busca (RH & MEDICO) ---
                elif tab_name == "🔍 Busca":
                    st.markdown("### 🔎 Busca Individualizada de Beneficiário")
                    
                    # Usar st.selectbox para selecionar o beneficiário
                    selected_name = st.selectbox(
                        "Selecione o nome do Beneficiário para detalhamento:",
                        options=["Selecione um Beneficiário"] + nomes_possiveis,
                        index=(nomes_possiveis.index(st.session_state.selected_benef) + 1) if st.session_state.selected_benef in nomes_possiveis else 0
                    )

                    # Atualiza o estado da sessão com o nome selecionado
                    if selected_name != "Selecione um Beneficiário":
                        st.session_state.selected_benef = selected_name
                    elif st.session_state.selected_benef is not None and st.session_state.selected_benef not in nomes_possiveis:
                        st.session_state.selected_benef = None

                    selected_benef = st.session_state.selected_benef
                    
                    if selected_benef and selected_benef in nomes_possiveis:
                        st.info(f"Dados gerais de utilização para: **{selected_benef}**")
                        
                        # Filtros específicos
                        filt_util = utilizacao[utilizacao['Nome_do_Associado'] == selected_benef]
                        filt_cad = cadastro[cadastro['Nome_do_Associado'] == selected_benef]
                        
                        # Cartões de Resumo
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Custo Total Filtrado", format_brl(filt_util['Valor'].sum()))
                        with col2:
                            st.metric("Total de Atendimentos", len(filt_util))
                        with col3:
                            idade = int((pd.Timestamp.today() - filt_cad['Data_de_Nascimento'].iloc[0]).dt.days // 365) if not filt_cad.empty and 'Data_de_Nascimento' in filt_cad.columns and not filt_cad['Data_de_Nascimento'].empty and not pd.isna(filt_cad['Data_de_Nascimento'].iloc[0]) else "N/A"
                            st.metric("Idade Atual", idade)
                        with col4:
                            st.metric("Tipo", filt_util['Tipo_Beneficiario'].iloc[0] if not filt_util.empty else "N/A")

                        st.markdown("#### Histórico de Utilização Detalhada")
                        if not filt_util.empty:
                            # Seleciona colunas relevantes para visualização
                            cols_view = [col for col in ['Data_do_Atendimento', 'Descricao_do_Servico', 'Tipo_de_Servico', 'Valor'] if col in filt_util.columns]
                            
                            st.dataframe(
                                style_dataframe_brl(filt_util[cols_view].sort_values('Data_do_Atendimento', ascending=False)), 
                                use_container_width=True
                            )
                        else:
                            st.info("Nenhuma utilização encontrada no período para este beneficiário.")
                    else:
                        st.info("Por favor, selecione um beneficiário na caixa acima para visualizar os dados detalhados.")

                # --- TAB 5: Exportação (RH ONLY) ---
                elif tab_name == "📤 Exportação":
                    st.markdown("### 📥 Exportação de Dados Filtrados")

                    @st.cache_data
                    def convert_df_to_excel(df):
                        output = BytesIO()
                        # Usa xlsxwriter para melhor compatibilidade
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False, sheet_name='DadosFiltrados')
                        processed_data = output.getvalue()
                        return processed_data

                    # Dataframe de exportação
                    df_export = utilizacao_filtrada.copy()
                    
                    # Colunas amigáveis para exportação
                    friendly_cols = {col: col.replace('_', ' ').title() for col in df_export.columns}
                    df_export.rename(columns=friendly_cols, inplace=True)
                    
                    if not df_export.empty:
                        excel_data = convert_df_to_excel(df_export)
                        st.markdown(f"**Dados prontos para exportação:** {len(df_export)} linhas filtradas.")
                        st.dataframe(df_export.head(10), use_container_width=True)

                        st.download_button(
                            label="Download Dados Filtrados em Excel",
                            data=excel_data,
                            file_name="dados_saude_filtrados.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    else:
                        st.warning("⚠️ O DataFrame de utilização está vazio após a aplicação dos filtros. Nada para exportar.")
                        
                # --- TAB 1: Análise Médica (MEDICO ONLY) ---
                elif tab_name == "🏥 Análise Médica":
                    st.markdown("### 🩺 Ficha Médica Detalhada")
                    
                    selected_benef = st.session_state.selected_benef
                    
                    if not selected_benef or selected_benef not in nomes_possiveis:
                        st.warning("⚠️ Por favor, utilize a aba **🔍 Busca** para selecionar um beneficiário antes de realizar a análise médica.")
                    else:
                        st.success(f"Análise detalhada para: **{selected_benef}**")
                        
                        # Filtros específicos
                        filt_cad = cadastro[cadastro['Nome_do_Associado'] == selected_benef]
                        filt_med = medicina_trabalho[medicina_trabalho['Nome_do_Associado'] == selected_benef]
                        filt_at = atestados[atestados['Nome_do_Associado'] == selected_benef]
                        
                        if not filt_cad.empty:
                            st.markdown("#### Dados Cadastrais")
                            col1, col2, col3, col4 = st.columns(4)
                            
                            data_nasc = filt_cad['Data_de_Nascimento'].iloc[0].strftime('%d/%m/%Y') if 'Data_de_Nascimento' in filt_cad.columns and not pd.isna(filt_cad['Data_de_Nascimento'].iloc[0]) else "N/A"
                            idade = int((pd.Timestamp.today() - filt_cad['Data_de_Nascimento'].iloc[0]).dt.days // 365) if data_nasc != "N/A" else "N/A"
                            
                            with col1: st.markdown(f"**Data Nasc:** **{data_nasc}**")
                            with col2: st.markdown(f"**Idade:** **{idade}**")
                            with col3: st.markdown(f"**Sexo:** **{filt_cad[sexo_col].iloc[0] if sexo_col and not filt_cad[sexo_col].empty else 'N/A'}**")
                            with col4: st.markdown(f"**Matrícula:** **{filt_cad['Matricula'].iloc[0] if 'Matricula' in filt_cad.columns and not filt_cad['Matricula'].empty else 'N/A'}**")
                        
                        
                        st.markdown("---")
                        
                        # Atestados
                        st.markdown("#### Histórico de Atestados de Afastamento")
                        if not filt_at.empty:
                            # Selecionar colunas relevantes
                            at_cols = ['Data_do_Afastamento', 'Dias_Afastado', 'CID', 'Motivo']
                            at_cols_present = [c for c in at_cols if c in filt_at.columns]
                            
                            st.dataframe(filt_at[at_cols_present].sort_values('Data_do_Afastamento', ascending=False), use_container_width=True)
                        else:
                            st.info("Nenhum registro de atestado de afastamento encontrado.")
                            
                        # Medicina do Trabalho
                        st.markdown("#### Exames de Medicina do Trabalho")
                        if not filt_med.empty:
                            # Selecionar colunas relevantes
                            med_cols = ['Data_do_Exame', 'Tipo_de_Exame', 'Resultado']
                            med_cols_present = [c for c in med_cols if c in filt_med.columns]

                            st.dataframe(filt_med[med_cols_present].sort_values('Data_do_Exame', ascending=False), use_container_width=True)
                        else:
                            st.info("Nenhum registro de medicina do trabalho encontrado.")
                    
    else:
        st.info("👆 Por favor, carregue um arquivo Excel/XLTX com as abas 'Utilizacao' e 'Cadastro' para iniciar a análise do dashboard.")

# ---------------------------
# 10. RODAPÉ (Forçar logout)
# ---------------------------
st.sidebar.markdown("---")
if st.session_state.logged_in:
    if st.sidebar.button("Sair", type="secondary", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.selected_benef = None
        # Substituição de st.experimental_rerun() por st.rerun()
        st.rerun()
