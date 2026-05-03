import os
import time
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

# Semente fixa para total reprodutibilidade
np.random.seed(42)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:adminpassword@localhost:5432/climdb")

def wait_for_db(engine, max_retries=15, delay=2):
    print("⏳ A aguardar o PostgreSQL...")
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print("✅ Base de dados pronta!")
                return True
        except Exception:
            time.sleep(delay)
    raise ConnectionError("❌ Falha ao ligar à base de dados.")

def setup_database(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS estacoes (
                id SERIAL PRIMARY KEY,
                cidade VARCHAR(100) NOT NULL,
                estado VARCHAR(2) NOT NULL,
                clima_base_temp FLOAT NOT NULL,
                amplitude_termica FLOAT NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS leituras (
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
    with engine.connect() as conn:
        if conn.execute(text("SELECT COUNT(*) FROM estacoes")).scalar() > 0:
            print("⏭️ Os dados já existem. A saltar a geração.")
            return

    print("⚙️ A gerar 10 anos de dados climáticos para 7 cidades...")
    estacoes_data = [
        {"cidade": "São Paulo", "estado": "SP", "clima_base_temp": 20.0, "amplitude_termica": 6.0},
        {"cidade": "Rio de Janeiro", "estado": "RJ", "clima_base_temp": 24.0, "amplitude_termica": 5.0},
        {"cidade": "Brasília", "estado": "DF", "clima_base_temp": 21.0, "amplitude_termica": 7.0},
        {"cidade": "Salvador", "estado": "BA", "clima_base_temp": 25.0, "amplitude_termica": 3.0},
        {"cidade": "Maceió", "estado": "AL", "clima_base_temp": 26.0, "amplitude_termica": 2.5},
        {"cidade": "Recife", "estado": "PE", "clima_base_temp": 26.5, "amplitude_termica": 2.5},
        {"cidade": "Xique-Xique", "estado": "BA", "clima_base_temp": 28.0, "amplitude_termica": 8.0},
    ]
    
    df_estacoes = pd.DataFrame(estacoes_data)
    df_estacoes.to_sql("estacoes", engine, if_exists="append", index=False)
    
    df_estacoes_db = pd.read_sql("SELECT id, cidade, clima_base_temp, amplitude_termica FROM estacoes", engine)
    datas = pd.date_range(start="2014-01-01", end="2023-12-31", freq="D") # 10 anos
    leituras = []
    
    for _, row in df_estacoes_db.iterrows():
        estacao_id, base_t, amp_t = row['id'], row['clima_base_temp'], row['amplitude_termica']
        
        # Sazonalidade realista usando funções trigonométricas
        sazonalidade = np.sin((datas.dayofyear - 1) * (2 * np.pi / 365.25))
        temperatura = base_t + (sazonalidade * amp_t) + np.random.normal(0, 1.5, len(datas))
        
        umidade = np.clip(80 - (temperatura - base_t) * 2 + np.random.normal(0, 5, len(datas)), 20, 100)
        prob_chuva = np.where(umidade > 70, 0.4, 0.1)
        precipitacao = np.where(np.random.random(len(datas)) < prob_chuva, np.random.exponential(15, len(datas)), 0)
        
        df_leituras = pd.DataFrame({
            "estacao_id": estacao_id, "data_medicao": datas,
            "temperatura": np.round(temperatura, 1), "umidade": np.round(umidade, 1),
            "precipitacao": np.round(precipitacao, 1)
        })
        leituras.append(df_leituras)
        
    print("💾 A guardar os registos na base de dados...")
    pd.concat(leituras, ignore_index=True).to_sql("leituras", engine, if_exists="append", index=False, chunksize=10000)
    print("✅ Dados guardados com sucesso!")

if __name__ == "__main__":
    engine = create_engine(DATABASE_URL)
    wait_for_db(engine)
    setup_database(engine)
    generate_and_insert_data(engine)
