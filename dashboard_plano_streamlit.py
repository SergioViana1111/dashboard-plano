# dashboard_plano_streamlit.py
import pandas as pd
import numpy as np
from unidecode import unidecode
import streamlit as st
import matplotlib.pyplot as plt

# ---------------------------
# 1. Configuração do Streamlit
# ---------------------------
st.set_page_config(page_title="Dashboard Plano de Saúde", layout="wide")

st.title("📊 Dashboard de Utilização do Plano de Saúde")

# ---------------------------
# 2. Upload do arquivo
# ---------------------------
uploaded_file = st.file_uploader("Escolha o arquivo .xltx", type="xltx")
if uploaded_file is not None:
    # 2.1 Ler abas
    utilizacao = pd.read_excel(uploaded_file, sheet_name='Utilizacao')
    cadastro = pd.read_excel(uploaded_file, sheet_name='Cadastro')

    # 2.2 Padronizar nomes de colunas
    def clean_cols(df):
        df.columns = [unidecode(col).strip().replace(' ', '_') for col in df.columns]
        return df

    utilizacao = clean_cols(utilizacao)
    cadastro = clean_cols(cadastro)

    # ---------------------------
    # 3. Tratamento de datas
    # ---------------------------
    date_cols_util = ['Data_do_Atendimento', 'Competencia', 'Data_de_Nascimento']
    date_cols_cad = ['Data_de_Nascimento', 'Data_de_Admissao_do_Empregado', 
                     'Data_de_Adesao_ao_Plano', 'Data_de_Cancelamento']

    for col in date_cols_util:
        if col in utilizacao.columns:
            utilizacao[col] = pd.to_datetime(utilizacao[col], errors='coerce')
    for col in date_cols_cad:
        if col in cadastro.columns:
            cadastro[col] = pd.to_datetime(cadastro[col], errors='coerce')

    # ---------------------------
    # 4. Beneficiário: Titular ou Dependente
    # ---------------------------
    if 'Nome_Titular' in utilizacao.columns and 'Nome_do_Associado' in utilizacao.columns:
        utilizacao['Tipo_Beneficiario'] = np.where(
            utilizacao['Nome_Titular'] == utilizacao['Nome_do_Associado'],
            'Titular',
            'Dependente'
        )
    else:
        utilizacao['Tipo_Beneficiario'] = 'Desconhecido'

    # ---------------------------
    # 5. KPIs
    # ---------------------------
    st.subheader("📌 KPIs")
    custo_total = utilizacao['Valor'].sum()
    st.metric("Custo Total (R$)", f"{custo_total:,.2f}")

    custo_por_beneficiario = utilizacao.groupby('Nome_do_Associado')['Valor'].sum().sort_values(ascending=False)
    custo_por_tipo = utilizacao.groupby('Grupo_Tipo_de_Atendimento')['Valor'].sum().sort_values(ascending=False)

    st.write("**Top 10 beneficiários por custo:**")
    st.dataframe(custo_por_beneficiario.head(10))

    st.write("**Custo por tipo de atendimento:**")
    st.dataframe(custo_por_tipo)

    # ---------------------------
    # 6. Evolução Mensal
    # ---------------------------
    if 'Data_do_Atendimento' in utilizacao.columns:
        utilizacao['Mes_Ano'] = utilizacao['Data_do_Atendimento'].dt.to_period('M')
        evolucao_mensal = utilizacao.groupby('Mes_Ano')['Valor'].sum()

        st.subheader("📈 Evolução Mensal do Custo")
        fig, ax = plt.subplots(figsize=(10,4))
        evolucao_mensal.plot(kind='bar', color='skyblue', ax=ax)
        ax.set_ylabel("Valor (R$)")
        ax.set_xlabel("Mês/Ano")
        ax.set_title("Evolução Mensal do Custo")
        plt.xticks(rotation=45)
        st.pyplot(fig)

    # ---------------------------
    # 7. Identificação de CIDs Crônicos
    # ---------------------------
    cids_cronicos = ['E11', 'I10', 'J45']  # exemplo
    if 'Codigo_do_CID' in utilizacao.columns:
        utilizacao['Cronico'] = utilizacao['Codigo_do_CID'].isin(cids_cronicos)
        beneficiarios_cronicos = utilizacao[utilizacao['Cronico']].groupby('Nome_do_Associado')['Valor'].sum()

        st.subheader("🏥 Beneficiários Crônicos")
        st.dataframe(beneficiarios_cronicos)

    # ---------------------------
    # 8. Gráfico por tipo de atendimento
    # ---------------------------
    st.subheader("💡 Custo por Tipo de Atendimento")
    fig2, ax2 = plt.subplots(figsize=(10,4))
    custo_por_tipo.plot(kind='bar', color='orange', ax=ax2)
    ax2.set_ylabel("Valor (R$)")
    ax2.set_xlabel("Tipo de Atendimento")
    ax2.set_title("Custo por Tipo de Atendimento")
    plt.xticks(rotation=45)
    st.pyplot(fig2)

    st.success("✅ Dashboard carregado com sucesso!")
else:
    st.info("Aguardando upload do arquivo .xltx")
