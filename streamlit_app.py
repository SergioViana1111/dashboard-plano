import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
import unicodedata
from datetime import datetime

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Dashboard Analítico de Plano de Saúde",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FUNÇÕES HELPERS ---

@st.cache_data
def normalize_name(name):
    """Remove acentos e minúsculas para facilitar a busca."""
    if pd.isna(name):
        return ""
    name = str(name).lower()
    return ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')

def format_brl(value):
    """Formata um valor numérico para o padrão monetário BRL."""
    if pd.isna(value):
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def calculate_age(birth_date):
    """Calcula a idade a partir da data de nascimento."""
    if pd.isna(birth_date):
        return None
    today = datetime.now()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def style_dataframe_brl(df_input, currency_cols=['Valor', 'Custo Total', 'Custo Médio']):
    """
    Aplica formatação BRL em colunas de moeda e garante que o índice comece em 1.
    Usa st.dataframe para interatividade e formatação simplificada.
    """
    df = df_input.copy()
    
    # Garantir índice 1-based para exibição
    df.index = np.arange(1, len(df) + 1)
    
    # Aplicar formatação BRL
    styled_df = df.style.format({col: 'R$ {:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.') for col in currency_cols if col in df.columns})
    
    return styled_df

# --- GERAÇÃO DE DADOS MOCK (SIMULAÇÃO DE CARREGAMENTO) ---

@st.cache_data
def load_mock_data():
    """Gera DataFrames de exemplo para simular o carregamento de dados."""
    
    # 1. Dados de Cadastro (Beneficiários)
    n = 1000
    nomes = [f"Beneficiario {i:04d}" for i in range(n)]
    datas_nasc = pd.to_datetime(np.random.randint(datetime(1950, 1, 1).timestamp(), datetime(2005, 12, 31).timestamp(), n), unit='s').date
    sexos = np.random.choice(['M', 'F'], n, p=[0.55, 0.45])
    municipios = np.random.choice(['São Paulo', 'Rio de Janeiro', 'Belo Horizonte', 'Campinas', 'Porto Alegre'], n, p=[0.4, 0.2, 0.15, 0.15, 0.1])
    tipos_beneficiario = np.random.choice(['Titular', 'Dependente', 'PAD'], n, p=[0.6, 0.3, 0.1])
    
    df_cadastro = pd.DataFrame({
        'Nome_do_Associado': nomes,
        'Data_Nascimento': datas_nasc,
        'Sexo': sexos,
        'Município': municipios,
        'Tipo_Beneficiario': tipos_beneficiario,
    })
    df_cadastro.drop_duplicates(subset=['Nome_do_Associado'], inplace=True)
    df_cadastro['Idade'] = df_cadastro['Data_Nascimento'].apply(calculate_age)
    
    # 2. Dados de Utilização (Atendimentos)
    m = 10000
    benef_util = np.random.choice(df_cadastro['Nome_do_Associado'], m)
    datas_atendimento = pd.to_datetime(np.random.randint(datetime(2023, 1, 1).timestamp(), datetime(2024, 9, 30).timestamp(), m), unit='s')
    valores = np.random.lognormal(mean=7, sigma=1.5, size=m) * 10 
    cids = np.random.choice(['E11.9', 'I10', 'J45.9', 'M54.5', 'R51', 'Z00.0', 'K21.9', 'H52.1'], m, p=[0.1, 0.08, 0.07, 0.15, 0.2, 0.1, 0.1, 0.2])
    procedimentos = np.random.choice(['Consulta Clínica', 'Exames Laboratoriais', 'Tomografia', 'Internação Geral', 'Fisioterapia', 'Cirurgia Pequena'], m, p=[0.4, 0.3, 0.1, 0.05, 0.1, 0.05])

    df_utilizacao = pd.DataFrame({
        'Data_do_Atendimento': datas_atendimento,
        'Nome_do_Associado': benef_util,
        'Nome_do_Procedimento': procedimentos,
        'Codigo_do_CID': cids,
        'Valor': valores,
    })
    
    # 3. Medicina do Trabalho e Atestados (Para exportação e detalhe)
    df_med_trab = df_utilizacao[['Nome_do_Associado']].drop_duplicates().sample(frac=0.3)
    df_med_trab['Data'] = pd.to_datetime(np.random.randint(datetime(2024, 1, 1).timestamp(), datetime(2024, 9, 30).timestamp(), len(df_med_trab)), unit='s').date
    df_med_trab['Tipo_Exame'] = np.random.choice(['Admissional', 'Periódico', 'Demissional'], len(df_med_trab))
    
    df_atestados = df_utilizacao[['Nome_do_Associado']].drop_duplicates().sample(frac=0.1)
    df_atestados['Data_Inicio'] = pd.to_datetime(np.random.randint(datetime(2024, 1, 1).timestamp(), datetime(2024, 9, 30).timestamp(), len(df_atestados)), unit='s').date
    df_atestados['Dias_Afastamento'] = np.random.randint(1, 15, len(df_atestados))
    df_atestados['Codigo_do_CID'] = np.random.choice(['M54.5', 'R51', 'J45.9', 'Z00.0'], len(df_atestados))


    # Merge para adicionar informações de idade/sexo na utilização (muito útil para filtros)
    df_utilizacao = pd.merge(df_utilizacao, df_cadastro[['Nome_do_Associado', 'Idade', 'Sexo', 'Tipo_Beneficiario']], on='Nome_do_Associado', how='left')

    return df_utilizacao, df_cadastro, df_med_trab, df_atestados

