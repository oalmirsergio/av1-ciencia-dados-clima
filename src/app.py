import os
import pandas as pd
import streamlit as st
import plotly.express as px
from sqlalchemy import create_engine

st.set_page_config(page_title="Monitorização Climática", layout="wide")

# DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:adminpassword@localhost:5432/climdb")
engine = create_engine(DATABASE_URL)

st.title("🌦️ Análise de Dados Climáticos (2014 - 2023)")
st.markdown("Projeto com PostgreSQL, SQLAlchemy e Streamlit.")

@st.cache_data(ttl=600)
def load_cities():
    with engine.connect() as conn:
        return pd.read_sql("SELECT id, cidade, estado FROM estacoes ORDER BY cidade", conn)

df_cidades = load_cities()

# --- SIDEBAR (Filtros que afetam ambas as abas) ---
st.sidebar.header("Filtros Interativos")
ano_selecionado = st.sidebar.slider("Selecione o Ano:", 2014, 2023, (2014, 2023))

# Criação das Abas
tab1, tab2 = st.tabs(["📊 Análise Individual", "⚔️ Comparativo entre Cidades"])

# ==========================================
# ABA 1: ANÁLISE INDIVIDUAL
# ==========================================
with tab1:
    cidade_selecionada = st.selectbox("Selecione a Cidade:", df_cidades['cidade'].tolist())
    estacao_id = df_cidades[df_cidades['cidade'] == cidade_selecionada]['id'].iloc[0]

    # Consulta SQL original
    query = f"""
        SELECT l.data_medicao, l.temperatura, l.umidade, l.precipitacao, e.cidade
        FROM leituras l
        JOIN estacoes e ON l.estacao_id = e.id
        WHERE e.id = {estacao_id}
        AND EXTRACT(YEAR FROM l.data_medicao) BETWEEN {ano_selecionado[0]} AND {ano_selecionado[1]}
        ORDER BY l.data_medicao
    """

    with engine.connect() as conn:
        df_dados = pd.read_sql(query, conn)

    st.subheader(f"Resumo Histórico: {cidade_selecionada}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Máxima Histórica", f"{df_dados['temperatura'].max():.1f}°C")
    col2.metric("Mínima Histórica", f"{df_dados['temperatura'].min():.1f}°C")
    col3.metric("Pico de Precipitação (1 dia)", f"{df_dados['precipitacao'].max():.1f}mm")

    st.divider()

    # Gráfico 1: Linhas (Série Temporal)
    st.subheader("Evolução Temporal da Temperatura")
    fig_linha = px.line(df_dados, x="data_medicao", y="temperatura", color_discrete_sequence=["#FF5733"])
    st.plotly_chart(fig_linha, use_container_width=True)

    colA, colB = st.columns(2)
    with colA:
        # Gráfico 2: Barras (Agregação de Média Mensal)
        st.subheader("Sazonalidade: Média de Chuva por Mês")
        df_dados['mes'] = pd.to_datetime(df_dados['data_medicao']).dt.month
        chuva_mensal = df_dados.groupby('mes')['precipitacao'].mean().reset_index()
        fig_barra = px.bar(chuva_mensal, x="mes", y="precipitacao", color_discrete_sequence=["#33C1FF"])
        st.plotly_chart(fig_barra, use_container_width=True)

    with colB:
        # Gráfico 3: Histograma (Distribuição)
        st.subheader("Distribuição da Umidade")
        fig_hist = px.histogram(df_dados, x="umidade", nbins=30, color_discrete_sequence=["#33FF57"])
        st.plotly_chart(fig_hist, use_container_width=True)

# ==========================================
# ABA 2: COMPARATIVO
# ==========================================
with tab2:
    st.subheader("⚔️ Comparação Direta entre Cidades")
    
    cidades_comparar = st.multiselect(
        "Selecione as cidades para comparar:",
        options=df_cidades['cidade'].tolist(),
        default=df_cidades['cidade'].tolist()[:2] # Pega as duas primeiras como padrão
    )

    if cidades_comparar:
        ids_comparar = df_cidades[df_cidades['cidade'].isin(cidades_comparar)]['id'].tolist()
        ids_filtro = ",".join(map(str, ids_comparar))

        # Query comparativa usando o operador IN
        query_comp = f"""
            SELECT l.data_medicao, l.temperatura, l.precipitacao, e.cidade
            FROM leituras l
            JOIN estacoes e ON l.estacao_id = e.id
            WHERE e.id IN ({ids_filtro})
            AND EXTRACT(YEAR FROM l.data_medicao) BETWEEN {ano_selecionado[0]} AND {ano_selecionado[1]}
            ORDER BY l.data_medicao
        """

        with engine.connect() as conn:
            df_comp = pd.read_sql(query_comp, conn)

        # Gráfico Comparativo de Temperatura
        st.subheader("🌡️ Comparativo de Temperatura")
        fig_comp_temp = px.line(
            df_comp, 
            x="data_medicao", 
            y="temperatura", 
            color="cidade",
            labels={"temperatura": "Temperatura (°C)", "data_medicao": "Data"}
        )
        st.plotly_chart(fig_comp_temp, use_container_width=True)

        # Gráfico Comparativo de Amplitude (Boxplot)
        st.subheader("📊 Amplitude e Dispersão Térmica")
        fig_comp_box = px.box(
            df_comp, 
            x="cidade", 
            y="temperatura", 
            color="cidade",
            title="Variação Térmica por Cidade (Boxplot)"
        )
        st.plotly_chart(fig_comp_box, use_container_width=True)

        # Tabela Comparativa de Médias
        st.subheader("📋 Resumo Médio do Período")
        df_resumo = df_comp.groupby('cidade')[['temperatura', 'precipitacao']].mean().reset_index()
        df_resumo.columns = ['Cidade', 'Temp. Média (°C)', 'Chuva Média (mm)']
        st.dataframe(df_resumo.style.format(precision=1), use_container_width=True)
    else:
        st.info("Selecione pelo menos uma cidade para habilitar a comparação.")
