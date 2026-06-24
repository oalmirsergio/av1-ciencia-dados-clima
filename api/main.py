import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import pandas as pd

app = FastAPI(title="API de Ingestão e Monitoramento Climático - AV2")

# Libera o acesso para o container do Streamlit consumir os dados
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:adminpassword@db:5432/climadb")
engine = create_engine(DATABASE_URL)

@app.get("/health")
def health_check():
    """Rota obrigatória de monitoramento de saúde do ecossistema"""
    return {"status": "ok"}

@app.get("/cidades")
def get_cidades():
    """Retorna todas as estações cadastradas no banco para alimentar os seletores"""
    try:
        with engine.connect() as conn:
            df = pd.read_sql("SELECT id, cidade, estado FROM estacoes ORDER BY cidade", conn)
            return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no banco de dados: {str(e)}")

@app.get("/dados/{estacao_id}")
def get_dados_estacao(estacao_id: int):
    """Retorna o histórico meteorológico completo da estação selecionada"""
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT data_medicao, temperatura, umidade, precipitacao 
                FROM leituras 
                WHERE estacao_id = :estacao_id 
                ORDER BY data_medicao
            """)
            df = pd.read_sql(query, conn, params={"estacao_id": estacao_id})
            if df.empty:
                raise HTTPException(status_code=404, detail="Nenhum dado encontrado para esta estação.")
            
            # Converte data para string para serialização JSON correta
            df['data_medicao'] = df['data_medicao'].astype(str)
            return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar medições: {str(e)}")