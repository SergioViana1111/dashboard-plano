# dashboard_plano_saude_com_busca.py
import pandas as pd
import numpy as np
from unidecode import unidecode
import streamlit as st
import plotly.express as px
from io import BytesIO

# ---------------------------
# Helper: formatação BR
# ---------------------------
def format_currency_br(value):
    """Formata número float para padrão brasileiro: 1.234,56"""
    try:
        s = f"{float(value):,.2f}"
    except:
        s = "0,00"
    # s ex: '1,234.56' se locale en_US; aqui invertemos
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def format_dataframe_currency(df, cols):
    """Formata colunas monetárias de um dataframe para string em BR"""
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = df[c].apply(lambda x: format_currency_br(x) if pd.notna(x) else "")
    return df

def normalize_name(s):
    return unidecode(str(s)).strip().upper()

# ---------------------------
# 0. Autenticação segura
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

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
    
    if st.sidebar.button("Entrar"):
        try:
            usernames = st.secrets["credentials"]["usernames"]
            passwords = st.secrets["credentials"]["passwords"]
            roles = st.secrets["credentials"]["roles"]
        except Exception as e:
            st.error("Erro na leitura de st.secrets. Verifique as credenciais.")
            return
        
        if st.session_state.username_input in usernames:
            idx = usernames.index(st.session_state.username_input)
            if st.session_state.password_input == passwords[idx]:
                st.session_state.logged_in = True
                st.session_state.username = st.session_state.username_input
                st.session_state.role = roles[idx]
                st.success(f"Bem-vindo(a), {st.session_state.username}!")
            else:
                st.error("Senha incorreta")
        else:
            st.error("Usuário não encontrado")

# Chama a função de login
login()

# ---------------------------
# Função cache para carregar excel
# ---------------------------
@st.cache_data(show_spinner=False)
def load_excel(file_bytes):
    # aceita xlsx / xltx (?) - tentaremos abrir e ler abas esperadas
    xls = pd.ExcelFile(file_bytes)
    sheets = xls.sheet_names
    # tenta carregar as abas principais, se existirem
    def load_sheet(name):
        if name in sheets:
            return pd.read_excel(xls, sheet_name=name)
        else:
            return pd.DataFrame()
    utilizacao = load_sheet('Utilizacao')
    cadastro = load_sheet('Cadastro')
    medicina_trabalho = load_sheet('Medicina_do_Trabalho')
    atestados = load_sheet('Atestados')
    return utilizacao, cadastro, medicina_trabalho, atestados

