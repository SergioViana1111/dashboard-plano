import pandas as pd
import numpy as np
from unidecode import unidecode
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go 
from io import BytesIO
import re
# NOVO: Importação para tabelas interativas (AgGrid)
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

# ---------------------------
# 0. CONFIGURAÇÃO DE PÁGINA E TEMA
# ---------------------------
st.set_page_config(
    page_title="Dashboard Saúde",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para visual Power BI
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
    [data-testid="stSidebar"] .stDateInput label,
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
# 1. FUNÇÕES DE FORMATAÇÃO
# ---------------------------
def format_brl(value):
    """Formata um float ou int para string no padrão monetário brasileiro (R$ 1.234,56)"""
    if pd.isna(value):
        return "R$ 0,00"
    # Garante que o valor é float antes de formatar
    value = float(value) 
    # Formata para string BR: ponto para milhar, vírgula para decimal
    return "R$ {:,.2f}".format(value).replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")

# FUNÇÃO: Formata o DataFrame inteiro com o padrão BR
def style_dataframe_brl(df, value_cols=['Valor']):
    """Aplica formatação monetária BR em colunas específicas de um DataFrame.
    Retorna um Styler para uso no st.dataframe."""
    
    # Criamos uma cópia do DF para aplicar o Styler
    df_styled = df.copy() 
    
    formatters = {}
    
    # 1. Colunas de Valor (R$ 1.234,56)
    for col in value_cols:
        if col in df_styled.columns:
            # Usamos a função format_brl como formatter
            formatters[col] = format_brl
    
    # 2. Colunas de Volume (1.234)
    if 'Volume' in df_styled.columns and 'Volume' not in formatters:
        # Formato de número inteiro com separador de milhar BR (ponto)
        formatters['Volume'] = lambda x: '{:,.0f}'.format(x).replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        
    if 0 in df_styled.columns and 0 not in formatters:
        formatters[0] = lambda x: '{:,.0f}'.format(x).replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")

    # Aplica o estilo.
    if formatters:
        return df_styled.style.format(formatters)
    return df_styled

# ---------------------------
# 2. AUTENTICAÇÃO
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

# garantir key para seleção persistente do beneficiário
if "selected_benef" not in st.session_state:
    st.session_state.selected_benef = None

def login():
    # Inicializa inputs no session_state
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
    
    # Simulação de st.secrets para rodar localmente se não estiver no Streamlit Cloud
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
                st.success(f"✅ Bem-vindo(a), {st.session_state.username}!")
                # Força o refresh da página para carregar o dashboard
                st.rerun()
            else:
                st.error("❌ Senha incorreta")
        else:
            st.error("❌ Usuário não encontrado")

# Chama a função de login
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
    
    st.markdown("---")
    
    # ---------------------------
    # 4. Upload do arquivo
    # ---------------------------
    uploaded_file = st.file_uploader("📁 Escolha o arquivo .xltx ou .xlsx", type=["xlsx", "xltx"])
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
        # 5. Padronização e Limpeza de Dados
        # ---------------------------
        def clean_cols(df):
            df.columns = [unidecode(col).strip().replace(' ','_').replace('-','_') for col in df.columns]
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

        # CONVERSÃO DE VALORES DE AMERICANO PARA FLOAT:
        if 'Valor' in utilizacao.columns:
            try:
                # Tenta limpar e converter se for string (Remove R$, espaços e vírgulas de milhar, deixando apenas o ponto decimal)
                if utilizacao['Valor'].dtype == 'object' or utilizacao['Valor'].dtype == np.dtype('object'):
                    # Tenta tratar o cenário 1: Padrão Americano (ponto decimal) com vírgula de milhar. Ex: '58,146.17'
                    utilizacao.loc[:, 'Valor'] = (utilizacao['Valor']
                                                  .astype(str)
                                                  .str.replace(r'[^\d\.\,]', '', regex=True) # Remove tudo que não for digito, ponto ou vírgula
                                                  .str.replace(',', '', regex=False) # Remove vírgula de milhar
                                                 )
                    # O resultado agora deve ser '58146.17' (ponto decimal). Converte para float.
                
                # Para evitar problemas de SettingWithCopyWarning
                utilizacao.loc[:, 'Valor'] = pd.to_numeric(utilizacao['Valor'], errors='coerce')
                
            except Exception as e:
                st.warning(f"⚠️ Erro ao converter a coluna 'Valor' para numérico: {e}")


        # ---------------------------
        # 6. Tipo Beneficiário
        # ---------------------------
        if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
            utilizacao['Tipo_Beneficiario'] = np.where(
                utilizacao['Nome_Titular'] == utilizacao['Nome_do_Associado'],
                'Titular', 'Dependente'
            )
        else:
            utilizacao['Tipo_Beneficiario'] = 'Desconhecido'

        # ---------------------------
        # 7. Filtros Sidebar
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
        
        # NOVO: Filtro Global de Planos
        possible_plano_cols = [col for col in utilizacao.columns if 'plano' in col.lower() and 'descricao' in col.lower()]
        plano_col = possible_plano_cols[0] if possible_plano_cols else None
        plano_opts = utilizacao[plano_col].dropna().unique() if plano_col else []
        plano_filtro = st.sidebar.multiselect("🛡️ Plano Contratado", options=plano_opts, default=plano_opts)


        # Município
        municipio_filtro = None
        if 'Municipio_do_Participante' in cadastro.columns:
            municipio_opts = cadastro['Municipio_do_Participante'].dropna().unique()
            municipio_filtro = st.sidebar.multiselect("📍 Município", options=municipio_opts, default=municipio_opts)

        # Faixa etária
        idade_col = 'Data_de_Nascimento'
        min_age, max_age = 0, 100
        if idade_col in cadastro.columns:
            # Cálculo de idade para obter o min/max real, se aplicável
            idade_real = (pd.Timestamp.today() - cadastro[idade_col]).dt.days // 365
            if not idade_real.empty:
                min_age = max(0, int(idade_real.min()))
                max_age = int(idade_real.max())
                
        # O slider usará 0-100 como range, mas os defaults serão calculados ou o padrão 18-65
        default_min = 18 if min_age < 18 else min_age
        default_max = 65 if max_age > 65 else max_age
        faixa_etaria = st.sidebar.slider("📅 Faixa Etária", min_value=0, max_value=100, value=(default_min, default_max))

        # Período
        periodo_min = utilizacao['Data_do_Atendimento'].min() if 'Data_do_Atendimento' in utilizacao.columns and not utilizacao['Data_do_Atendimento'].empty else pd.Timestamp.today()
        periodo_max = utilizacao['Data_do_Atendimento'].max() if 'Data_do_Atendimento' in utilizacao.columns and not utilizacao['Data_do_Atendimento'].empty else pd.Timestamp.today()
        # Tratamento para garantir que período_min e periodo_max sejam datas válidas
        if pd.isna(periodo_min) or periodo_min == pd.Timestamp.today():
             periodo_min = pd.Timestamp.today().normalize() - pd.DateOffset(years=1)
        if pd.isna(periodo_max) or periodo_max == pd.Timestamp.today():
            periodo_max = pd.Timestamp.today().normalize()
            
        periodo = st.sidebar.date_input("📆 Período", [periodo_min, periodo_max])
        # Garantir que o output é sempre uma lista de 2 elementos
        if not isinstance(periodo, list) or len(periodo) != 2:
            st.warning("Selecione um período válido (data de início e fim).")
            # Usa o default para evitar erro na filtragem
            periodo = [periodo_min, periodo_max]


        # ---------------------------
        # 8. Aplicar filtros
        # ---------------------------
        cadastro_filtrado = cadastro.copy()
        if idade_col in cadastro_filtrado.columns:
            idade = (pd.Timestamp.today() - cadastro_filtrado[idade_col]).dt.days // 365
            # Aplica o filtro de Faixa Etária
            cadastro_filtrado = cadastro_filtrado[(idade >= faixa_etaria[0]) & (idade <= faixa_etaria[1])]
        
        # Filtro de Sexo
        if sexo_filtro and sexo_col:
            cadastro_filtrado = cadastro_filtrado[cadastro_filtrado[sexo_col].isin(sexo_filtro)]
            
        # Filtro de Município
        if municipio_filtro is not None:
            if 'Municipio_do_Participante' in cadastro_filtrado.columns:
                cadastro_filtrado = cadastro_filtrado[cadastro_filtrado['Municipio_do_Participante'].isin(municipio_filtro)]

        utilizacao_filtrada = utilizacao.copy()
        
        # Filtro de Tipo Beneficiário
        if tipo_benef_filtro:
            utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Tipo_Beneficiario'].isin(tipo_benef_filtro)]
            
        # Filtro de Plano
        if plano_filtro and plano_col:
            utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada[plano_col].isin(plano_filtro)]

        # garantir que filtragem cruze com cadastro filtrado se houver Nome_do_Associado em ambas
        benef_col = 'Nome_do_Associado'
        if benef_col in utilizacao_filtrada.columns and benef_col in cadastro_filtrado.columns:
            # Lista de beneficiários válidos após filtros do cadastro (faixa, sexo, município)
            benef_validos = cadastro_filtrado[benef_col].dropna().unique()
            utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada[benef_col].isin(benef_validos)]
            
        # Filtro de Período
        data_col = 'Data_do_Atendimento'
        if data_col in utilizacao_filtrada.columns:
            utilizacao_filtrada = utilizacao_filtrada[
                (utilizacao_filtrada[data_col] >= pd.to_datetime(periodo[0])) &
                (utilizacao_filtrada[data_col] <= pd.to_datetime(periodo[1]))
            ]
        # REFILTRAR CADASTRO após a filtragem da utilização para garantir lista de nomes completa
        if benef_col in utilizacao_filtrada.columns and benef_col in cadastro_filtrado.columns:
             benef_utilizados = utilizacao_filtrada[benef_col].dropna().unique()
             cadastro_filtrado = cadastro_filtrado[cadastro_filtrado[benef_col].isin(benef_utilizados)]


        # ---------------------------
        # 9. Preparar lista de nomes para busca
        # ---------------------------
        nomes_from_cad = set()
        if 'Nome_do_Associado' in cadastro_filtrado.columns:
            nomes_from_cad = set(cadastro_filtrado['Nome_do_Associado'].dropna().unique())
        nomes_from_util = set()
        if 'Nome_do_Associado' in utilizacao_filtrada.columns:
            nomes_from_util = set(utilizacao_filtrada['Nome_do_Associado'].dropna().unique())

        nomes_possiveis = sorted(list(nomes_from_cad.union(nomes_from_util)))

        def normalize_name(s):
            return unidecode(str(s)).strip().upper()

        nomes_norm_map = {normalize_name(n): n for n in nomes_possiveis}
        
        # ---------------------------
        # 9.1. Função para encontrar a coluna de COD
        # ---------------------------
        def get_cod_col(df):
            if 'Nome_do_Procedimento' in df.columns:
                return 'Nome_do_Procedimento'
            elif 'Codigo_do_Procedimento' in df.columns:
                return 'Codigo_do_Procedimento'
            elif 'Codigo_do_CID' in df.columns:
                return 'Codigo_do_CID'
            return None


        # ---------------------------
        # 10. Dashboard Tabs por Role
        # ---------------------------

        # Definir abas disponíveis por cargo com emojis
        if role == "RH":
            # NOVO: Adicionado "Detalhes Interativos"
            tabs = ["📊 KPIs Gerais", "📈 Comparativo", "🚨 Alertas", "🔍 Busca", "📑 Detalhes Interativos", "📤 Exportação"]
        elif role == "MEDICO":
            tabs = ["🏥 Análise Médica", "🔍 Busca"]
        else:
            tabs = []
        
        tab_objects = st.tabs(tabs)
        
        # ---------------------------
        # 11. Implementação do Conteúdo das Tabs
        # ---------------------------

        for i, tab_name in enumerate(tabs):
            with tab_objects[i]:
                
                # --- ABA: KPIs GERAIS (RH) ---
                if tab_name == "📊 KPIs Gerais":
                    st.markdown("### 📌 Indicadores Principais")
                    
                    # Métricas em cards
                    custo_total = utilizacao_filtrada['Valor'].sum() if 'Valor' in utilizacao_filtrada.columns else 0
                    volume_total = len(utilizacao_filtrada)
                    num_beneficiarios = utilizacao_filtrada['Nome_do_Associado'].nunique() if 'Nome_do_Associado' in utilizacao_filtrada.columns else 0
                    custo_medio = custo_total / num_beneficiarios if num_beneficiarios > 0 else 0

                    
                    # PRIMEIRA LINHA: Custo Total e Atendimentos
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("💰 Custo Total", format_brl(custo_total))
                    with col2:
                        st.metric("📋 Atendimentos", f"{volume_total:,.0f}".replace(",", "."))
                    
                    # SEGUNDA LINHA: Beneficiários e Custo Médio
                    col3, col4 = st.columns(2)
                    with col3:
                        st.metric("👥 Beneficiários", f"{num_beneficiarios:,.0f}".replace(",", "."))
                    with col4:
                        st.metric("📊 Custo Médio por Beneficiário", format_brl(custo_medio))
                    
                    st.markdown("---")
                    
                    # Gráfico de evolução temporal
                    if 'Data_do_Atendimento' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        st.markdown("### 📈 Evolução de Custos por Mês")
                        # Para evitar SettingWithCopyWarning
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

                    # Top 20 beneficiários (AGORA É TOP 20)
                    col1_top, col2_top = st.columns(2)
                    
                    with col1_top:
                        if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                            st.markdown("### 💎 Top 20 por Custo")
                            custo_por_benef = utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].sum().sort_values(ascending=False)
                            df_custo = custo_por_benef.head(20).reset_index().rename(columns={'Nome_do_Associado':'Beneficiário','Valor':'Valor'})
                            df_custo.insert(0, 'Ranking', range(1, 1 + len(df_custo)))
                            st.dataframe(style_dataframe_brl(df_custo), use_container_width=True, height=400, hide_index=True)
                            
                            # Exportação do Top 20 Custo (NOVO)
                            buf_top20 = BytesIO()
                            df_custo_export = df_custo.copy()
                            # Para exportação, removemos a formatação de R$
                            df_custo_export['Valor'] = df_custo_export['Valor'].round(2)
                            df_custo_export.to_excel(buf_top20, index=False)
                            buf_top20.seek(0)
                            st.download_button(
                                label="📥 Exportar Top 20 Custo",
                                data=buf_top20,
                                file_name="top20_custo_beneficiarios.xlsx",
                                mime="application/vnd.ms-excel",
                                key="export_top20_custo"
                            )
                            
                    with col2_top:
                        if 'Nome_do_Associado' in utilizacao_filtrada.columns:
                            st.markdown("### 📊 Top 20 por Volume")
                            top20_volume = utilizacao_filtrada.groupby('Nome_do_Associado').size().sort_values(ascending=False)
                            df_volume = top20_volume.head(20).reset_index().rename(columns={'Nome_do_Associado':'Beneficiário',0:'Volume'})
                            df_volume.insert(0, 'Ranking', range(1, 1 + len(df_volume)))
                            st.dataframe(style_dataframe_brl(df_volume, value_cols=[]), use_container_width=True, height=400, hide_index=True)


                    st.markdown("---")
                    
                    # NOVO: Ranking de CODs por Município
                    st.markdown("### 🗺️ Ranking de Procedimentos/CIDs por Município")
                    
                    cod_col = get_cod_col(utilizacao_filtrada)
                    
                    if cod_col and 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        
                        # 1. Merge com Município
                        df_merge = utilizacao_filtrada.merge(
                            cadastro_filtrado[['Nome_do_Associado', 'Municipio_do_Participante']].drop_duplicates(),
                            on='Nome_do_Associado', 
                            how='left'
                        )
                        df_merge['Municipio_do_Participante'] = df_merge['Municipio_do_Participante'].fillna('Desconhecido')
                        
                        # 2. Seletor de Município
                        municipios_validos = sorted(df_merge['Municipio_do_Participante'].unique().tolist())
                        selected_municipio = st.selectbox(
                            "📍 Selecione o Município para Análise:", 
                            options=["TODOS"] + municipios_validos
                        )
                        
                        # 3. Filtragem por Município
                        if selected_municipio != "TODOS":
                            df_filtrado_mun = df_merge[df_merge['Municipio_do_Participante'] == selected_municipio]
                        else:
                            df_filtrado_mun = df_merge.copy()
                            
                        # 4. Agrupamento
                        ranking_cod = df_filtrado_mun.groupby(cod_col).agg(
                            Volume=('Valor', 'size'),
                            Custo_Total=('Valor', 'sum')
                        ).reset_index()
                        
                        # 5. Ordenação (por Volume decrescente)
                        ranking_cod = ranking_cod.sort_values(by='Volume', ascending=False)
                        
                        ranking_cod.insert(0, 'Ranking', range(1, 1 + len(ranking_cod)))
                        ranking_cod = ranking_cod.rename(columns={cod_col: 'Código/Procedimento', 'Volume': 'Volume (Freq.)', 'Custo_Total': 'Custo Total'})
                        
                        st.dataframe(
                            style_dataframe_brl(ranking_cod, value_cols=['Custo Total']), 
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Gráfico para visualização
                        if not ranking_cod.empty:
                            top10_ranking = ranking_cod.head(10).sort_values(by='Custo Total', ascending=True)
                            fig_cod = px.bar(
                                top10_ranking,
                                x='Custo Total',
                                y='Código/Procedimento',
                                orientation='h',
                                title=f'Top 10 Códigos/Procedimentos por Custo em {selected_municipio}',
                                color='Custo Total',
                                color_continuous_scale=px.colors.sequential.Plasma
                            )
                            fig_cod.update_layout(
                                plot_bgcolor='white',
                                paper_bgcolor='white',
                                yaxis={'categoryorder':'total ascending'}
                            )
                            st.plotly_chart(fig_cod, use_container_width=True)

                    else:
                        st.info(f"ℹ️ Não foi possível realizar o ranking. Colunas necessárias ({cod_col}, Nome_do_Associado, Valor) ou Município não encontradas/preenchidas.")

                # --- ABA: COMPARATIVO (RH) ---
                elif tab_name == "📈 Comparativo":
                    if plano_col and 'Valor' in utilizacao_filtrada.columns:
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
                        
                # --- ABA: ALERTAS (RH) ---
                elif tab_name == "🚨 Alertas":
                    st.markdown("### 🚨 Alertas e Inconsistências")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        # Os inputs de número (custo_lim) já esperam o formato numérico, sem formatação BR
                        custo_lim = st.number_input("💰 Limite de custo (R$)", value=5000.00, step=100.00, key=f"custo_lim_{tab_name}")
                    with col2:
                        vol_lim = st.number_input("📊 Limite de atendimentos", value=20, key=f"vol_lim_{tab_name}")

                    if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        custo_por_benef = utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].sum()
                        top10_volume = utilizacao_filtrada.groupby('Nome_do_Associado').size()
                        
                        # Filtra E ordena do maior para o menor para que o ranking 1 seja o maior valor.
                        alert_custo = custo_por_benef[custo_por_benef > custo_lim].sort_values(ascending=False) 
                        
                        # Filtra E ordena do maior para o menor para que o ranking 1 seja o maior volume.
                        alert_vol = top10_volume[top10_volume > vol_lim].sort_values(ascending=False)

                        col1_alert, col2_alert = st.columns(2)
                        
                        with col1_alert:
                            if not alert_custo.empty:
                                st.markdown("#### ⚠️ Acima do Limite de Custo")
                                df_alert_custo = alert_custo.reset_index().rename(columns={'Nome_do_Associado':'Beneficiário','Valor':'Valor'})
                                df_alert_custo.insert(0, 'Ranking', range(1, 1 + len(df_alert_custo)))
                                # USANDO A NOVA FUNÇÃO style_dataframe_brl
                                st.dataframe(style_dataframe_brl(df_alert_custo), use_container_width=True, hide_index=True)
                            else:
                                st.success("✅ Nenhum alerta de custo")

                        with col2_alert:
                            if not alert_vol.empty:
                                st.markdown("#### ⚠️ Acima do Limite de Volume")
                                df_alert_vol = alert_vol.reset_index().rename(columns={'Nome_do_Associado':'Beneficiário',0:'Volume'})
                                df_alert_vol.insert(0, 'Ranking', range(1, 1 + len(df_alert_vol)))
                                # USANDO A NOVA FUNÇÃO style_dataframe_brl (sem R$)
                                st.dataframe(style_dataframe_brl(df_alert_vol, value_cols=[]), use_container_width=True, hide_index=True)
                            else:
                                st.success("✅ Nenhum alerta de volume")


                    st.markdown("### ⚠️ Inconsistências")
                    inconsistencias = pd.DataFrame()
                    if sexo_col and 'Codigo_do_CID' in utilizacao_filtrada.columns and 'Nome_do_Associado' in utilizacao_filtrada.columns:
                        def padronizar_nome(nome): return unidecode(str(nome)).strip().upper()
                        
                        # Usar cópias para evitar SettingWithCopyWarning
                        utilizacao_filtrada_temp = utilizacao_filtrada.copy()
                        cadastro_filtrado_temp = cadastro_filtrado.copy()
                        
                        utilizacao_filtrada_temp['Nome_merge'] = utilizacao_filtrada_temp['Nome_do_Associado'].apply(padronizar_nome)
                        cadastro_filtrado_temp['Nome_merge'] = cadastro_filtrado_temp['Nome_do_Associado'].apply(padronizar_nome)
                        
                        utilizacao_merge = utilizacao_filtrada_temp.merge(
                            cadastro_filtrado_temp[['Nome_merge', sexo_col]].drop_duplicates(), on='Nome_merge', how='left'
                        )
                        
                        # Tratamento da coluna de sexo após o merge
                        if sexo_col not in utilizacao_merge.columns:
                            utilizacao_merge[sexo_col] = 'Desconhecido'
                        else:
                            utilizacao_merge[sexo_col] = utilizacao_merge[sexo_col].fillna('Desconhecido')
                        
                        # Inconsistência: CID de Parto (O80) em homens (Sexo='M')
                        parto_masc = utilizacao_merge[(utilizacao_merge['Codigo_do_CID']=='O80') & (utilizacao_merge[sexo_col]=='M')]
                        if not parto_masc.empty:
                            inconsistencias = pd.concat([inconsistencias, parto_masc.drop(columns='Nome_merge')])
                            
                    if not inconsistencias.empty:
                        inconsistencias = inconsistencias.reset_index(drop=True)
                        inconsistencias.insert(0, 'Linha', range(1, 1 + len(inconsistencias)))
                        # Aplicar formatação para a coluna 'Valor' nas inconsistências
                        st.dataframe(style_dataframe_brl(inconsistencias), use_container_width=True, hide_index=True)
                    else:
                        st.success("✅ Nenhuma inconsistência lógica (aparente) encontrada.")

                # --- ABA: ANÁLISE MÉDICA (MEDICO) ---
                elif tab_name == "🏥 Análise Médica":
                    st.markdown("### 🧬 Beneficiários com Condições Crônicas")
                    cids_cronicos = ['E11','I10','J45'] # Diabetes, Hipertensão, Asma
                    if 'Codigo_do_CID' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        utilizacao_filtrada_temp = utilizacao_filtrada.copy()
                        # Verifica se o CID começa com um dos códigos crônicos
                        utilizacao_filtrada_temp.loc[:, 'Cronico'] = utilizacao_filtrada_temp['Codigo_do_CID'].astype(str).str.startswith(tuple(cids_cronicos))
                        beneficiarios_cronicos = utilizacao_filtrada_temp[utilizacao_filtrada_temp['Cronico']].groupby('Nome_do_Associado')['Valor'].sum()
                        df_cronicos = beneficiarios_cronicos.reset_index().rename(columns={'Nome_do_Associado':'Beneficiário','Valor':'Valor'})
                        df_cronicos.insert(0, 'Ranking', range(1, 1 + len(df_cronicos)))
                        st.dataframe(style_dataframe_brl(df_cronicos), use_container_width=True,hide_index=True)
                    else:
                        st.info("ℹ️ Colunas de CID ou Valor não encontradas para esta análise.")

                    st.markdown("### 💊 Top 10 Procedimentos por Custo")
                    if 'Nome_do_Procedimento' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        top_proc = utilizacao_filtrada.groupby('Nome_do_Procedimento')['Valor'].sum().sort_values(ascending=False).head(10)
                        df_top_proc = top_proc.reset_index().rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Valor'})
                        df_top_proc.insert(0, 'Ranking', range(1, 1 + len(df_top_proc)))
                        st.dataframe(style_dataframe_brl(df_top_proc), use_container_width=True,hide_index=True)
                    else:
                        st.info("ℹ️ Colunas de Procedimento/Valor não encontradas para esta análise.")

                # --- ABA: BUSCA (RH/MEDICO) ---
                elif tab_name == "🔍 Busca":
                    st.markdown("### 🔎 Busca por Beneficiário")
                    
                    # caixa de busca (tempo real)
                    search_input = st.text_input("Digite nome do beneficiário (busca em tempo real)", key="busca_input")

                    # Calcula matches conforme input
                    search_query = search_input.strip()
                    matches = []
                    if search_query:
                        q_norm = normalize_name(search_query)
                        # Substring match on normalized names
                        matches = [orig for norm, orig in nomes_norm_map.items() if q_norm in norm]
                        matches = sorted(matches)
                    else:
                        # quando vazio, sugerir top 20 por volume (se disponível) ou top 20 nomes
                        if 'Nome_do_Associado' in utilizacao_filtrada.columns:
                            vol = utilizacao_filtrada.groupby('Nome_do_Associado').size().sort_values(ascending=False)
                            suggestions = vol.head(20).index.tolist()
                            matches = [s for s in suggestions if s in nomes_possiveis]
                        else:
                            matches = nomes_possiveis[:20]

                    chosen = None
                    if matches:
                        # NEW: 'select_benef' to keep state on refresh
                        chosen = st.selectbox("Resultados da busca — selecione o beneficiário", options=[""] + matches, index=0, key="busca_selectbox")
                        if chosen == "":
                            st.session_state.selected_benef = None
                        else:
                            st.session_state.selected_benef = chosen
                    else:
                        st.write("Nenhum resultado encontrado. Tente refinar os filtros.")

                    # --- INÍCIO: Seção Detalhada ---
                    selected_benef = st.session_state.selected_benef 
                    if selected_benef:
                        st.markdown(f"## 👤 Detalhes do Beneficiário: **{selected_benef}**")

                        # Preparar dados do beneficiário
                        util_b = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'] == selected_benef].copy()
                        cad_b = cadastro_filtrado[cadastro_filtrado['Nome_do_Associado'] == selected_benef].copy()

                        # Métricas rápidas
                        col_metrica_1, col_metrica_2, col_metrica_3 = st.columns(3)
                        
                        if 'Nome_do_Associado' in utilizacao_filtrada.columns:
                            custo_total_b = util_b['Valor'].sum() if 'Valor' in util_b.columns else 0
                            volume_b = len(util_b)
                            custo_medio_b = custo_total_b / volume_b if volume_b > 0 else 0
                            
                            with col_metrica_1:
                                st.metric("💰 Custo Total (filtros)", format_brl(custo_total_b)) 
                            with col_metrica_2:
                                st.metric("📋 Volume (atendimentos)", f"{volume_b:,.0f}".replace(",", "."))
                            with col_metrica_3:
                                st.metric("📊 Custo Médio por Atendimento", format_brl(custo_medio_b))

                        # Expander com detalhes
                        with st.expander(f"🔍 Dados detalhados — {selected_benef}", expanded=True):
                            
                            st.markdown("### 📝 Informações Cadastrais")
                            if not cad_b.empty:
                                cad_b_display = cad_b.reset_index(drop=True)
                                cad_b_display.insert(0, 'ID', range(1, 1 + len(cad_b_display)))
                                st.dataframe(cad_b_display, use_container_width=True,hide_index=True)
                            else:
                                st.info("ℹ️ Informações cadastrais não encontradas nos filtros aplicados.")

                            st.markdown("### 📋 Utilização do Plano (Atendimentos)")
                            if not util_b.empty:
                                util_b_display = util_b.reset_index(drop=True)
                                util_b_display.insert(0, 'ID_Registro', range(1, 1 + len(util_b_display)))
                                # APLICAR FORMAT_BRL PARA A COLUNA 'Valor' NO DATAFRAME VISUAL
                                st.dataframe(style_dataframe_brl(util_b_display), use_container_width=True,hide_index=True)
                            else:
                                st.info("ℹ️ Nenhum registro de utilização encontrado para os filtros aplicados.")

                            # Histórico de custos e procedimentos
                            st.markdown("### 📈 Histórico de Custos")
                            if 'Valor' in util_b.columns and 'Data_do_Atendimento' in util_b.columns and not util_b.empty:
                                # evolução do beneficiário
                                util_b.loc[:, 'Mes_Ano'] = util_b['Data_do_Atendimento'].dt.to_period('M')
                                evol_b = util_b.groupby('Mes_Ano')['Valor'].sum().reset_index()
                                evol_b['Mes_Ano'] = evol_b['Mes_Ano'].astype(str)
                                
                                fig_b = go.Figure()
                                fig_b.add_trace(go.Scatter(
                                    x=evol_b['Mes_Ano'],
                                    y=evol_b['Valor'],
                                    mode='lines+markers',
                                    name='Custo',
                                    line=dict(color='#11998e', width=3),
                                    marker=dict(size=8, color='#38ef7d'),
                                    fill='tozeroy',
                                    fillcolor='rgba(17, 153, 142, 0.1)'
                                ))

                                fig_b.update_layout(
                                    plot_bgcolor='white',
                                    paper_bgcolor='white',
                                    xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
                                    yaxis=dict(showgrid=True, gridcolor='#f0f0f0', tickprefix="R$ ", tickformat=",.2f"),
                                    hovermode='x unified',
                                    height=400
                                )
                                st.plotly_chart(fig_b, use_container_width=True)
                            else:
                                st.info("ℹ️ Dados de data e valor insuficientes para gráfico de evolução.")


                            col_proc, col_cid = st.columns(2)

                            with col_proc:
                                st.markdown("### 💉 Principais Procedimentos")
                                if 'Nome_do_Procedimento' in util_b.columns and 'Valor' in util_b.columns:
                                    top_proc_b = util_b.groupby('Nome_do_Procedimento')['Valor'].sum().sort_values(ascending=False).head(10)
                                    df_top_proc = top_proc_b.reset_index().rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Valor'})
                                    df_top_proc.insert(0, 'Ranking', range(1, 1 + len(df_top_proc)))
                                    # USANDO A NOVA FUNÇÃO style_dataframe_brl
                                    st.dataframe(style_dataframe_brl(df_top_proc), use_container_width=True,hide_index=True)
                                else:
                                    st.info("ℹ️ Colunas de procedimento ou valor não encontradas.")
                            
                            with col_cid:
                                # CIDs associados
                                st.markdown("### 🩺 CIDs Associados")
                                if 'Codigo_do_CID' in util_b.columns:
                                    cids = util_b['Codigo_do_CID'].dropna().unique().tolist()
                                    if len(cids) > 0:
                                        st.code(", ".join(map(str, cids)))
                                    else:
                                        st.info("ℹ️ Nenhum CID associado encontrado.")
                                else:
                                    st.info("ℹ️ Coluna 'Codigo_do_CID' não encontrada.")

                            
                            # Exportar relatório individual em Excel
                            st.markdown("---")
                            st.markdown("### 📥 Exportar Relatório Individual")
                            buf_ind = BytesIO()
                            with pd.ExcelWriter(buf_ind, engine='xlsxwriter') as writer:
                                if not util_b.empty:
                                    # remove a coluna de Mes_Ano temporária para exportação
                                    util_b_export = util_b.drop(columns=['Mes_Ano', 'Tipo_Beneficiario'], errors='ignore')
                                    # Garantir o valor numérico para exportação
                                    if 'Valor' in util_b_export.columns:
                                        util_b_export['Valor'] = pd.to_numeric(util_b_export['Valor'], errors='coerce')
                                    util_b_export.to_excel(writer, sheet_name='Utilizacao_Individual', index=False)
                                if not cad_b.empty:
                                    # Certifique-se de usar a versão original do cad_b sem a coluna ID temporária para exportação
                                    cad_b.drop(columns=['ID'], errors='ignore').to_excel(writer, sheet_name='Cadastro_Individual', index=False)
                                if not medicina_trabalho.empty:
                                    # Filtragem de medicina do trabalho para o beneficiário
                                    med_b = medicina_trabalho[medicina_trabalho.get('Nome_do_Associado', pd.Series()).fillna('') == selected_benef]
                                    if not med_b.empty:
                                        med_b.to_excel(writer, sheet_name='Medicina_do_Trabalho_Ind', index=False)
                                if not atestados.empty:
                                    # Filtragem de atestados para o beneficiário
                                    at_b = atestados[atestados.get('Nome_do_Associado', pd.Series()).fillna('') == selected_benef]
                                    if not at_b.empty:
                                        at_b.to_excel(writer, sheet_name='Atestados_Ind', index=False)
                            buf_ind.seek(0)
                            st.download_button(
                                label="📥 Baixar Relatório Individual (.xlsx)",
                                data=buf_ind,
                                file_name=f"relatorio_beneficiario_{normalize_name(selected_benef)[:50]}.xlsx",
                                mime="application/vnd.ms-excel",
                                use_container_width=True
                            )
                    # --- FIM: Seção Detalhada ---
                
                # --- NOVO ABA: DETALHES INTERATIVOS (RH) ---
                elif tab_name == "📑 Detalhes Interativos":
                    st.markdown("### 🗂️ Dados de Utilização Interativos")
                    st.write("Use a tabela interativa para filtrar, ordenar e selecionar registros de utilização. Exporte o resultado exato que você vê na tabela (incluindo filtros e ordenação aplicados).")

                    if utilizacao_filtrada.empty:
                        st.info("ℹ️ Nenhum dado de utilização encontrado com os filtros aplicados.")
                    else:
                        # Prepara o DataFrame para o AgGrid
                        df_ag = utilizacao_filtrada.copy()
                        df_ag.index = df_ag.index + 1 # Inicia o index em 1
                        df_ag = df_ag.reset_index().rename(columns={'index': 'ID_Registro'})

                        # Configuração do AgGrid
                        gb = GridOptionsBuilder.from_dataframe(df_ag)
                        
                        # Formatação monetária e de data para AgGrid (exemplo)
                        if 'Valor' in df_ag.columns:
                            gb.configure_column("Valor", type=["numericColumn", "customNumericFormat"], 
                                                valueFormatter="`'R$ ' + data.Valor.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})`",
                                                aggFunc='sum')
                        if 'Data_do_Atendimento' in df_ag.columns:
                            gb.configure_column("Data_do_Atendimento", type=["dateColumnFilter", "customDateTimeFormat"], 
                                                custom_format_string='dd/MM/yyyy',
                                                cellRenderer='agDateStringCellRenderer')

                        gb.configure_default_column(editable=False, filter=True, sortable=True, resizable=True)
                        gb.configure_grid_options(domLayout='normal')
                        
                        # Opções de exportação
                        gb.configure_export_params(data_key="data", file_name="export_utilizacao_aggrid", 
                                                   column_separator=";", suppress_quotes=True)
                        
                        # Configura a barra de status com agregações
                        gb.configure_grid_options(
                            enableRangeSelection=True,
                            rowSelection='multiple',
                            suppressRowClickSelection=True,
                            groupSelectsChildren=True,
                            groupSelectsFiltered=True,
                            showOpenedGroup=True,
                            enableCellTextSelection=True,
                            ensureDomOrder=True
                        )

                        gridOptions = gb.build()

                        # Exibe a tabela interativa
                        grid_response = AgGrid(
                            df_ag,
                            gridOptions=gridOptions,
                            data_return_mode=DataReturnMode.AS_INPUT,
                            update_mode=GridUpdateMode.MODEL_CHANGED,
                            fit_columns_on_grid_load=False,
                            allow_unsafe_jscode=True, # Set it to True to allow jsfunction to be injected
                            enable_enterprise_modules=False,
                            height=400,
                            width='100%',
                            reload_data=True
                        )
                        
                        # Botão de Exportação Excel (usa a funcionalidade nativa do AgGrid)
                        st.markdown(
                            """
                            <script>
                            function download_data() {
                                const gridApi = Streamlit.getGridApi('aggrid'); 
                                if (gridApi) {
                                    gridApi.exportDataAsExcel();
                                }
                            }
                            </script>
                            <button onclick="download_data()" style='
                                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                                color: white;
                                border: none;
                                border-radius: 8px;
                                padding: 0.75rem 2rem;
                                font-weight: 600;
                                transition: all 0.3s ease;
                                cursor: pointer;
                                display: block;
                                width: 100%;
                                margin-top: 1rem;
                            '>📥 Baixar Dados Visualizados (Excel)</button>
                            """,
                            unsafe_allow_html=True
                        )


                # --- ABA: EXPORTAÇÃO (RH) ---
                elif tab_name == "📤 Exportação":
                    st.markdown("### 📥 Exportar Relatório Completo")
                    st.write("Baixe todas as abas do arquivo processado, respeitando os filtros de `Período`, `Sexo`, `Município`, `Faixa Etária`, `Tipo de Beneficiário` e `Plano` aplicados.")
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        # Para exportar, é melhor que os dados voltem ao formato numérico puro
                        # Remove a coluna temporária 'Tipo_Beneficiario' se for exportar a Utilizacao completa
                        utilizacao_filtrada_export = utilizacao_filtrada.drop(columns=['Tipo_Beneficiario'], errors='ignore')
                        
                        # Garantir o valor numérico para exportação
                        if 'Valor' in utilizacao_filtrada_export.columns:
                            utilizacao_filtrada_export['Valor'] = pd.to_numeric(utilizacao_filtrada_export['Valor'], errors='coerce')
                            
                        utilizacao_filtrada_export.to_excel(writer, sheet_name='Utilizacao_Filtrada', index=False)
                        cadastro_filtrado.to_excel(writer, sheet_name='Cadastro_Filtrado', index=False)
                        
                        # A exportação do Medicina do Trabalho e Atestados é filtrada pelo Cadastro Filtrado
                        med_export = medicina_trabalho.copy()
                        if 'Nome_do_Associado' in med_export.columns and 'Nome_do_Associado' in cadastro_filtrado.columns:
                            med_export = med_export[med_export['Nome_do_Associado'].isin(cadastro_filtrado['Nome_do_Associado'])]

                        at_export = atestados.copy()
                        if 'Nome_do_Associado' in at_export.columns and 'Nome_do_Associado' in cadastro_filtrado.columns:
                            at_export = at_export[at_export['Nome_do_Associado'].isin(cadastro_filtrado['Nome_do_Associado'])]
                            
                        if not med_export.empty:
                            med_export.to_excel(writer, sheet_name='Medicina_do_Trabalho_Filtrada', index=False)
                        if not at_export.empty:
                            at_export.to_excel(writer, sheet_name='Atestados_Filtrados', index=False)
                            
                    buffer.seek(0)
                    st.download_button(
                        "📥 Baixar Relatório Filtrado (.xlsx)", 
                        buffer, 
                        "dashboard_plano_saude_filtrado.xlsx", 
                        "application/vnd.ms-excel", 
                        use_container_width=True
                    )
                    st.success("✅ Processamento de dados concluído. Utilize as abas.")
