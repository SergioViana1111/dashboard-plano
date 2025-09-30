import pandas as pd 
import numpy as np
from unidecode import unidecode
import streamlit as st
import plotly.express as px
from io import BytesIO
import locale

# Configurar locale brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    # fallback se não suportado no ambiente
    locale.setlocale(locale.LC_ALL, '')

# ---------------------------
# 0. Autenticação segura
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.selected_benef = None
    st.session_state.show_details_for = None

def login():
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

# Função utilitária para normalizar nomes
def normalize_name(s):
    return unidecode(str(s)).strip().upper()

# Função para sanitizar keys
def _sanitize_key(s):
    return "".join(e for e in s if e.isalnum())

# Formatação monetária BR
def br_money(v):
    try:
        return locale.currency(v, grouping=True)
    except:
        # fallback
        return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# ---------------------------
# Dashboard principal
# ---------------------------
if st.session_state.logged_in:
    role = st.session_state.role
    st.title(f"📊 Dashboard de Utilização do Plano de Saúde - {role}")

    # ---------------------------
    # Upload do arquivo
    # ---------------------------
    uploaded_file = st.file_uploader("Escolha o arquivo .xltx", type="xltx")
    if uploaded_file is not None:
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

        # Padronizar colunas
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

        # Tipo Beneficiário
        if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
            utilizacao['Tipo_Beneficiario'] = np.where(
                utilizacao['Nome_Titular'] == utilizacao['Nome_do_Associado'],
                'Titular', 'Dependente'
            )
        else:
            utilizacao['Tipo_Beneficiario'] = 'Desconhecido'

        # ---------------------------
        # Sidebar - Filtros gerais
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
        # Aplicar filtros
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
            utilizacao_filtrada = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'].isin(cadastro_filtrado['Nome_do_Associado'])]
        if 'Data_do_Atendimento' in utilizacao_filtrada.columns:
            utilizacao_filtrada = utilizacao_filtrada[
                (utilizacao_filtrada['Data_do_Atendimento'] >= pd.to_datetime(periodo[0])) &
                (utilizacao_filtrada['Data_do_Atendimento'] <= pd.to_datetime(periodo[1]))
            ]

        # ---------------------------
        # Preparar lista de nomes para busca
        # ---------------------------
        nomes_from_cad = set()
        if 'Nome_do_Associado' in cadastro_filtrado.columns:
            nomes_from_cad = set(cadastro_filtrado['Nome_do_Associado'].dropna().unique())
        nomes_from_util = set()
        if 'Nome_do_Associado' in utilizacao_filtrada.columns:
            nomes_from_util = set(utilizacao_filtrada['Nome_do_Associado'].dropna().unique())
        nomes_possiveis = sorted(list(nomes_from_cad.union(nomes_from_util)))
        nomes_norm_map = {normalize_name(n): n for n in nomes_possiveis}

        # ---------------------------
        # Tabs por Role
        # ---------------------------
        if role == "RH":
            tabs = ["KPIs Gerais", "Comparativo de Planos", "Alertas & Inconsistências", "Busca", "Exportação"]
        elif role == "MEDICO":
            tabs = ["CIDs Crônicos & Procedimentos", "Busca"]
        else:
            tabs = ["Busca"]

        tab_objects = st.tabs(tabs)

        # ---------------------------
        # Função interna para renderizar aba Busca
        # ---------------------------
        def render_busca(tab_idx):
            with tab_objects[tab_idx]:
                st.subheader("🔎 Busca por Beneficiário")
                search_input = st.text_input("Digite o nome do beneficiário", "")

                # Matches filtrando nomes
                matches = []
                if search_input:
                    q_norm = normalize_name(search_input)
                    matches = [orig for norm, orig in nomes_norm_map.items() if q_norm in norm]
                else:
                    # top 20 por volume
                    if 'Nome_do_Associado' in utilizacao_filtrada.columns:
                        vol = utilizacao_filtrada.groupby('Nome_do_Associado').size().sort_values(ascending=False)
                        suggestions = vol.head(20).index.tolist()
                        matches = [s for s in suggestions if s in nomes_possiveis]
                    else:
                        matches = nomes_possiveis[:20]

                # Selectbox
                selected_benef = None
                if matches:
                    selected_benef = st.selectbox("Selecione o beneficiário", options=[""] + matches, index=0)
                    if selected_benef == "":
                        selected_benef = None
                st.session_state.selected_benef = selected_benef

                # Mostrar resumo rápido + botão para detalhes
                if selected_benef:
                    util_b = utilizacao_filtrada[utilizacao_filtrada['Nome_do_Associado'] == selected_benef].copy()
                    custo_total_b = util_b['Valor'].sum() if 'Valor' in util_b.columns else 0
                    volume_b = len(util_b)
                    key_base = _sanitize_key(normalize_name(selected_benef))

                    st.metric("Custo total (filtros atuais)", br_money(custo_total_b), key=f"metric_custo_busca_{key_base}")
                    st.metric("Volume (atendimentos)", str(volume_b), key=f"metric_vol_busca_{key_base}")

                    # evolução
                    if 'Valor' in util_b.columns and 'Data_do_Atendimento' in util_b.columns and not util_b.empty:
                        util_b['Mes_Ano'] = util_b['Data_do_Atendimento'].dt.to_period('M')
                        evol_b = util_b.groupby('Mes_Ano')['Valor'].sum().reset_index()
                        evol_b['Mes_Ano'] = evol_b['Mes_Ano'].astype(str)
                        fig_b = px.line(evol_b, x='Mes_Ano', y='Valor', markers=True, labels={'Mes_Ano':'Mês/Ano','Valor':'R$'})
                        st.plotly_chart(fig_b, use_container_width=True, key=f"fig_busca_{key_base}")

                    # botão Mostrar/Ocultar detalhes
                    btn_key = f"btn_show_det_{key_base}"
                    if st.button("Mostrar/Ocultar detalhes", key=btn_key):
                        if st.session_state.show_details_for == selected_benef:
                            st.session_state.show_details_for = None
                        else:
                            st.session_state.show_details_for = selected_benef

                    if st.session_state.get("show_details_for") == selected_benef:
                        cad_b = cadastro_filtrado[cadastro_filtrado['Nome_do_Associado'] == selected_benef].copy()

                        with st.expander(f"🔍 Dados detalhados — {selected_benef}", expanded=True):
                            st.subheader("Informações cadastrais")
                            if not cad_b.empty:
                                st.dataframe(cad_b.reset_index(drop=True))
                            else:
                                st.write("Informações cadastrais não encontradas.")

                            st.subheader("Utilização do plano")
                            if not util_b.empty:
                                st.dataframe(util_b.reset_index(drop=True))
                            else:
                                st.write("Nenhum registro encontrado.")

                            st.subheader("Histórico de custos e procedimentos")
                            if 'Valor' in util_b.columns:
                                st.metric("Custo total (filtros atuais)", br_money(util_b['Valor'].sum()))
                                if 'Data_do_Atendimento' in util_b.columns and not util_b.empty:
                                    util_b['Mes_Ano'] = util_b['Data_do_Atendimento'].dt.to_period('M')
                                    evol_b = util_b.groupby('Mes_Ano')['Valor'].sum().reset_index()
                                    evol_b['Mes_Ano'] = evol_b['Mes_Ano'].astype(str)
                                    fig_b = px.line(evol_b, x='Mes_Ano', y='Valor', markers=True, labels={'Mes_Ano':'Mês/Ano','Valor':'R$'})
                                    st.plotly_chart(fig_b, use_container_width=True)
                                if 'Nome_do_Procedimento' in util_b.columns:
                                    top_proc_b = util_b.groupby('Nome_do_Procedimento')['Valor'].sum().sort_values(ascending=False).head(20)
                                    st.write("Principais procedimentos")
                                    st.dataframe(top_proc_b.reset_index().rename(columns={'Nome_do_Procedimento':'Procedimento','Valor':'Valor'}))

                            st.subheader("CIDs associados")
                            if 'Codigo_do_CID' in util_b.columns:
                                cids = util_b['Codigo_do_CID'].dropna().unique().tolist()
                                st.write(", ".join(cids) if cids else "Nenhum CID associado.")

                            # Export individual
                            buf_ind = BytesIO()
                            with pd.ExcelWriter(buf_ind, engine='xlsxwriter') as writer:
                                if not util_b.empty:
                                    util_b.to_excel(writer, sheet_name='Utilizacao_Individual', index=False)
                                if not cad_b.empty:
                                    cad_b.to_excel(writer, sheet_name='Cadastro_Individual', index=False)
                            buf_ind.seek(0)
                            st.download_button(
                                "📥 Exportar relatório individual (.xlsx)",
                                data=buf_ind,
                                file_name=f"relatorio_{_sanitize_key(normalize_name(selected_benef))[:50]}.xlsx",
                                mime="application/vnd.ms-excel"
                            )

        # ---------------------------
        # Renderiza todas as abas
        # ---------------------------
        for i, tab_name in enumerate(tabs):
            if tab_name == "Busca":
                render_busca(i)
            else:
                with tab_objects[i]:
                    st.subheader(tab_name)
                    st.write("Conteúdo da aba ainda não implementado nesta demo.")  # Placeholder
