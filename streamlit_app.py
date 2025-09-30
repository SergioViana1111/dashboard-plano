import pandas as pd 
import numpy as np
from unidecode import unidecode
import streamlit as st
import plotly.express as px
from io import BytesIO
import re # Módulo de expressões regulares para limpeza mais robusta

# ---------------------------
# 0. FUNÇÃO DE FORMATAÇÃO BRASILEIRA (AJUSTADA)
# ---------------------------
def format_brl(value):
    """Formata um float ou int para string no padrão monetário brasileiro (R$ 1.234,56)"""
    if pd.isna(value):
        return "R$ 0,00"
    # Garante que o valor é float antes de formatar
    value = float(value) 
    # Formata para string BR: ponto para milhar, vírgula para decimal
    return "R$ {:,.2f}".format(value).replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")

# NOVA FUNÇÃO: Formata o DataFrame inteiro com o padrão BR
def style_dataframe_brl(df, value_cols=['Valor']):
    """Aplica formatação monetária BR em colunas específicas de um DataFrame.
    Retorna um Styler para uso no st.dataframe."""
    
    formatters = {}
    
    # 1. Colunas de Valor (R$ 1.234,56)
    for col in value_cols:
        if col in df.columns:
            # Usamos a função format_brl como formatter
            formatters[col] = format_brl
    
    # 2. Colunas de Volume (1.234) - Se houver colunas '0' ou 'Volume' não monetárias
    # Verifica a coluna 'Volume' se existir
    if 'Volume' in df.columns and 'Volume' not in formatters:
        # Formato de número inteiro com separador de milhar BR (ponto)
        formatters['Volume'] = lambda x: '{:,.0f}'.format(x).replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        
    # Verifica a coluna '0' (comum em count/size()) se existir
    if 0 in df.columns and 0 not in formatters:
        formatters[0] = lambda x: '{:,.0f}'.format(x).replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")

    # Aplica o estilo
    if formatters:
        return df.style.format(formatters)
    return df


# ---------------------------
# 0. Autenticação segura
# ---------------------------
# Configuração inicial do Streamlit
st.set_page_config(layout="wide")

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
    
    st.sidebar.subheader("🔐 Login")
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

    if st.sidebar.button("Entrar"):
        usernames = st.secrets["credentials"]["usernames"]
        passwords = st.secrets["credentials"]["passwords"]
        roles = st.secrets["credentials"]["roles"]
        
        if st.session_state.username_input in usernames:
            idx = usernames.index(st.session_state.username_input)
            if st.session_state.password_input == passwords[idx]:
                st.session_state.logged_in = True
                st.session_state.username = st.session_state.username_input
                st.session_state.role = roles[idx]
                st.success(f"Bem-vindo(a), {st.session_state.username}!")
                # Força o refresh da página para carregar o dashboard
                st.rerun()
            else:
                st.error("Senha incorreta")
        else:
            st.error("Usuário não encontrado")

# Chama a função de login
login()

