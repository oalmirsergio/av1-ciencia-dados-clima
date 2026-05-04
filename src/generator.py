import os
import time
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

# Semente fixa para reprodutibilidade
np.random.seed(42)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:adminpassword@db:5432/climadb")

def wait_for_db(engine, max_retries=15, delay=2):
    print("⏳ Aguardando o PostgreSQL...")
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print("✅ Banco de dados pronto!")
                return True
        except Exception:
            time.sleep(delay)
    raise ConnectionError("❌ Falha ao ligar à base de dados.")

def setup_database(engine):
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS leituras CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS estacoes CASCADE;"))
        
        conn.execute(text("""
            CREATE TABLE estacoes (
                id SERIAL PRIMARY KEY,
                cidade VARCHAR(100) NOT NULL,
                estado VARCHAR(2) NOT NULL,
                clima_base_temp FLOAT NOT NULL,
                amplitude_termica FLOAT NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE leituras (
                id SERIAL PRIMARY KEY,
                estacao_id INTEGER REFERENCES estacoes(id),
                data_medicao DATE NOT NULL,
                temperatura FLOAT NOT NULL,
                umidade FLOAT NOT NULL,
                precipitacao FLOAT NOT NULL
            );
        """))
        conn.commit()

def generate_and_insert_data(engine):
    print("⚙️ Gerando 10 anos de dados...")
    
    estacoes_data = [
        {"cidade": "São Paulo", "estado": "SP", "clima_base_temp": 20.0, "amplitude_termica": 7.0},
        {"cidade": "Rio de Janeiro", "estado": "RJ", "clima_base_temp": 24.5, "amplitude_termica": 6.0},
        {"cidade": "Brasília", "estado": "DF", "clima_base_temp": 21.0, "amplitude_termica": 5.0},
        {"cidade": "Salvador", "estado": "BA", "clima_base_temp": 26.0, "amplitude_termica": 3.0},
        {"cidade": "Maceió", "estado": "AL", "clima_base_temp": 26.5, "amplitude_termica": 2.5},
        {"cidade": "Recife", "estado": "PE", "clima_base_temp": 27.0, "amplitude_termica": 2.5},
        {"cidade": "Xique-Xique", "estado": "BA", "clima_base_temp": 28.5, "amplitude_termica": 8.0},
    ]
    
    df_estacoes = pd.DataFrame(estacoes_data)
    df_estacoes.to_sql("estacoes", engine, if_exists="append", index=False)
    
    df_estacoes_db = pd.read_sql("SELECT id, cidade, clima_base_temp, amplitude_termica FROM estacoes", engine)
    datas = pd.date_range(start="2014-01-01", end="2023-12-31", freq="D")
    leituras = []
    
    for _, row in df_estacoes_db.iterrows():
        n = len(datas)
        # 1. Sazonalidade ajustada (Pico em Janeiro, Mínima em Julho)
        # Usamos cos(x) onde x=0 em Janeiro para começar no topo
        dias = datas.dayofyear
        sazonalidade = np.cos((dias - 15) * (2 * np.pi / 365.25))
        
        # 2. Ruído de "Frente Fria" (Variações que duram de 5 a 10 dias)
        ruido_longo = np.convolve(np.random.normal(0, 2, n), np.ones(7)/7, mode='same')
        
        # 3. Ruído Diário (Instabilidade comum)
        ruido_diario = np.random.normal(0, 1.2, n)
        
        # 4. Tendência de Aquecimento Global (0.5 graus em 10 anos)
        tendencia = np.linspace(0, 0.5, n)
        
        # Equação Final da Temperatura
        temperatura = row['clima_base_temp'] + (sazonalidade * row['amplitude_termica']) + ruido_longo + ruido_diario + tendencia
        
        # Lógica de Umidade (Inversa à temperatura + ruído)
        umidade = np.clip(100 - (temperatura * 1.5) + np.random.normal(20, 5, n), 20, 100)
        
        # Chuva (Mais provável no verão e com alta umidade)
        prob_chuva = np.where((sazonalidade > 0) & (umidade > 65), 0.3, 0.05)
        precipitacao = np.where(np.random.random(n) < prob_chuva, np.random.exponential(12, n), 0)
        
        df_leituras = pd.DataFrame({
            "estacao_id": row['id'],
            "data_medicao": datas,
            "temperatura": np.round(temperatura, 1),
            "umidade": np.round(umidade, 1),
            "precipitacao": np.round(precipitacao, 1)
        })
        leituras.append(df_leituras)
        
    print("💾 Inserindo dados caóticos e realistas no banco...")
    pd.concat(leituras, ignore_index=True).to_sql("leituras", engine, if_exists="append", index=False, chunksize=10000)
    print("✅ Concluído!")

if __name__ == "__main__":
    engine = create_engine(DATABASE_URL)
    wait_for_db(engine)
    setup_database(engine)
    generate_and_insert_data(engine)
