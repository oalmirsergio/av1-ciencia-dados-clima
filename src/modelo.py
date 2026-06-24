import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

def treinar_e_prever(df: pd.DataFrame, ano_corte: int, tipo_modelo: str):
    """
    Realiza engenharia de atributos temporais, divide os dados com base em t0,
    treina o modelo e calcula as métricas MAE e RMSE do período de validação.
    """
    df = df.copy()
    df['data_medicao'] = pd.to_datetime(df['data_medicao'])
    df['ano'] = df['data_medicao'].dt.year
    df['dia_ano'] = df['data_medicao'].dt.dayofyear
    
    # Engenharia de Atributos Cíclicos para capturar a sazonalidade exata do generator.py
    df['sin_dia_ano'] = np.sin(2 * np.pi * df['dia_ano'] / 365.25)
    df['cos_dia_ano'] = np.cos(2 * np.pi * df['dia_ano'] / 365.25)
    
    features = ['ano', 'sin_dia_ano', 'cos_dia_ano']
    
    # Divisão de Treino e Teste com base no parâmetro t0 (ano_corte)
    df_treino = df[df['ano'] < ano_corte]
    df_teste = df[df['ano'] >= ano_corte]
    
    if df_treino.empty or df_teste.empty:
        return None, 0, 0
    
    X_treino = df_treino[features]
    y_treino = df_treino['temperatura']
    X_teste = df_teste[features]
    y_teste = df_teste['temperatura']
    
    # Escolha e treinamento do algoritmo
    if tipo_modelo == "Regressão Linear":
        model = LinearRegression()
    else:
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        
    model.fit(X_treino, y_treino)
    
    # Geração de Previsões no conjunto de teste
    previsoes = model.predict(X_teste)
    
    # Cálculo das métricas de erro exigidas pelo professor
    mae = mean_absolute_error(y_teste, previsoes)
    rmse = np.sqrt(mean_squared_error(y_teste, previsoes))
    
    # Estrutura o DataFrame de saída mapeando o passado e o futuro previsto
    df_resultado = df.copy()
    df_resultado['previsao'] = np.nan
    df_resultado.loc[df_resultado['ano'] >= ano_corte, 'previsao'] = previsoes
    
    return df_resultado, mae, rmse