# Se estiver logado, carrega o dashboard imediatamente
if st.session_state.logged_in:
    role = st.session_state.role
    st.title(f"📊 Dashboard de Utilização do Plano de Saúde - {role}")
    
    # ---------------------------
    # 2. Upload do arquivo
    # ---------------------------
    uploaded_file = st.file_uploader("Escolha o arquivo .xltx", type="xltx")
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
        # 3. Padronização de colunas
        # ---------------------------
        def clean_cols(df):
            df.columns = [unidecode(col).strip().replace(' ','_').replace('-','_') for col in df.columns]
            return df
        utilizacao = clean_cols(utilizacao)
        cadastro = clean_cols(cadastro)
        medicina_trabalho = clean_cols(medicina_trabalho)
        atestados = clean_cols(atestados)

        # ---------------------------
        # 4. Conversão de datas e VALORES (MODIFICADO)
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
                st.warning(f"Erro ao converter a coluna 'Valor' para numérico: {e}")


        # ---------------------------
        # 5. Tipo Beneficiário
        # ---------------------------
        if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
            utilizacao['Tipo_Beneficiario'] = np.where(
                utilizacao['Nome_Titular'] == utilizacao['Nome_do_Associado'],
                'Titular', 'Dependente'
            )
        else:
            utilizacao['Tipo_Beneficiario'] = 'Desconhecido'

        # ---------------------------
        # 6. Filtros Sidebar
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
        # 7. Aplicar filtros
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
        # garantir que filtragem cruze com cadastro filtrado se houver Nome_do_Associado em ambas
        if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Nome_do_Associado' in cadastro_filtrado.columns:
            utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'].isin(cadastro_filtrado['Nome_do_Associado'])]
        if 'Data_do_Atendimento' in utilizacao_filtrada.columns:
            utilizacao_filtrada = utilizacao_filtrada[
                (utilizacao_filtrada['Data_do_Atendimento'] >= pd.to_datetime(periodo[0])) &
                (utilizacao_filtrada['Data_do_Atendimento'] <= pd.to_datetime(periodo[1]))
            ]

        # ---------------------------
        # 7.1 Preparar lista de nomes para busca (respeitando os filtros aplicados)
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
        # 8. Dashboard Tabs por Role (inserir aba "Busca" antes da "Exportação")
        # ---------------------------

        # Definir abas disponíveis por cargo
        if role == "RH":
            tabs = ["KPIs Gerais", "Comparativo de Planos", "Alertas & Inconsistências", "Exportação"]
        elif role == "MEDICO":
            tabs = ["CIDs Crônicos & Procedimentos"]
        else:
            tabs = []

        # inserir "Busca" antes de "Exportação" se existir
        if "Exportação" in tabs:
            export_index = tabs.index("Exportação")
            tabs.insert(export_index, "Busca")
        elif role == "MEDICO":
              # Adiciona Busca para o Médico também
              tabs.append("Busca")

        tab_objects = st.tabs(tabs)
        
        # ---------------------------
        # 8.1 Implementação da aba "Busca" e Detalhes
        # ---------------------------
        if "Busca" in tabs:
            idx_busca = tabs.index("Busca")
            with tab_objects[idx_busca]:
                st.subheader("🔎 Busca por Beneficiário")
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
                    chosen = st.selectbox("Resultados da busca — selecione o beneficiário", options=[""] + matches, index=0, key="busca_selectbox")
                    if chosen == "":
                        st.session_state.selected_benef = None
                    else:
                        st.session_state.selected_benef = chosen
                else:
                    st.write("Nenhum resultado")

                # --- INÍCIO: Seção Detalhada (Movida para dentro da aba Busca) ---
                selected_benef = st.session_state.selected_benef 
                if selected_benef:
                    st.markdown(f"### 🔎 Detalhes rápidos para: **{selected_benef}**")

                    # Preparar dados do beneficiário
                    util_b = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'] == selected_benef].copy()
                    cad_b = cadastro_filtrado[cadastro_filtrado['Nome_do_Associado'] == selected_benef].copy()

                    # Métricas rápidas
                    if 'Nome_do_Associado' in utilizacao_filtrada.columns:
                        custo_total_b = util_b['Valor'].sum() if 'Valor' in util_b.columns else 0
                        volume_b = len(util_b)
                        # APLICA FORMAT_BRL AQUI
                        st.metric("Custo total (filtros atuais)", format_brl(custo_total_b)) 
                        st.metric("Volume (atendimentos)", f"{volume_b}")

                    # Expander com detalhes
                    with st.expander(f"🔍 Dados detalhados — {selected_benef}", expanded=True):
                        st.subheader("Informações cadastrais")
                        if not cad_b.empty:
                            st.dataframe(cad_b.reset_index(drop=True))
                        else:
                            st.write("Informações cadastrais não encontradas nos filtros aplicados.")

                        st.subheader("Utilização do plano (atendimentos relacionados)")
                        if not util_b.empty:
                            # APLICAR FORMAT_BRL PARA A COLUNA 'Valor' NO DATAFRAME VISUAL
                            # USANDO A NOVA FUNÇÃO style_dataframe_brl
                            st.dataframe(style_dataframe_brl(util_b.reset_index(drop=True)))
                        else:
                            st.write("Nenhum registro de utilização encontrado para os filtros aplicados.")

                        # Histórico de custos e procedimentos
                        st.subheader("Histórico de custos e procedimentos")
                        if 'Valor' in util_b.columns:
                            # APLICA FORMAT_BRL AQUI
                            st.metric("Custo total (filtros atuais)", format_brl(custo_total_b))
                            
                            # evolução do beneficiário
                            if 'Data_do_Atendimento' in util_b.columns and not util_b.empty:
                                util_b.loc[:, 'Mes_Ano'] = util_b['Data_do_Atendimento'].dt.to_period('M')
                                evol_b = util_b.groupby('Mes_Ano')['Valor'].sum().reset_index()
                                evol_b['Mes_Ano'] = evol_b['Mes_Ano'].astype(str)
                                fig_b = px.line(evol_b, x='Mes_Ano', y='Valor', markers=True, labels={'Mes_Ano':'Mês/Ano','Valor':'R$'})
                                # Formatação de eixo para BR
                                fig_b.update_yaxes(tickprefix="R$", tickformat=",.2f") # Usa tickformat nativo para milhares
                                fig_b.update_traces(hovertemplate='R$ %{y:,.2f}') 
                                st.plotly_chart(fig_b, use_container_width=True)
                            else:
                                st.write("Dados de data e valor insuficientes para gráfico de evolução.")


                            if 'Nome_do_Procedimento' in util_b.columns and 'Valor' in util_b.columns:
                                top_proc_b = util_b.groupby('Nome_do_Procedimento')['Valor'].sum().sort_values(ascending=False).head(20)
                                st.write("Principais procedimentos utilizados pelo beneficiário")
                                
                                # APLICAR FORMAT_BRL PARA A COLUNA 'Valor' NO DATAFRAME VISUAL
                                if 'Valor' in top_proc_b.index.name: # Checa se a série é o Valor
                                    df_top_proc = top_proc_b.reset_index().rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Valor'})
                                    # USANDO A NOVA FUNÇÃO style_dataframe_brl
                                    st.dataframe(style_dataframe_brl(df_top_proc))
                                else:
                                    st.dataframe(top_proc_b.reset_index().rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Valor'}))

                        # CIDs associados
                        st.subheader("CIDs associados")
                        if 'Codigo_do_CID' in util_b.columns:
                            cids = util_b['Codigo_do_CID'].dropna().unique().tolist()
                            if len(cids) > 0:
                                st.write(", ".join(map(str, cids)))
                            else:
                                st.write("Nenhum CID associado encontrado.")
                        else:
                            st.write("Coluna 'Codigo_do_CID' não encontrada.")

                        
                        # Exportar relatório individual em Excel
                        st.subheader("Exportar relatório individual")
                        buf_ind = BytesIO()
                        with pd.ExcelWriter(buf_ind, engine='xlsxwriter') as writer:
                            if not util_b.empty:
                                util_b.to_excel(writer, sheet_name='Utilizacao_Individual', index=False)
                            if not cad_b.empty:
                                cad_b.to_excel(writer, sheet_name='Cadastro_Individual', index=False)
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
                            label="📥 Exportar relatório individual (.xlsx)",
                            data=buf_ind,
                            file_name=f"relatorio_{normalize_name(selected_benef)[:50]}.xlsx",
                            mime="application/vnd.ms-excel"
                        )
                # --- FIM: Seção Detalhada ---
        
        # ---------------------------
        # 9. Conteúdo das demais abas (KPIs, Comparativo, Alertas, Exportação, CIDs...)
        # ---------------------------

        for i, tab_name in enumerate(tabs):
            # pular a aba Busca
            if tab_name == "Busca":
                continue

            with tab_objects[i]:
                if tab_name == "KPIs Gerais":
                    st.subheader("📌 KPIs Gerais")
                    custo_total = utilizacao_filtrada['Valor'].sum() if 'Valor' in utilizacao_filtrada.columns else 0
                    # APLICA FORMAT_BRL AQUI
                    st.metric("Custo Total (R$)", format_brl(custo_total))

                    if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        custo_por_benef = utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].sum().sort_values(ascending=False)
                        top10_volume = utilizacao_filtrada.groupby('Nome_do_Associado').size().sort_values(ascending=False)
                        
                        st.write("**Top 10 Beneficiários por Custo**")
                        df_custo = custo_por_benef.head(10).reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado','Valor':'Valor'})
                        # USANDO A NOVA FUNÇÃO style_dataframe_brl
                        st.dataframe(style_dataframe_brl(df_custo))
                        
                        st.write("**Top 10 Beneficiários por Volume**")
                        df_volume = top10_volume.head(10).reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado',0:'Volume'})
                        # USANDO A NOVA FUNÇÃO style_dataframe_brl (sem R$)
                        st.dataframe(style_dataframe_brl(df_volume, value_cols=[]))

                    if 'Data_do_Atendimento' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        # Para evitar SettingWithCopyWarning
                        utilizacao_filtrada_temp = utilizacao_filtrada.copy() 
                        utilizacao_filtrada_temp['Mes_Ano'] = utilizacao_filtrada_temp['Data_do_Atendimento'].dt.to_period('M')
                        evolucao = utilizacao_filtrada_temp.groupby('Mes_Ano')['Valor'].sum().reset_index()
                        evolucao['Mes_Ano'] = evolucao['Mes_Ano'].astype(str)
                        fig = px.bar(
                            evolucao, x='Mes_Ano', y='Valor', color='Valor', text='Valor',
                            labels={'Mes_Ano':'Mês/Ano','Valor':'R$'}, height=400
                        )
                        # Formatação de eixo para BR
                        fig.update_yaxes(tickprefix="R$", tickformat=",.2f")
                        fig.update_traces(hovertemplate='R$ %{y:,.2f}') 
                        st.plotly_chart(fig, use_container_width=True)

                elif tab_name == "Comparativo de Planos":
                    possible_cols = [col for col in utilizacao_filtrada.columns if 'plano' in col.lower() and 'descricao' in col.lower()]
                    if possible_cols and 'Valor' in utilizacao_filtrada.columns:
                        plano_col = possible_cols[0]
                        st.subheader("📊 Comparativo de Planos")
                        comp = utilizacao_filtrada.groupby(plano_col)['Valor'].sum().reset_index()
                        fig = px.bar(comp, x=plano_col, y='Valor', color=plano_col, text='Valor', height=400)
                        # Formatação de eixo para BR
                        fig.update_yaxes(tickprefix="R$", tickformat=",.2f")
                        fig.update_traces(hovertemplate='R$ %{y:,.2f}') 
                        st.plotly_chart(fig, use_container_width=True)

                        comp_volume = utilizacao_filtrada.groupby(plano_col).size().reset_index(name='Volume')
                        fig2 = px.bar(comp_volume, x=plano_col, y='Volume', color=plano_col, text='Volume', height=400)
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("Coluna de plano ou valor não encontrada.")

                elif tab_name == "Alertas & Inconsistências":
                    st.subheader("🚨 Alertas")
                    # Os inputs de número (custo_lim) já esperam o formato numérico, sem formatação BR
                    custo_lim = st.number_input("Limite de custo (R$)", value=5000.00, step=100.00, key=f"custo_lim_{tab_name}")
                    vol_lim = st.number_input("Limite de atendimentos", value=20, key=f"vol_lim_{tab_name}")

                    if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        custo_por_benef = utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].sum()
                        top10_volume = utilizacao_filtrada.groupby('Nome_do_Associado').size()
                        alert_custo = custo_por_benef[custo_por_benef > custo_lim]
                        alert_vol = top10_volume[top10_volume > vol_lim]

                        if not alert_custo.empty:
                            st.write("**Beneficiários acima do limite de custo:**")
                            df_alert_custo = alert_custo.reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado','Valor':'Valor'})
                            # USANDO A NOVA FUNÇÃO style_dataframe_brl
                            st.dataframe(style_dataframe_brl(df_alert_custo))
                            
                        if not alert_vol.empty:
                            st.write("**Beneficiários acima do limite de volume:**")
                            df_alert_vol = alert_vol.reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado',0:'Volume'})
                            # USANDO A NOVA FUNÇÃO style_dataframe_brl (sem R$)
                            st.dataframe(style_dataframe_brl(df_alert_vol, value_cols=[]))

                    st.subheader("⚠️ Inconsistências")
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
                        
                        parto_masc = utilizacao_merge[(utilizacao_merge['Codigo_do_CID']=='O80') & (utilizacao_merge[sexo_col]=='M')]
                        if not parto_masc.empty:
                            inconsistencias = pd.concat([inconsistencias, parto_masc.drop(columns='Nome_merge')])
                            
                    if not inconsistencias.empty:
                        # Aplicar formatação para a coluna 'Valor' nas inconsistências
                        # USANDO A NOVA FUNÇÃO style_dataframe_brl
                        st.dataframe(style_dataframe_brl(inconsistencias))
                    else:
                        st.write("Nenhuma inconsistência encontrada.")

                elif tab_name == "Exportação":
                    st.subheader("📤 Exportar Relatório")
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        # Para exportar, é melhor que os dados voltem ao formato numérico puro
                        utilizacao_filtrada.to_excel(writer, sheet_name='Utilizacao', index=False)
                        cadastro_filtrado.to_excel(writer, sheet_name='Cadastro', index=False)
                        if not medicina_trabalho.empty:
                            medicina_trabalho.to_excel(writer, sheet_name='Medicina_do_Trabalho', index=False)
                        if not atestados.empty:
                            atestados.to_excel(writer, sheet_name='Atestados', index=False)
                    buffer.seek(0)
                    st.download_button("📥 Baixar Relatório Completo", buffer, "dashboard_plano_saude.xlsx", "application/vnd.ms-excel")
                    st.success("✅ Dashboard carregado com sucesso!")

                elif tab_name == "CIDs Crônicos & Procedimentos":
                    st.subheader("🏥 Beneficiários Crônicos")
                    cids_cronicos = ['E11','I10','J45'] 
                    if 'Codigo_do_CID' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        utilizacao_filtrada_temp = utilizacao_filtrada.copy()
                        utilizacao_filtrada_temp.loc[:, 'Cronico'] = utilizacao_filtrada_temp['Codigo_do_CID'].isin(cids_cronicos)
                        beneficiarios_cronicos = utilizacao_filtrada_temp[utilizacao_filtrada_temp['Cronico']].groupby('Nome_do_Associado')['Valor'].sum()
                        df_cronicos = beneficiarios_cronicos.reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado','Valor':'Valor'})
                        # USANDO A NOVA FUNÇÃO style_dataframe_brl
                        st.dataframe(style_dataframe_brl(df_cronicos))

                    st.subheader("💊 Top Procedimentos")
                    if 'Nome_do_Procedimento' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        top_proc = utilizacao_filtrada.groupby('Nome_do_Procedimento')['Valor'].sum().sort_values(ascending=False).head(10)
                        df_top_proc = top_proc.reset_index().rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Valor'})
                        # USANDO A NOVA FUNÇÃO style_dataframe_brl
                        st.dataframe(style_dataframe_brl(df_top_proc))
                    else:
                        st.info("Colunas de CID ou Procedimento/Valor não encontradas para esta análise.")