# Carregar dados
df_utilizacao, df_cadastro, medicina_trabalho, atestados = load_mock_data()

# --- SIDEBAR E FILTROS ---

st.sidebar.title("🛠️ Filtros Analíticos")

# 1. Filtro de Período
min_date = df_utilizacao['Data_do_Atendimento'].min().date()
max_date = df_utilizacao['Data_do_Atendimento'].max().date()
data_range = st.sidebar.date_input(
    "📅 Período de Atendimento",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(data_range) == 2:
    start_date = datetime.combine(data_range[0], datetime.min.time())
    end_date = datetime.combine(data_range[1], datetime.max.time())
    utilizacao_filtrada = df_utilizacao[
        (df_utilizacao['Data_do_Atendimento'] >= start_date) & 
        (df_utilizacao['Data_do_Atendimento'] <= end_date)
    ].copy()
else:
    utilizacao_filtrada = df_utilizacao.copy()

# 2. Filtros Categóricos
st.sidebar.markdown("---")
# Faixa Etária (Editável, Novo Requisito)
min_idade_data = utilizacao_filtrada['Idade'].min()
max_idade_data = utilizacao_filtrada['Idade'].max()
faixa_etaria = st.sidebar.slider(
    "👶 Faixa Etária (Anos)",
    min_value=int(min_idade_data) if not pd.isna(min_idade_data) else 0,
    max_value=int(max_idade_data) if not pd.isna(max_idade_data) else 100,
    value=(0, 100) # Inicia em 0 a 100 conforme solicitado
)
utilizacao_filtrada = utilizacao_filtrada[
    (utilizacao_filtrada['Idade'] >= faixa_etaria[0]) & 
    (utilizacao_filtrada['Idade'] <= faixa_etaria[1])
].copy()


# Sexo
sexo_options = utilizacao_filtrada['Sexo'].dropna().unique().tolist()
sexo_selecionado = st.sidebar.multiselect("🚻 Sexo", options=sexo_options, default=sexo_options)
utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Sexo'].isin(sexo_selecionado)].copy()


# Município
municipio_options = utilizacao_filtrada['Município'].dropna().unique().tolist()
municipio_selecionado = st.sidebar.multiselect("🏙️ Município", options=municipio_options, default=municipio_options)
utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Município'].isin(municipio_selecionado)].copy()

# Tipo de Beneficiário (Novo Requisito)
tipo_options = utilizacao_filtrada['Tipo_Beneficiario'].dropna().unique().tolist()
tipo_selecionado = st.sidebar.multiselect("👨‍👩‍👧 Tipo de Beneficiário", options=tipo_options, default=tipo_options, help="Titular, Dependente, ou PAD (Programa de Atenção a Doentes Crônicos/Especiais)")
utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Tipo_Beneficiario'].isin(tipo_selecionado)].copy()


# Aplica os filtros de cadastro
nomes_filtrados = utilizacao_filtrada['Nome_do_Associado'].unique().tolist()
cadastro_filtrado = df_cadastro[df_cadastro['Nome_do_Associado'].isin(nomes_filtrados)].copy()
nomes_possiveis = cadastro_filtrado['Nome_do_Associado'].unique().tolist()
nomes_norm_map = {normalize_name(nome): nome for nome in nomes_possiveis}


st.title("🛡️ Análise de Uso de Plano de Saúde")
st.markdown(f"**Base de Dados:** {min_date.strftime('%d/%m/%Y')} até {max_date.strftime('%d/%m/%Y')}")


# --- DASHBOARD PRINCIPAL ---

if utilizacao_filtrada.empty:
    st.warning("⚠️ Nenhum dado encontrado com os filtros aplicados. Tente ajustar a seleção.")
    
else:
    # Métricas Globais (Topo)
    total_custo = utilizacao_filtrada['Valor'].sum()
    total_volume = len(utilizacao_filtrada)
    total_benef = utilizacao_filtrada['Nome_do_Associado'].nunique()
    custo_medio_benef = total_custo / total_benef if total_benef > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Custo Total", format_brl(total_custo))
    with col2:
        st.metric("📋 Volume Atendimentos", f"{total_volume:,.0f}".replace(",", "."))
    with col3:
        st.metric("👥 Beneficiários Únicos", f"{total_benef:,.0f}".replace(",", "."))
    with col4:
        st.metric("📊 Custo Médio p/ Beneficiário", format_brl(custo_medio_benef))

    st.markdown("---")

    # Inicializar estado para a busca detalhada
    if 'selected_benef' not in st.session_state:
        st.session_state.selected_benef = None
    if 'selected_cid' not in st.session_state:
        st.session_state.selected_cid = None
    
    # Resetar selected_benef se o filtro de nome na barra lateral não for usado
    # Isso garante que a seleção na tabela Top 20 prevaleça se a Busca não for ativada
    if 'busca_selectbox' not in st.session_state or st.session_state.busca_selectbox == "":
        pass # Não resetar aqui, a tabela Top 20 que irá definir.

    
    tab_names = ["🏠 Dashboard Resumo", "🏥 Análise Médica", "🔍 Busca", "📤 Exportação"]
    tabs = st.tabs(tab_names)

    for tab_name, tab in zip(tab_names, tabs):
        with tab:

            # --- ABA: DASHBOARD RESUMO ---
            if tab_name == "🏠 Dashboard Resumo":
                
                # Gráfico de Evolução de Custo ao longo do tempo
                st.markdown("### 📈 Evolução Mensal de Custos")
                utilizacao_filtrada.loc[:, 'Mes_Ano'] = utilizacao_filtrada['Data_do_Atendimento'].dt.to_period('M')
                evolucao = utilizacao_filtrada.groupby('Mes_Ano')['Valor'].sum().reset_index()
                evolucao['Mes_Ano'] = evolucao['Mes_Ano'].astype(str)

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=evolucao['Mes_Ano'], 
                    y=evolucao['Valor'], 
                    name='Custo Total',
                    marker_color='#11998e'
                ))

                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    xaxis=dict(showgrid=True, gridcolor='#f0f0f0', title='Mês/Ano'),
                    yaxis=dict(showgrid=True, gridcolor='#f0f0f0', tickprefix="R$ ", tickformat=",.0f", title='Custo (R$)'),
                    hovermode='x unified',
                    height=450,
                    title_x=0.5
                )
                st.plotly_chart(fig, use_container_width=True)

                
                col_demo, col_tipo = st.columns(2)

                # Análise por Demografia (Idade)
                with col_demo:
                    st.markdown("### 🧬 Distribuição de Custo por Faixa Etária")
                    bins = [0, 18, 25, 35, 45, 55, 65, 100]
                    labels = ['0-17', '18-24', '25-34', '35-44', '45-54', '55-64', '65+']
                    utilizacao_filtrada.loc[:, 'Faixa_Etaria_Agrupada'] = pd.cut(utilizacao_filtrada['Idade'], bins=bins, labels=labels, right=False)
                    custo_por_idade = utilizacao_filtrada.groupby('Faixa_Etaria_Agrupada')['Valor'].sum().reset_index()
                    
                    fig_idade = go.Figure(data=[go.Pie(
                        labels=custo_por_idade['Faixa_Etaria_Agrupada'], 
                        values=custo_por_idade['Valor'], 
                        hole=.3,
                        hovertemplate="Faixa Etária: %{label}<br>Custo: %{value:$,.0f}<br>Percentual: %{percent}<extra></extra>",
                        marker=dict(colors=go.colors.sequential.Teal)
                    )])
                    fig_idade.update_layout(height=400, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_idade, use_container_width=True)


                # Análise por Tipo de Beneficiário
                with col_tipo:
                    st.markdown("### 👨‍👩‍👧 Custo por Tipo de Beneficiário")
                    custo_por_tipo = utilizacao_filtrada.groupby('Tipo_Beneficiario')['Valor'].sum().sort_values(ascending=False).reset_index()

                    fig_tipo = go.Figure(data=[go.Bar(
                        x=custo_por_tipo['Tipo_Beneficiario'], 
                        y=custo_por_tipo['Valor'], 
                        marker_color='#38ef7d',
                        hovertemplate="Tipo: %{x}<br>Custo: %{y:$,.0f}<extra></extra>",
                    )])
                    fig_tipo.update_layout(
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        xaxis=dict(title=None),
                        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', tickprefix="R$ ", tickformat=",.0f"),
                        height=400,
                        margin=dict(t=10, b=10)
                    )
                    st.plotly_chart(fig_tipo, use_container_width=True)


            # --- ABA: ANÁLISE MÉDICA (MEDICO) ---
            elif tab_name == "🏥 Análise Médica":
                
                # --- NOVAS IMPLEMENTAÇÕES ---

                # Explicação das Condições Crônicas (Requisito: Como elegeu?)
                st.markdown("### 🧬 Beneficiários com Condições Crônicas")
                st.info("""
                    **Critério de Elegibilidade:** Um beneficiário é considerado com 'Condição Crônica' se o **Código do CID** em qualquer um de seus atendimentos iniciar com um dos códigos de raiz definidos.
                    * **Códigos Atualmente Monitorados:** * **E11:** Diabetes Mellitus Não-Insulino-Dependente (Tipo 2)
                        * **I10:** Hipertensão Essencial (Primária)
                        * **J45:** Asma
                    A análise abaixo soma o custo total de **todos os atendimentos** (crônicos ou não) dos beneficiários que tiveram pelo menos um atendimento associado a estes CIDs de raiz.
                """)
                
                # Análise de Condições Crônicas
                cids_cronicos = ['E11','I10','J45'] 
                if 'Codigo_do_CID' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                    utilizacao_filtrada_temp = utilizacao_filtrada.copy()
                    utilizacao_filtrada_temp.loc[:, 'Cronico'] = utilizacao_filtrada_temp['Codigo_do_CID'].astype(str).str.startswith(tuple(cids_cronicos), na=False)
                    
                    # Nomes dos beneficiários que tiveram CIDs crônicos
                    beneficiarios_com_cronico = utilizacao_filtrada_temp[utilizacao_filtrada_temp['Cronico']]['Nome_do_Associado'].unique()
                    
                    # Filtrar a utilização para incluir apenas esses beneficiários (cuidado com o índice)
                    util_cronicos_full = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'].isin(beneficiarios_com_cronico)]
                    
                    beneficiarios_cronicos = util_cronicos_full.groupby('Nome_do_Associado')['Valor'].sum().sort_values(ascending=False)
                    
                    df_cronicos = beneficiarios_cronicos.reset_index().rename(columns={'Nome_do_Associado':'Beneficiário','Valor':'Custo Total'})
                    
                    st.dataframe(style_dataframe_brl(df_cronicos[['Beneficiário', 'Custo Total']]), use_container_width=True)
                else:
                    st.info("ℹ️ Colunas de CID ou Valor não encontradas para esta análise.")

                # --- TOP 20 MAIORES UTILIZADORES POR CUSTO (Novo Requisito e Interativo) ---
                st.markdown("---")
                st.markdown("### 💸 Top 20 Beneficiários por Custo (Clique na linha para ver detalhes)")
                
                if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                    top_users = utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].agg(
                        Custo_Total='sum',
                        Volume_Atendimentos='size',
                    ).sort_values(by='Custo_Total', ascending=False).head(20).reset_index()
                    
                    top_users['Custo Médio'] = top_users['Custo_Total'] / top_users['Volume_Atendimentos']
                    
                    # Cria um DataFrame para exibição com index 1-based e BRL formatado
                    df_top_users_display = style_dataframe_brl(top_users.rename(columns={'Nome_do_Associado': 'Beneficiário'}), currency_cols=['Custo Total', 'Custo Médio'])
                    
                    # Usando st.dataframe para interatividade de seleção
                    # O ID do beneficiário é necessário para buscar os detalhes
                    st.markdown("Selecione um beneficiário na tabela para abrir o **Detalhe** na aba 🔍 Busca.")
                    
                    # Uso de st.data_editor para permitir a seleção de linhas (Requisito de Interatividade)
                    selected_data = st.data_editor(
                        df_top_users_display.data, 
                        key="top_users_table", 
                        use_container_width=True,
                        hide_index=False,
                        column_config={"Custo Total": st.column_config.Progress(format="R$ %f", min_value=0, max_value=top_users['Custo_Total'].max())}
                    )
                    
                    # Lógica para capturar o beneficiário selecionado na tabela
                    if selected_data:
                        # O índice retornado é o 0-based, mas a coluna 'Beneficiário' está presente
                        selected_name = selected_data['Beneficiário'][selected_data.index[0] - 1]
                        st.session_state.selected_benef = selected_name
                        st.success(f"Beneficiário **{selected_name}** selecionado! Vá para a aba 🔍 Busca.")
                    
                    # Lógica para evitar que a seleção da tabela conflite com a busca manual se não houver clique
                    if not selected_data and st.session_state.get('selected_benef_from_table'):
                         st.session_state.selected_benef = st.session_state.selected_benef_from_table


                else:
                    st.info("ℹ️ Colunas de Nome ou Valor não encontradas para esta análise.")
                
                # --- TOP 10 CIDs POR CUSTO (Novo Requisito) ---
                st.markdown("---")
                st.markdown("### 🩺 Top 10 CIDs de Raiz por Custo")
                
                if 'Codigo_do_CID' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                    # Usar apenas a raiz do CID
                    utilizacao_filtrada.loc[:, 'CID_Raiz'] = utilizacao_filtrada['Codigo_do_CID'].astype(str).str[:3]
                    top_cids = utilizacao_filtrada.groupby('CID_Raiz')['Valor'].sum().sort_values(ascending=False).head(10)
                    df_top_cids = top_cids.reset_index().rename(columns={'CID_Raiz':'CID Raiz','Valor':'Custo Total'})
                    
                    st.dataframe(style_dataframe_brl(df_top_cids), use_container_width=True)
                else:
                    st.info("ℹ️ Colunas de CID ou Valor não encontradas para esta análise.")

                # --- TOP 10 PROCEDIMENTOS POR CUSTO (EXISTENTE) ---
                st.markdown("---")
                st.markdown("### 💊 Top 10 Procedimentos por Custo")
                if 'Nome_do_Procedimento' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                    top_proc = utilizacao_filtrada.groupby('Nome_do_Procedimento')['Valor'].sum().sort_values(ascending=False).head(10)
                    df_top_proc = top_proc.reset_index().rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Custo Total'})
                    st.dataframe(style_dataframe_brl(df_top_proc), use_container_width=True)
                else:
                    st.info("ℹ️ Colunas de Procedimento/Valor não encontradas para esta análise.")

                
                # --- BUSCA DE BENEFICIÁRIOS POR CID (CID como Raiz - Novo Requisito) ---
                st.markdown("---")
                st.markdown("### 🔎 Buscar Beneficiários por CID de Raiz")
                
                cid_options = sorted(utilizacao_filtrada['CID_Raiz'].dropna().unique().tolist()) if 'CID_Raiz' in utilizacao_filtrada.columns else []
                cid_input = st.selectbox(
                    "Selecione o CID de Raiz (ex: I10, E11)", 
                    options=[""] + cid_options, 
                    key="busca_cid_input",
                    index=0
                )
                
                if cid_input:
                    util_cid = utilizacao_filtrada[utilizacao_filtrada['CID_Raiz'] == cid_input].copy()
                    
                    if not util_cid.empty:
                        total_users_cid = util_cid['Nome_do_Associado'].nunique()
                        total_cost_cid = util_cid['Valor'].sum()
                        
                        st.markdown(f"#### 👤 Beneficiários associados ao CID **{cid_input}**")
                        st.metric(f"Total de Beneficiários", f"{total_users_cid:,.0f}", delta=format_brl(total_cost_cid))
                        
                        # Agrupar e mostrar os usuários
                        usuarios_por_cid = util_cid.groupby('Nome_do_Associado')['Valor'].agg(
                            Custo_Total='sum',
                            Volume_Atendimentos='size',
                        ).sort_values(by='Custo_Total', ascending=False).reset_index()
                        
                        # Criar uma nova tabela interativa para seleção, permitindo a transição para a aba 'Busca'
                        st.markdown("Selecione um beneficiário nesta tabela para ver o detalhe na aba 🔍 Busca.")
                        
                        df_usuarios_cid_display = style_dataframe_brl(
                            usuarios_por_cid.rename(columns={'Nome_do_Associado': 'Beneficiário'}), 
                            currency_cols=['Custo Total']
                        )
                        
                        # Usando st.dataframe para interatividade de seleção
                        selected_data_cid = st.data_editor(
                            df_usuarios_cid_display.data, 
                            key="cid_users_table", 
                            use_container_width=True,
                            hide_index=False,
                        )
                        
                        if selected_data_cid:
                            selected_name_cid = selected_data_cid['Beneficiário'][selected_data_cid.index[0] - 1]
                            st.session_state.selected_benef = selected_name_cid
                            st.success(f"Beneficiário **{selected_name_cid}** selecionado! Vá para a aba 🔍 Busca.")
                    
                    else:
                        st.info(f"ℹ️ Nenhum atendimento encontrado para o CID {cid_input} nos filtros aplicados.")
                    
                
            # --- ABA: BUSCA (RH/MEDICO) ---
            elif tab_name == "🔍 Busca":
                st.markdown("### 🔎 Busca por Beneficiário")
                
                # Se um beneficiário foi selecionado nas tabelas Top 20 ou CID, use-o como default.
                default_benef = st.session_state.selected_benef if st.session_state.selected_benef else ""

                # caixa de busca (tempo real)
                search_input = st.text_input(
                    "Digite o nome do beneficiário (busca em tempo real)", 
                    value=default_benef,
                    key="busca_input"
                )

                # Se o usuário digitou, prioriza a busca
                search_query = search_input.strip()
                matches = []
                if search_query:
                    q_norm = normalize_name(search_query)
                    # Substring match on normalized names
                    matches = [orig for norm, orig in nomes_norm_map.items() if q_norm in norm]
                    matches = sorted(matches)
                else:
                    # quando vazio, sugerir top 20 por volume ou nomes
                    if 'Nome_do_Associado' in utilizacao_filtrada.columns:
                        vol = utilizacao_filtrada.groupby('Nome_do_Associado').size().sort_values(ascending=False)
                        suggestions = vol.head(20).index.tolist()
                        matches = [s for s in suggestions if s in nomes_possiveis]
                    else:
                        matches = nomes_possiveis[:20]

                
                # Se houver uma seleção prévia (da tabela interativa), use-a como índice
                default_index = 0
                if default_benef and default_benef in matches:
                     default_index = matches.index(default_benef) + 1 # +1 pois o primeiro item é a string vazia ("")

                chosen = None
                if matches:
                    chosen = st.selectbox(
                        "Resultados da busca — selecione o beneficiário", 
                        options=[""] + matches, 
                        index=default_index, 
                        key="busca_selectbox"
                    )
                    
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
                        
                        # --- Informações Cadastrais ---
                        st.markdown("### 📝 Informações Cadastrais")
                        if not cad_b.empty:
                            # Removendo index para aplicar 1-based no style_dataframe_brl
                            st.dataframe(style_dataframe_brl(cad_b.reset_index(drop=True), currency_cols=[]), use_container_width=True)
                        else:
                            st.info("ℹ️ Informações cadastrais não encontradas nos filtros aplicados.")

                        # --- Utilização do Plano (Atendimentos) ---
                        st.markdown("### 📋 Utilização do Plano (Atendimentos) - Interativo")
                        if not util_b.empty:
                            # APLICAR FORMAT_BRL e 1-based index
                            df_util_b_display = style_dataframe_brl(util_b.reset_index(drop=True))
                            st.data_editor(
                                df_util_b_display.data, 
                                key="util_b_table", 
                                use_container_width=True,
                                hide_index=False,
                            )
                        else:
                            st.info("ℹ️ Nenhum registro de utilização encontrado para os filtros aplicados.")
                        
                        # --- Medicina do Trabalho e Atestados (Para exportação e detalhe) ---
                        med_b = medicina_trabalho[medicina_trabalho.get('Nome_do_Associado', pd.Series()).fillna('') == selected_benef]
                        at_b = atestados[atestados.get('Nome_do_Associado', pd.Series()).fillna('') == selected_benef]

                        st.markdown("### 💼 Medicina do Trabalho (Aso, etc.)")
                        if not med_b.empty:
                            st.dataframe(style_dataframe_brl(med_b.reset_index(drop=True), currency_cols=[]), use_container_width=True)
                        else:
                            st.info("ℹ️ Nenhum registro de Medicina do Trabalho encontrado.")
                            
                        st.markdown("### 📑 Atestados/Afastamentos")
                        if not at_b.empty:
                            st.dataframe(style_dataframe_brl(at_b.reset_index(drop=True), currency_cols=[]), use_container_width=True)
                        else:
                            st.info("ℹ️ Nenhum registro de Atestados encontrado.")


                        # --- Histórico de custos e procedimentos ---
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
                                df_top_proc = top_proc_b.reset_index().rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Custo Total'})
                                st.dataframe(style_dataframe_brl(df_top_proc), use_container_width=True)
                            else:
                                st.info("ℹ️ Colunas de procedimento ou valor não encontradas.")
                        
                        with col_cid:
                            # CIDs associados
                            st.markdown("### 🩺 CIDs Associados")
                            if 'Codigo_do_CID' in util_b.columns:
                                # Agrupa por CID e soma o custo para esse CID específico
                                cids_agrupados = util_b.groupby('Codigo_do_CID')['Valor'].sum().sort_values(ascending=False)
                                df_cids = cids_agrupados.reset_index().rename(columns={'Codigo_do_CID':'CID','Valor':'Custo Total'})
                                
                                st.dataframe(style_dataframe_brl(df_cids), use_container_width=True)
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
                                util_b_export.to_excel(writer, sheet_name='Utilizacao_Individual', index=False)
                            if not cad_b.empty:
                                cad_b.to_excel(writer, sheet_name='Cadastro_Individual', index=False)
                            if not med_b.empty:
                                med_b.to_excel(writer, sheet_name='Medicina_do_Trabalho_Ind', index=False)
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


            # --- ABA: EXPORTAÇÃO (RH) ---
            elif tab_name == "📤 Exportação":
                st.markdown("### 📥 Exportar Relatório Completo")
                st.write("Baixe todas as abas do arquivo processado, respeitando os filtros de `Período`, `Sexo`, `Município`, `Faixa Etária` e `Tipo de Beneficiário` aplicados.")
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    # Preparação da Utilização
                    utilizacao_filtrada_export = utilizacao_filtrada.drop(columns=['Tipo_Beneficiario', 'Idade', 'CID_Raiz'], errors='ignore')
                    utilizacao_filtrada_export.to_excel(writer, sheet_name='Utilizacao_Filtrada', index=False)
                    
                    # Cadastro já está filtrado
                    cadastro_filtrado.to_excel(writer, sheet_name='Cadastro_Filtrado', index=False)
                    
                    # A exportação do Medicina do Trabalho e Atestados é filtrada pelos Nomes do Cadastro Filtrado
                    med_export = medicina_trabalho.copy()
                    if 'Nome_do_Associado' in med_export.columns:
                        med_export = med_export[med_export['Nome_do_Associado'].isin(cadastro_filtrado['Nome_do_Associado'])]

                    at_export = atestados.copy()
                    if 'Nome_do_Associado' in at_export.columns:
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
    
    st.sidebar.markdown("---")
    st.sidebar.success("✅ Processamento de dados concluído. Utilize as abas.")
