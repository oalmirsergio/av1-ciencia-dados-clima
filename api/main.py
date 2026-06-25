import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import pandas as pd
from typing import Optional

app = FastAPI(title="API de Ingestão e Monitoramento Climático - AV2")

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

@app.get("/resumo")
def get_resumo(ano_inicio: Optional[int] = Query(None), ano_fim: Optional[int] = Query(None)):
    """Retorna estatísticas agregadas por cidade, com filtro opcional de período."""
    try:
        with engine.connect() as conn:
            query_str = """
                SELECT e.cidade, e.estado, 
                       AVG(l.temperatura) as media_temperatura,
                       AVG(l.umidade) as media_umidade,
                       SUM(l.precipitacao) as total_precipitacao
                FROM leituras l
                JOIN estacoes e ON l.estacao_id = e.id
                WHERE 1=1
            """
            params = {}
            if ano_inicio is not None:
                query_str += " AND EXTRACT(YEAR FROM l.data_medicao) >= :ano_inicio"
                params["ano_inicio"] = ano_inicio
            if ano_fim is not None:
                query_str += " AND EXTRACT(YEAR FROM l.data_medicao) <= :ano_fim"
                params["ano_fim"] = ano_fim
                
            query_str += " GROUP BY e.cidade, e.estado ORDER BY e.cidade"
            
            df = pd.read_sql(text(query_str), conn, params=params)
            return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar resumo: {str(e)}")

@app.get("/dados/{estacao_id}")
def get_dados_estacao(estacao_id: int, ano_inicio: Optional[int] = Query(None), ano_fim: Optional[int] = Query(None)):
    """Retorna o histórico da estação com filtro de período via query params."""
    try:
        with engine.connect() as conn:
            query_str = """
                SELECT data_medicao, temperatura, umidade, precipitacao 
                FROM leituras 
                WHERE estacao_id = :estacao_id 
            """
            params = {"estacao_id": estacao_id}
            
            if ano_inicio is not None:
                query_str += " AND EXTRACT(YEAR FROM data_medicao) >= :ano_inicio"
                params["ano_inicio"] = ano_inicio
            if ano_fim is not None:
                query_str += " AND EXTRACT(YEAR FROM data_medicao) <= :ano_fim"
                params["ano_fim"] = ano_fim
                
            query_str += " ORDER BY data_medicao"
            
            df = pd.read_sql(text(query_str), conn, params=params)
            
            if df.empty:
                raise HTTPException(status_code=404, detail="Nenhum dado encontrado para esta estação no período.")
            
            df['data_medicao'] = df['data_medicao'].astype(str)
            return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar medições: {str(e)}")