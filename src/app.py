import os
import streamlit as st
import pandas as pd
import plotly.express as px
import requests

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
    
    # Consumindo a rota /resumo exigida pelo professor
    try:
        res_resumo = requests.get(f"{API_URL}/resumo?ano_inicio={ano_selecionado[0]}&ano_fim={ano_selecionado[1]}")
        if res_resumo.status_code == 200:
            df_resumo = pd.DataFrame(res_resumo.json())
            if not df_resumo.empty:
                media_nac = df_resumo['media_temperatura'].mean()
                st.sidebar.metric("Termômetro Nacional", f"{media_nac:.1f} °C", help="Média agregada da rota /resumo")
    except:
        pass
    
    st.sidebar.markdown("---")
    st.sidebar.header("🧠 Configurações de Machine Learning")
    tipo_modelo = st.sidebar.selectbox("Modelo Preditivo:", ["Regressão Linear", "Random Forest"])
    ano_corte = st.sidebar.slider("Ponto de Corte Temporal (t0):", 2017, 2022, 2021)

    tab1, tab2, tab3 = st.tabs(["📊 Análise Individual", "⚔️ Comparativo", "🔮 Inteligência Preditiva"])

    # ABA 1: ANÁLISE INDIVIDUAL
    with tab1:
        cidade_selecionada = st.selectbox("Selecione a Cidade:", df_cidades['cidade'].tolist(), key="sb_ind")
        estacao_id = df_cidades[df_cidades['cidade'] == cidade_selecionada]['id'].values[0]
        
        # Filtro via Query Params direto na API
        url_dados = f"{API_URL}/dados/{estacao_id}?ano_inicio={ano_selecionado[0]}&ano_fim={ano_selecionado[1]}"
        response = requests.get(url_dados)
        
        if response.status_code == 200:
            df_ind = pd.DataFrame(response.json())
            df_ind['data_medicao'] = pd.to_datetime(df_ind['data_medicao'])
            
            st.subheader(f"📈 Tendência de Temperatura — {cidade_selecionada}")
            fig_temp = px.line(df_ind, x="data_medicao", y="temperatura", labels={"temperatura": "Temperatura (°C)", "data_medicao": "Data"})
            st.plotly_chart(fig_temp, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🌧️ Precipitação Mensal Média")
                df_ind['mes'] = df_ind['data_medicao'].dt.month
                df_chuva = df_ind.groupby('mes')['precipitacao'].mean().reset_index()
                fig_chuva = px.bar(df_chuva, x="mes", y="precipitacao", labels={"precipitacao": "Chuva (mm)", "mes": "Mês"})
                st.plotly_chart(fig_chuva, use_container_width=True)
            with col2:
                st.subheader("📊 Distribuição de Umidade")
                fig_umidade = px.histogram(df_ind, x="umidade", nbins=30, labels={"umidade": "Umidade (%)"})
                st.plotly_chart(fig_umidade, use_container_width=True)

    # ABA 2: COMPARATIVO
    with tab2:
        cidades_selecionadas = st.multiselect("Selecione as Cidades:", df_cidades['cidade'].tolist(), default=df_cidades['cidade'].tolist()[:2])
        
        if len(cidades_selecionadas) > 0:
            dfs_comp = []
            for city in cidades_selecionadas:
                c_id = df_cidades[df_cidades['cidade'] == city]['id'].values[0]
                res_c = requests.get(f"{API_URL}/dados/{c_id}?ano_inicio={ano_selecionado[0]}&ano_fim={ano_selecionado[1]}")
                if res_c.status_code == 200:
                    df_c = pd.DataFrame(res_c.json())
                    df_c['cidade'] = city
                    dfs_comp.append(df_c)
            
            if dfs_comp:
                df_comp = pd.concat(dfs_comp)
                df_comp['data_medicao'] = pd.to_datetime(df_comp['data_medicao'])
                
                st.subheader("🌡️ Comparativo no Tempo")
                fig_comp_temp = px.line(df_comp, x="data_medicao", y="temperatura", color="cidade")
                st.plotly_chart(fig_comp_temp, use_container_width=True)
                
                st.subheader("📊 Amplitude e Dispersão Térmica")
                fig_comp_box = px.box(df_comp, x="cidade", y="temperatura", color="cidade")
                st.plotly_chart(fig_comp_box, use_container_width=True)

    # ABA 3: INTELIGÊNCIA PREDITIVA
    with tab3:
        st.header("🔮 Predição de Séries Temporais")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            cidade_ml = st.selectbox("Selecione a Cidade:", df_cidades['cidade'].tolist(), key="sb_ml")
        with col_m2:
            variavel_alvo = st.selectbox("Variável a Prever:", ["temperatura", "umidade", "precipitacao"])

        estacao_id_ml = df_cidades[df_cidades['cidade'] == cidade_ml]['id'].values[0]
        
        # Pega a base cheia (sem filtro de ano) para o modelo treinar/testar no t0
        res_ml = requests.get(f"{API_URL}/dados/{estacao_id_ml}")
        if res_ml.status_code == 200:
            df_ml = pd.DataFrame(res_ml.json())
            
            df_res, mae, rmse = treinar_e_prever(df_ml, ano_corte, tipo_modelo, variavel_alvo)
            
            if df_res is not None:
                st.markdown(f"O modelo preditivo previu **{variavel_alvo}** usando dados anteriores a **{ano_corte}** para treino.")
                
                m1, m2 = st.columns(2)
                with m1:
                    st.metric(label="Erro Médio Absoluto (MAE)", value=f"{mae:.2f}")
                with m2:
                    st.metric(label="Raiz do Erro Quadrático Médio (RMSE)", value=f"{rmse:.2f}")
                
                df_res['data_medicao'] = pd.to_datetime(df_res['data_medicao'])
                
                fig_pred = px.line(
                    df_res, 
                    x="data_medicao", 
                    y=[variavel_alvo, "previsao"],
                    labels={"value": variavel_alvo.capitalize(), "data_medicao": "Data", "variable": "Tipo"},
                    title=f"Aderência do Modelo — {tipo_modelo} (Corte t0: {ano_corte})"
                )
                
                fig_pred.update_traces(patch={"line": {"dash": "dash"}}, selector={"name": "previsao"})
                st.plotly_chart(fig_pred, use_container_width=True)