# Se estiver logado, carrega o dashboard
if st.session_state.logged_in:
    role = st.session_state.role
    st.title(f"📊 Dashboard de Utilização do Plano de Saúde - {role}")

    # ---------------------------
    # Upload do arquivo
    # ---------------------------
    uploaded_file = st.file_uploader("Escolha o arquivo (.xlsx/.xls)", type=["xlsx", "xls", "xltx"])
    if uploaded_file is not None:
        utilizacao, cadastro, medicina_trabalho, atestados = load_excel(uploaded_file)

        # ---------------------------
        # Padronização de colunas
        # ---------------------------
        def clean_cols(df):
            if df is None or df.empty:
                return pd.DataFrame()
            df = df.copy()
            df.columns = [unidecode(str(col)).strip().replace(' ','_').replace('-','_') for col in df.columns]
            return df
        utilizacao = clean_cols(utilizacao)
        cadastro = clean_cols(cadastro)
        medicina_trabalho = clean_cols(medicina_trabalho)
        atestados = clean_cols(atestados)

        # ---------------------------
        # Conversão de datas
        # ---------------------------
        date_cols_util = ['Data_do_Atendimento','Competencia','Data_de_Nascimento']
        date_cols_cad = ['Data_de_Nascimento','Data_de_Admissao_do_Empregado','Data_de_Adesao_ao_Plano','Data_de_Cancelamento']
        date_cols_med = ['Data_do_Exame']
        date_cols_at = ['Data_do_Afastamento']

        for col in date_cols_util:
            if col in utilizacao.columns:
                utilizacao.loc[:, col] = pd.to_datetime(utilizacao[col], errors='coerce')
        for col in date_cols_cad:
            if col in cadastro.columns:
                cadastro.loc[:, col] = pd.to_datetime(cadastro[col], errors='coerce')
        for col in date_cols_med:
            if col in medicina_trabalho.columns:
                medicina_trabalho.loc[:, col] = pd.to_datetime(medicina_trabalho[col], errors='coerce')
        for col in date_cols_at:
            if col in atestados.columns:
                atestados.loc[:, col] = pd.to_datetime(atestados[col], errors='coerce')

        # ---------------------------
        # Tipo Beneficiário
        # ---------------------------
        if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
            utilizacao.loc[:, 'Tipo_Beneficiario'] = np.where(
                utilizacao['Nome_Titular'] == utilizacao['Nome_do_Associado'],
                'Titular', 'Dependente'
            )
        else:
            utilizacao.loc[:, 'Tipo_Beneficiario'] = 'Desconhecido'

        # ---------------------------
        # Filtros Sidebar
        # ---------------------------
        st.sidebar.subheader("Filtros")
        # Sexo - tenta detectar coluna no cadastro
        possible_sexo_cols = [col for col in cadastro.columns if 'sexo' in col.lower()]
        sexo_col = possible_sexo_cols[0] if possible_sexo_cols else None
        sexo_opts = cadastro[sexo_col].dropna().unique() if (sexo_col and not cadastro.empty) else []
        sexo_filtro = st.sidebar.multiselect("Sexo", options=list(sexo_opts), default=list(sexo_opts))

        # Tipo Beneficiário
        tipo_benef_opts = utilizacao['Tipo_Beneficiario'].dropna().unique() if 'Tipo_Beneficiario' in utilizacao.columns else []
        tipo_benef_filtro = st.sidebar.multiselect(
            "Tipo Beneficiário",
            options=list(tipo_benef_opts),
            default=list(tipo_benef_opts)
        )

        # Município
        municipio_filtro = None
        if 'Municipio_do_Participante' in cadastro.columns:
            municipio_opts = cadastro['Municipio_do_Participante'].dropna().unique()
            municipio_filtro = st.sidebar.multiselect("Município do Participante", options=list(municipio_opts), default=list(municipio_opts))

        # Faixa etária
        faixa_etaria = st.sidebar.slider("Faixa Etária", 0, 100, (18, 65))

        # Período
        if 'Data_do_Atendimento' in utilizacao.columns and not utilizacao['Data_do_Atendimento'].isna().all():
            periodo_min = utilizacao['Data_do_Atendimento'].min()
            periodo_max = utilizacao['Data_do_Atendimento'].max()
        else:
            periodo_min = pd.Timestamp.today()
            periodo_max = pd.Timestamp.today()
        periodo = st.sidebar.date_input("Período", [periodo_min, periodo_max])

        # ---------------------------
        # Barra de busca por nome (módulo extra)
        # ---------------------------
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔎 Busca rápida (Nome)")
        busca_nome_input = st.sidebar.text_input("Digite nome do beneficiário (buscar)", value="").strip()

        # ---------------------------
        # Aplicar filtros
        # ---------------------------
        cadastro_filtrado = cadastro.copy() if not cadastro.empty else cadastro
        if 'Data_de_Nascimento' in cadastro_filtrado.columns:
            idade = (pd.Timestamp.today() - cadastro_filtrado['Data_de_Nascimento']).dt.days // 365
            cadastro_filtrado = cadastro_filtrado[(idade >= faixa_etaria[0]) & (idade <= faixa_etaria[1])]
        if sexo_filtro and sexo_col:
            cadastro_filtrado = cadastro_filtrado[cadastro_filtrado[sexo_col].isin(sexo_filtro)]
        if municipio_filtro is not None and not cadastro_filtrado.empty:
            cadastro_filtrado = cadastro_filtrado[cadastro_filtrado['Municipio_do_Participante'].isin(municipio_filtro)]

        utilizacao_filtrada = utilizacao.copy()
        if tipo_benef_filtro:
            utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Tipo_Beneficiario'].isin(tipo_benef_filtro)]
        # filtra por cadastro filtrado se houver coluna Nome_do_Associado em ambos
        if ('Nome_do_Associado' in utilizacao_filtrada.columns) and ('Nome_do_Associado' in cadastro_filtrado.columns):
            utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'].isin(cadastro_filtrado['Nome_do_Associado'])]
        # período
        if 'Data_do_Atendimento' in utilizacao_filtrada.columns and periodo:
            utilizacao_filtrada = utilizacao_filtrada[
                (utilizacao_filtrada['Data_do_Atendimento'] >= pd.to_datetime(periodo[0])) &
                (utilizacao_filtrada['Data_do_Atendimento'] <= pd.to_datetime(periodo[1]))
            ]

        # ---------------------------
        # Abas por Role (inclui aba Busca)
        # ---------------------------
        if role == "RH":
            tabs = ["KPIs Gerais", "Comparativo de Planos", "Alertas & Inconsistências", "Exportação", "Busca"]
        elif role == "MEDICO":
            tabs = ["CIDs Crônicos & Procedimentos", "Busca"]
        else:
            tabs = ["Busca"]  # fallback: pelo menos a busca

        tab_objects = st.tabs(tabs)

        # ---------------------------
        # Conteúdo das abas
        # ---------------------------
        for i, tab_name in enumerate(tabs):
            with tab_objects[i]:
                if tab_name == "KPIs Gerais":
                    st.subheader("📌 KPIs Gerais")
                    custo_total = utilizacao_filtrada['Valor'].sum() if 'Valor' in utilizacao_filtrada.columns else 0
                    custo_total_format = format_currency_br(custo_total)
                    st.metric("Custo Total (R$)", custo_total_format)

                    if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        custo_por_benef = utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].sum().sort_values(ascending=False)
                        custo_por_benef_df = custo_por_benef.reset_index()
                        custo_por_benef_df = custo_por_benef_df.rename(columns={'Nome_do_Associado':'Nome do Associado','Valor':'Valor'})
                        custo_por_benef_df = format_dataframe_currency(custo_por_benef_df, ['Valor'])
                        st.write("**Top 10 Beneficiários por Custo**")
                        st.dataframe(custo_por_benef_df.head(10), use_container_width=True)

                        top10_volume = utilizacao_filtrada.groupby('Nome_do_Associado').size().sort_values(ascending=False)
                        top10_volume_df = top10_volume.reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado', 0:'Volume'})
                        st.write("**Top 10 Beneficiários por Volume**")
                        st.dataframe(top10_volume_df.head(10), use_container_width=True)

                    if 'Data_do_Atendimento' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        df_evo = utilizacao_filtrada.copy()
                        df_evo.loc[:, 'Mes_Ano'] = df_evo['Data_do_Atendimento'].dt.to_period('M').astype(str)
                        evolucao = df_evo.groupby('Mes_Ano')['Valor'].sum().reset_index()
                        evolucao['Valor_fmt'] = evolucao['Valor'].apply(lambda x: format_currency_br(x))
                        fig = px.bar(evolucao, x='Mes_Ano', y='Valor', text='Valor_fmt',
                                     labels={'Mes_Ano':'Mês/Ano','Valor':'R$'}, height=450)
                        # mostrar textos formatados; eixo Y pode manter padrão numérico (Plotly)
                        fig.update_traces(textposition='outside')
                        fig.update_layout(yaxis_title='R$')
                        st.plotly_chart(fig, use_container_width=True)

                elif tab_name == "Comparativo de Planos":
                    possible_cols = [col for col in utilizacao_filtrada.columns if 'plano' in col.lower() and 'descricao' in col.lower()]
                    if possible_cols:
                        plano_col = possible_cols[0]
                        st.subheader("📊 Comparativo de Planos")
                        comp = utilizacao_filtrada.groupby(plano_col)['Valor'].sum().reset_index()
                        comp['Valor_fmt'] = comp['Valor'].apply(lambda x: format_currency_br(x))
                        fig = px.bar(comp, x=plano_col, y='Valor', text='Valor_fmt', height=400)
                        fig.update_traces(textposition='outside')
                        st.plotly_chart(fig, use_container_width=True)

                        comp_volume = utilizacao_filtrada.groupby(plano_col).size().reset_index(name='Volume')
                        fig2 = px.bar(comp_volume, x=plano_col, y='Volume', text='Volume', height=400)
                        fig2.update_traces(textposition='outside')
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("Coluna de plano não encontrada.")

                elif tab_name == "Alertas & Inconsistências":
                    st.subheader("🚨 Alertas")
                    custo_lim = st.number_input("Limite de custo (R$)", value=5000)
                    vol_lim = st.number_input("Limite de atendimentos", value=20)

                    if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        custo_por_benef = utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].sum()
                        top10_volume = utilizacao_filtrada.groupby('Nome_do_Associado').size()
                        alert_custo = custo_por_benef[custo_por_benef > float(custo_lim)]
                        alert_vol = top10_volume[top10_volume > int(vol_lim)]

                        if not alert_custo.empty:
                            df_alert_custo = alert_custo.reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado','Valor':'Valor'})
                            df_alert_custo = format_dataframe_currency(df_alert_custo, ['Valor'])
                            st.write("**Beneficiários acima do limite de custo:**")
                            st.dataframe(df_alert_custo, use_container_width=True)
                        if not alert_vol.empty:
                            df_alert_vol = alert_vol.reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado', 0:'Volume'})
                            st.write("**Beneficiários acima do limite de volume:**")
                            st.dataframe(df_alert_vol, use_container_width=True)

                    st.subheader("⚠️ Inconsistências")
                    inconsistencias = pd.DataFrame()
                    if sexo_col and 'Codigo_do_CID' in utilizacao_filtrada.columns and 'Nome_do_Associado' in utilizacao_filtrada.columns:
                        # criar colunas de merge padronizadas
                        utilizacao_tmp = utilizacao_filtrada.copy()
                        cadastro_tmp = cadastro_filtrado.copy()
                        utilizacao_tmp.loc[:, 'Nome_merge'] = utilizacao_tmp['Nome_do_Associado'].apply(normalize_name)
                        cadastro_tmp.loc[:, 'Nome_merge'] = cadastro_tmp['Nome_do_Associado'].apply(normalize_name) if 'Nome_do_Associado' in cadastro_tmp.columns else ""
                        utilizacao_merge = utilizacao_tmp.merge(
                            cadastro_tmp[['Nome_merge', sexo_col]].drop_duplicates(), on='Nome_merge', how='left'
                        )
                        if sexo_col not in utilizacao_merge.columns:
                            utilizacao_merge[sexo_col] = 'Desconhecido'
                        else:
                            utilizacao_merge[sexo_col] = utilizacao_merge[sexo_col].fillna('Desconhecido')
                        parto_masc = utilizacao_merge[(utilizacao_merge['Codigo_do_CID']=='O80') & (utilizacao_merge[sexo_col]=='M')]
                        if not parto_masc.empty:
                            inconsistencias = pd.concat([inconsistencias, parto_masc])
                    if not inconsistencias.empty:
                        st.dataframe(inconsistencias, use_container_width=True)
                    else:
                        st.write("Nenhuma inconsistência encontrada.")

                elif tab_name == "Exportação":
                    st.subheader("📤 Exportar Relatório")
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        utilizacao_filtrada.to_excel(writer, sheet_name='Utilizacao', index=False)
                        cadastro_filtrado.to_excel(writer, sheet_name='Cadastro', index=False)
                        if not medicina_trabalho.empty:
                            medicina_trabalho.to_excel(writer, sheet_name='Medicina_do_Trabalho', index=False)
                        if not atestados.empty:
                            atestados.to_excel(writer, sheet_name='Atestados', index=False)
                        writer.save()
                    buffer.seek(0)
                    st.download_button("📥 Baixar Relatório Completo", buffer, "dashboard_plano_saude.xlsx", "application/vnd.ms-excel")
                    st.success("✅ Arquivo gerado com sucesso!")

                elif tab_name == "CIDs Crônicos & Procedimentos":
                    st.subheader("🏥 Beneficiários Crônicos")
                    cids_cronicos = ['E11','I10','J45']  # ajuste conforme necessidade
                    if 'Codigo_do_CID' in utilizacao_filtrada.columns:
                        util_tmp = utilizacao_filtrada.copy()
                        util_tmp.loc[:, 'Cronico'] = util_tmp['Codigo_do_CID'].isin(cids_cronicos)
                        beneficiarios_cronicos = util_tmp[util_tmp['Cronico']].groupby('Nome_do_Associado')['Valor'].sum().reset_index()
                        beneficiarios_cronicos = beneficiarios_cronicos.rename(columns={'Nome_do_Associado':'Nome do Associado','Valor':'Valor'})
                        beneficiarios_cronicos = format_dataframe_currency(beneficiarios_cronicos, ['Valor'])
                        st.dataframe(beneficiarios_cronicos, use_container_width=True)

                    st.subheader("💊 Top Procedimentos")
                    if 'Nome_do_Procedimento' in utilizacao_filtrada.columns:
                        top_proc = utilizacao_filtrada.groupby('Nome_do_Procedimento')['Valor'].sum().sort_values(ascending=False).head(10)
                        top_proc_df = top_proc.reset_index().rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Valor'})
                        top_proc_df = format_dataframe_currency(top_proc_df, ['Valor'])
                        st.dataframe(top_proc_df, use_container_width=True)

                elif tab_name == "Busca":
                    st.subheader("🔎 Busca por Beneficiário")
                    st.write("Digite parte ou nome completo do beneficiário na caixa de busca (sidebar).")
                    if busca_nome_input:
                        # busca case-insensitive e sem acentos tanto em cadastro quanto em utilização
                        term = normalize_name(busca_nome_input)
                        # preparar coluna de busca em cadastro e utilização
                        if 'Nome_do_Associado' in cadastro.columns:
                            cadastro_search = cadastro.copy()
                            cadastro_search.loc[:, 'Nome_merge'] = cadastro_search['Nome_do_Associado'].apply(normalize_name)
                        else:
                            cadastro_search = pd.DataFrame(columns=['Nome_do_Associado','Nome_merge'])
                        if 'Nome_do_Associado' in utilizacao.columns:
                            utilizacao_search = utilizacao.copy()
                            utilizacao_search.loc[:, 'Nome_merge'] = utilizacao_search['Nome_do_Associado'].apply(normalize_name)
                        else:
                            utilizacao_search = pd.DataFrame(columns=['Nome_do_Associado','Nome_merge'])

                        # encontrar correspondências em cadastro (preferível), senão em utilização
                        matches = cadastro_search[cadastro_search['Nome_merge'].str.contains(term, na=False)]
                        if matches.empty:
                            matches = utilizacao_search[utilizacao_search['Nome_merge'].str.contains(term, na=False)][['Nome_do_Associado','Nome_merge']].drop_duplicates()
                        
                        if matches.empty:
                            st.info("Nenhum beneficiário encontrado com esse termo.")
                        else:
                            # mostrar lista de correspondências
                            st.write(f"🔎 Resultados encontrados: {len(matches)}")
                            # mostra nomes e permite selecionar 1
                            names = matches['Nome_do_Associado'].dropna().unique().tolist()
                            sel_name = st.selectbox("Selecione o beneficiário para ver detalhes", options=names)
                            if sel_name:
                                # filtrar utilização e cadastro pelo nome selecionado
                                util_ben = utilizacao_search[utilizacao_search['Nome_merge'] == normalize_name(sel_name)].copy()
                                cad_ben = cadastro_search[cadastro_search['Nome_merge'] == normalize_name(sel_name)].copy()

                                # aplicar também os filtros gerais (faixa etária/sexo/periodo/tipo) aos dados do beneficiário
                                # se utilizacao_filtrada tiver sido filtrado pelo período e etc, podemos intersectar com util_ben
                                if not utilizacao_filtrada.empty and 'Nome_do_Associado' in utilizacao_filtrada.columns:
                                    util_ben = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'] == sel_name].copy()

                                # principais indicadores do beneficiário
                                st.markdown("### 📋 Resumo do Beneficiário")
                                total_ben = util_ben['Valor'].sum() if 'Valor' in util_ben.columns else 0
                                total_ben_fmt = format_currency_br(total_ben)
                                n_atend = len(util_ben) if not util_ben.empty else 0
                                st.write(f"**Nome:** {sel_name}")
                                if not cad_ben.empty and 'Data_de_Nascimento' in cad_ben.columns:
                                    dt_nasc = cad_ben.iloc[0].get('Data_de_Nascimento', None)
                                    if pd.notna(dt_nasc):
                                        idade = (pd.Timestamp.today() - pd.to_datetime(dt_nasc)).days // 365
                                        st.write(f"**Idade:** {int(idade)}")
                                st.write(f"**Total de atendimentos (no período aplicado):** {n_atend}")
                                st.write(f"**Custo total (no período aplicado):** R$ {total_ben_fmt}")

                                # tabela de utilização do beneficiário (formatada)
                                if not util_ben.empty:
                                    show_cols = util_ben.columns.tolist()
                                    # preferir colunas comuns como Data_do_Atendimento, Nome_do_Procedimento, Codigo_do_CID, Valor
                                    cols_to_show = [c for c in ['Data_do_Atendimento','Nome_do_Procedimento','Codigo_do_CID','Valor','Tipo_Beneficiario'] if c in util_ben.columns]
                                    df_ben_table = util_ben[cols_to_show].copy()
                                    if 'Valor' in df_ben_table.columns:
                                        df_ben_table = format_dataframe_currency(df_ben_table, ['Valor'])
                                    # formatar data colunas
                                    for c in df_ben_table.columns:
                                        if 'Data' in c and c in df_ben_table.columns:
                                            df_ben_table[c] = df_ben_table[c].dt.strftime('%Y-%m-%d')
                                    st.markdown("#### 🧾 Histórico de Utilização")
                                    st.dataframe(df_ben_table, use_container_width=True)

                                    # Top procedimentos do beneficiário
                                    if 'Nome_do_Procedimento' in util_ben.columns:
                                        top_proc = util_ben.groupby('Nome_do_Procedimento')['Valor'].sum().sort_values(ascending=False).reset_index()
                                        top_proc = top_proc.rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Valor'})
                                        top_proc = format_dataframe_currency(top_proc, ['Valor'])
                                        st.markdown("#### 💊 Procedimentos (por custo)")
                                        st.dataframe(top_proc.head(10), use_container_width=True)

                                    # CIDs associados
                                    if 'Codigo_do_CID' in util_ben.columns:
                                        cids = util_ben['Codigo_do_CID'].value_counts().reset_index().rename(columns={'index':'CID','Codigo_do_CID':'Contagem'})
                                        st.markdown("#### 🧾 CIDs")
                                        st.dataframe(cids, use_container_width=True)
                                else:
                                    st.info("Sem registros de utilização para o beneficiário no período/filtragem atual.")

                                # Exportar relatório individual
                                st.markdown("---")
                                if st.button("📥 Exportar relatório deste beneficiário (Excel)"):
                                    buffer = BytesIO()
                                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                        util_ben.to_excel(writer, sheet_name='Utilizacao_Beneficiario', index=False)
                                        cad_ben.to_excel(writer, sheet_name='Cadastro_Beneficiario', index=False)
                                        writer.save()
                                    buffer.seek(0)
                                    st.download_button("⬇️ Baixar arquivo", buffer, file_name=f"relatorio_{sel_name}.xlsx", mime="application/vnd.ms-excel")

                    else:
                        st.write("Digite um nome na busca (sidebar) para ver o relatório detalhado de um beneficiário.")

        # fim das abas
    else:
        st.info("Faça upload do arquivo do cliente (.xlsx) para carregar o dashboard.")
