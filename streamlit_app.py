import pandas as pd 
import numpy as np
from unidecode import unidecode
import streamlit as st
import plotly.express as px
from io import BytesIO

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
    # 1. Configuração do Streamlit
    # ---------------------------

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
        # 4. Conversão de datas
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
        # 6.1 Busca por Nome do Beneficiário (sidebar + topo)
        # ---------------------------
        st.sidebar.subheader("🔎 Busca por Beneficiário")
        search_input_sidebar = st.sidebar.text_input("Digite nome do beneficiário (busca em tempo real)", "")
        # Também no topo
        search_input_top = st.text_input("🔎 Buscar beneficiário (topo) — digite e selecione abaixo", search_input_sidebar)

        # Normalize helper
        def normalize_name(s):
            return unidecode(str(s)).strip().upper()

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
        nomes_norm_map = {normalize_name(n): n for n in nomes_possiveis}

        # Determine search string (prefer topo input if user typed there)
        search_query = search_input_top.strip() if search_input_top.strip() != "" else search_input_sidebar.strip()
        matches = []
        if search_query:
            q_norm = normalize_name(search_query)
            # Substring match on normalized names
            matches = [orig for norm, orig in nomes_norm_map.items() if q_norm in norm]
            matches = sorted(matches)
        else:
            # show top N suggestions (by cost or volume) when empty — list top 20 by volume
            if 'Nome_do_Associado' in utilizacao_filtrada.columns:
                vol = utilizacao_filtrada.groupby('Nome_do_Associado').size().sort_values(ascending=False)
                suggestions = vol.head(20).index.tolist()
                matches = [s for s in suggestions if s in nomes_possiveis]
            else:
                matches = nomes_possiveis[:20]

        # UI: selection box com matches
        st.sidebar.subheader("Resultados da busca")
        selected_benef = None
        if matches:
            selected_benef = st.sidebar.selectbox("Selecione o beneficiário", options=[""] + matches, index=0)
            if selected_benef == "":
                selected_benef = None
        else:
            st.sidebar.write("Nenhum resultado")

        # ---------------------------
        # 8. Dashboard Tabs por Role
        # ---------------------------

        # Definir abas disponíveis por cargo
        if role == "RH":
            tabs = ["KPIs Gerais", "Comparativo de Planos", "Alertas & Inconsistências", "Exportação"]
        elif role == "MEDICO":
            tabs = ["CIDs Crônicos & Procedimentos"]
        else:
            tabs = []

        tab_objects = st.tabs(tabs)

        # Antes das abas: se usuário selecionou beneficiário, mostrar destaque no topo
        if selected_benef:
            st.markdown(f"### 🔎 Detalhes rápidos para: **{selected_benef}**")
            # botão para abrir modal com detalhes (se suportado)
            try:
                open_modal = st.button("Abrir detalhes (modal)")
                if open_modal:
                    with st.modal(f"Detalhes: {selected_benef}"):
                        st.write(f"Mostrando informações detalhadas para **{selected_benef}**")
                        # (reutilizamos a mesma lógica abaixo para exibir)
                        pass
            except Exception:
                # streamlit versão antiga, ignorar
                pass

            # Mostra sumário rápido: custo total e volume no período e filtros atuais
            if 'Nome_do_Associado' in utilizacao_filtrada.columns:
                util_b = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'] == selected_benef]
                custo_total_b = util_b['Valor'].sum() if 'Valor' in util_b.columns else 0
                volume_b = len(util_b)
                st.metric("Custo total (filtros atuais)", f"R$ {custo_total_b:,.2f}")
                st.metric("Volume (atendimentos)", f"{volume_b}")

        for i, tab_name in enumerate(tabs):
            with tab_objects[i]:
                if tab_name == "KPIs Gerais":
                    st.subheader("📌 KPIs Gerais")
                    custo_total = utilizacao_filtrada['Valor'].sum() if 'Valor' in utilizacao_filtrada.columns else 0
                    st.metric("Custo Total (R$)", f"{custo_total:,.2f}")

                    if 'Nome_do_Associado' in utilizacao_filtrada.columns and 'Valor' in utilizacao_filtrada.columns:
                        custo_por_benef = utilizacao_filtrada.groupby('Nome_do_Associado')['Valor'].sum().sort_values(ascending=False)
                        top10_volume = utilizacao_filtrada.groupby('Nome_do_Associado').size().sort_values(ascending=False)
                        st.write("**Top 10 Beneficiários por Custo**")
                        st.dataframe(custo_por_benef.head(10).reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado','Valor':'Valor'}))
                        st.write("**Top 10 Beneficiários por Volume**")
                        st.dataframe(top10_volume.head(10).reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado',0:'Volume'}))

                    if 'Data_do_Atendimento' in utilizacao_filtrada.columns:
                        utilizacao_filtrada['Mes_Ano'] = utilizacao_filtrada['Data_do_Atendimento'].dt.to_period('M')
                        evolucao = utilizacao_filtrada.groupby('Mes_Ano')['Valor'].sum().reset_index()
                        evolucao['Mes_Ano'] = evolucao['Mes_Ano'].astype(str)
                        fig = px.bar(
                            evolucao, x='Mes_Ano', y='Valor', color='Valor', text='Valor',
                            labels={'Mes_Ano':'Mês/Ano','Valor':'R$'}, height=400
                        )
                        st.plotly_chart(fig, use_container_width=True)

                elif tab_name == "Comparativo de Planos":
                    possible_cols = [col for col in utilizacao_filtrada.columns if 'plano' in col.lower() and 'descricao' in col.lower()]
                    if possible_cols:
                        plano_col = possible_cols[0]
                        st.subheader("📊 Comparativo de Planos")
                        comp = utilizacao_filtrada.groupby(plano_col)['Valor'].sum().reset_index()
                        fig = px.bar(comp, x=plano_col, y='Valor', color=plano_col, text='Valor', height=400)
                        st.plotly_chart(fig, use_container_width=True)

                        comp_volume = utilizacao_filtrada.groupby(plano_col).size().reset_index(name='Volume')
                        fig2 = px.bar(comp_volume, x=plano_col, y='Volume', color=plano_col, text='Volume', height=400)
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
                    if sexo_col and 'Codigo_do_CID' in utilizacao_filtrada.columns:
                        def padronizar_nome(nome): return unidecode(str(nome)).strip().upper()
                        utilizacao_filtrada['Nome_merge'] = utilizacao_filtrada['Nome_do_Associado'].apply(padronizar_nome)
                        cadastro_filtrado['Nome_merge'] = cadastro_filtrado['Nome_do_Associado'].apply(padronizar_nome)
                        utilizacao_merge = utilizacao_filtrada.merge(
                            cadastro_filtrado[['Nome_merge', sexo_col]].drop_duplicates(), on='Nome_merge', how='left'
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
                    buffer.seek(0)
                    st.download_button("📥 Baixar Relatório Completo", buffer, "dashboard_plano_saude.xlsx", "application/vnd.ms-excel")
                    st.success("✅ Dashboard carregado com sucesso!")

                elif tab_name == "CIDs Crônicos & Procedimentos":
                    st.subheader("🏥 Beneficiários Crônicos")
                    cids_cronicos = ['E11','I10','J45']
                    if 'Codigo_do_CID' in utilizacao_filtrada.columns:
                        utilizacao_filtrada['Cronico'] = utilizacao_filtrada['Codigo_do_CID'].isin(cids_cronicos)
                        beneficiarios_cronicos = utilizacao_filtrada[utilizacao_filtrada['Cronico']].groupby('Nome_do_Associado')['Valor'].sum()
                        st.dataframe(beneficiarios_cronicos.reset_index().rename(columns={'Nome_do_Associado':'Nome do Associado','Valor':'Valor'}))

                    st.subheader("💊 Top Procedimentos")
                    if 'Nome_do_Procedimento' in utilizacao_filtrada.columns:
                        top_proc = utilizacao_filtrada.groupby('Nome_do_Procedimento')['Valor'].sum().sort_values(ascending=False).head(10)
                        st.dataframe(top_proc.reset_index().rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Valor'}))

        # ---------------------------
        # 9. Exibição detalhada do beneficiário selecionado (expander/modal) + export individual
        # ---------------------------
        if selected_benef:
            util_b = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'] == selected_benef].copy()
            cad_b = cadastro_filtrado[cadastro_filtrado['Nome_do_Associado'] == selected_benef].copy()

            # Expander com detalhes
            with st.expander(f"🔍 Dados detalhados — {selected_benef}", expanded=True):
                st.subheader("Informações cadastrais")
                if not cad_b.empty:
                    st.dataframe(cad_b.reset_index(drop=True))
                else:
                    st.write("Informações cadastrais não encontradas nos filtros aplicados.")

                st.subheader("Utilização do plano (atendimentos relacionados)")
                if not util_b.empty:
                    st.dataframe(util_b.reset_index(drop=True))
                else:
                    st.write("Nenhum registro de utilização encontrado para os filtros aplicados.")

                # Histórico de custos e procedimentos
                st.subheader("Histórico de custos e procedimentos")
                if 'Valor' in util_b.columns:
                    custo_total_b = util_b['Valor'].sum()
                    st.metric("Custo total (filtros atuais)", f"R$ {custo_total_b:,.2f}")
                    # evolução do beneficiário
                    if 'Data_do_Atendimento' in util_b.columns:
                        util_b['Mes_Ano'] = util_b['Data_do_Atendimento'].dt.to_period('M')
                        evol_b = util_b.groupby('Mes_Ano')['Valor'].sum().reset_index()
                        evol_b['Mes_Ano'] = evol_b['Mes_Ano'].astype(str)
                        fig_b = px.line(evol_b, x='Mes_Ano', y='Valor', markers=True, labels={'Mes_Ano':'Mês/Ano','Valor':'R$'})
                        st.plotly_chart(fig_b, use_container_width=True)
                if 'Nome_do_Procedimento' in util_b.columns:
                    top_proc_b = util_b.groupby('Nome_do_Procedimento')['Valor'].sum().sort_values(ascending=False).head(20)
                    st.write("Principais procedimentos utilizados pelo beneficiário")
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

                # Alertas individuais (usando limiares simples)
                st.subheader("Alertas individuais")
                alert_msgs = []
                if 'Valor' in util_b.columns:
                    if custo_total_b > 5000:
                        alert_msgs.append(f"Custo total R$ {custo_total_b:,.2f} acima de R$ 5.000 (limiar padrão).")
                if len(util_b) > 50:
                    alert_msgs.append(f"Volume de atendimentos ({len(util_b)}) maior que 50 (limiar padrão).")
                if alert_msgs:
                    for a in alert_msgs:
                        st.warning(a)
                else:
                    st.write("Nenhum alerta automático para os limiares padrão.")

                # Exportar relatório individual em Excel
                st.subheader("Exportar relatório individual")
                buf_ind = BytesIO()
                with pd.ExcelWriter(buf_ind, engine='xlsxwriter') as writer:
                    if not util_b.empty:
                        util_b.to_excel(writer, sheet_name='Utilizacao_Individual', index=False)
                    if not cad_b.empty:
                        cad_b.to_excel(writer, sheet_name='Cadastro_Individual', index=False)
                    if not medicina_trabalho.empty:
                        med_b = medicina_trabalho[medicina_trabalho.get('Nome_do_Associado', pd.Series()).fillna('') == selected_benef]
                        if not med_b.empty:
                            med_b.to_excel(writer, sheet_name='Medicina_do_Trabalho_Ind', index=False)
                    if not atestados.empty:
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

        # Fim do processamento do arquivo
