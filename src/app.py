import os
import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# Importação dinâmica do modelo isolado
try:
    from modelo import treinar_e_prever
except ImportError:
    from src.modelo import treinar_e_prever

st.set_page_config(page_title="Monitorização Climática Preditiva", layout="wide")

API_URL = os.getenv("API_URL", "http://api:8000")

st.title("🌦️ Sistema União de Monitoramento & Previsão Climática (AV2)")
st.markdown("Plataforma desacoplada de dados climáticos brasileiros (2014 - 2023).")

@st.cache_data(ttl=600)
def load_cities():
    try:
        response = requests.get(f"{API_URL}/cidades")
        if response.status_code == 200:
            return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Não foi possível conectar à API de dados: {e}")
    return pd.DataFrame(columns=['id', 'cidade', 'estado'])

df_cidades = load_cities()

if df_cidades.empty:
    st.warning("⚠️ Banco de dados ou API indisponíveis no momento. Verifique a execução dos containers.")
else:
    # --- PAINEL LATERAL DE CONTROLES ---
    st.sidebar.header("⚙️ Painel de Controle Geral")
    ano_selecionado = st.sidebar.slider("Exibição Histórica (Abas 1 e 2):", 2014, 2023, (2014, 2023))
    
    st.sidebar.markdown("---")
    st.sidebar.header("🧠 Configurações de Machine Learning")
    tipo_modelo = st.sidebar.selectbox("Modelo Preditivo:", ["Regressão Linear", "Random Forest"])
    ano_corte = st.sidebar.slider("Ponto de Corte Temporal (t0):", 2017, 2022, 2021)

    tab1, tab2, tab3 = st.tabs(["📊 Análise Individual", "⚔️ Comparativo entre Cidades", "🔮 Inteligência Preditiva"])

    # ==========================================
    # ABA 1: ANÁLISE INDIVIDUAL (Modificada para API)
    # ==========================================
    with tab1:
        cidade_selecionada = st.selectbox("Selecione a Cidade:", df_cidades['cidade'].tolist(), key="sb_ind")
        estacao_id = df_cidades[df_cidades['cidade'] == cidade_selecionada]['id'].values[0]
        
        response = requests.get(f"{API_URL}/dados/{estacao_id}")
        if response.status_code == 200:
            df_ind = pd.DataFrame(response.json())
            df_ind['data_medicao'] = pd.to_datetime(df_ind['data_medicao'])
            df_ind['ano'] = df_ind['data_medicao'].dt.year
            
            df_filtrado = df_ind[(df_ind['ano'] >= ano_selecionado[0]) & (df_ind['ano'] <= ano_selecionado[1])]
            
            st.subheader(f"📈 Tendência de Temperatura — {cidade_selecionada}")
            fig_temp = px.line(df_filtrado, x="data_medicao", y="temperatura", labels={"temperatura": "Temperatura (°C)", "data_medicao": "Data"})
            st.plotly_chart(fig_temp, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🌧️ Precipitação Mensal Média")
                df_filtrado['mes'] = df_filtrado['data_medicao'].dt.month
                df_chuva = df_filtrado.groupby('mes')['precipitacao'].mean().reset_index()
                fig_chuva = px.bar(df_chuva, x="mes", y="precipitacao", labels={"precipitacao": "Chuva (mm)", "mes": "Mês"})
                st.plotly_chart(fig_chuva, use_container_width=True)
            with col2:
                st.subheader("📊 Distribuição de Umidade")
                fig_umidade = px.histogram(df_filtrado, x="umidade", nbins=30, labels={"umidade": "Umidade (%)"})
                st.plotly_chart(fig_umidade, use_container_width=True)

    # ==========================================
    # ABA 2: COMPARATIVO ENTRE CIDADES (Modificada para API)
    # ==========================================
    with tab2:
        cidades_selecionadas = st.multiselect("Selecione as Cidades:", df_cidades['cidade'].tolist(), default=df_cidades['cidade'].tolist()[:2])
        
        if len(cidades_selecionadas) > 0:
            dfs_comp = []
            for city in cidades_selecionadas:
                c_id = df_cidades[df_cidades['cidade'] == city]['id'].values[0]
                res_c = requests.get(f"{API_URL}/dados/{c_id}")
                if res_c.status_code == 200:
                    df_c = pd.DataFrame(res_c.json())
                    df_c['cidade'] = city
                    dfs_comp.append(df_c)
            
            if dfs_comp:
                df_comp = pd.concat(dfs_comp)
                df_comp['data_medicao'] = pd.to_datetime(df_comp['data_medicao'])
                df_comp['ano'] = df_comp['data_medicao'].dt.year
                df_comp_filtrado = df_comp[(df_comp['ano'] >= ano_selecionado[0]) & (df_comp['ano'] <= ano_selecionado[1])]
                
                st.subheader("🌡️ Comparativo de Temperatura no Tempo")
                fig_comp_temp = px.line(df_comp_filtrado, x="data_medicao", y="temperatura", color="cidade")
                st.plotly_chart(fig_comp_temp, use_container_width=True)
                
                st.subheader("📊 Amplitude e Dispersão Térmica")
                fig_comp_box = px.box(df_comp_filtrado, x="cidade", y="temperatura", color="cidade")
                st.plotly_chart(fig_comp_box, use_container_width=True)

    # ==========================================
    # ABA 3: INTELIGÊNCIA PREDITIVA (REQUISITO AV2)
    # ==========================================
    with tab3:
        st.header("🔮 Predição de Séries Temporais")
        cidade_ml = st.selectbox("Selecione a Cidade para Análise Preditiva:", df_cidades['cidade'].tolist(), key="sb_ml")
        estacao_id_ml = df_cidades[df_cidades['cidade'] == cidade_ml]['id'].values[0]
        
        res_ml = requests.get(f"{API_URL}/dados/{estacao_id_ml}")
        if res_ml.status_code == 200:
            df_ml = pd.DataFrame(res_ml.json())
            
            # Dispara o treinamento e teste do modelo em tempo real baseado nos inputs do usuário
            df_res, mae, rmse = treinar_e_prever(df_ml, ano_corte, tipo_modelo)
            
            if df_res is not None:
                st.markdown(f"O modelo preditivo foi treinado com os dados históricos **anteriores ao ano de {ano_corte}** e avaliado de **{ano_corte} até 2023**.")
                
                # Exibição dos indicadores de performance exigidos (MAE, RMSE)
                m1, m2 = st.columns(2)
                with m1:
                    st.metric(label="Erro Médio Absoluto (MAE)", value=f"{mae:.2f} °C")
                with m2:
                    st.metric(label="Raiz do Erro Quadrático Médio (RMSE)", value=f"{rmse:.2f} °C")
                
                # Gráfico comparativo Real vs Previsão
                df_res['data_medicao'] = pd.to_datetime(df_res['data_medicao'])
                
                fig_pred = px.line(
                    df_res, 
                    x="data_medicao", 
                    y=["temperatura", "previsao"],
                    labels={"value": "Temperatura (°C)", "data_medicao": "Data", "variable": "Tipo"},
                    title=f"Análise de Aderência do Modelo — {tipo_modelo} (Corte t0: {ano_corte})"
                )
                
                # Customização visual: deixa a linha de previsão tracejada para melhor diferenciação
                fig_pred.update_traces(patch={"line": {"dash": "dash"}}, selector={"name": "previsao"})
                st.plotly_chart(fig_pred, use_container_width=True)
                
                st.info("💡 **Dica para a apresentação:** Como o processo gerador de dados simula uma oscilação senoidal perfeita de temperatura, o algoritmo de Regressão com variáveis senoidais consegue reproduzir e generalizar a curva perfeitamente, explicando a alta performance observada no MAE.")
