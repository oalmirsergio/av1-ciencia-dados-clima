# 🌦️ Monitoramento Climático Brasileiro (AV1)

Este projeto realiza a ingestão, armazenamento e visualização de dados climáticos históricos (simulados) de 7 cidades brasileiras ao longo de 10 anos (2014-2023). Desenvolvido para a disciplina de Ciência de Dados.

---

## 🚀 Como Executar (Requisito de Comando Único)

O projeto foi totalmente conteinerizado utilizando **Docker**. Para subir o banco de dados, gerar os dados e abrir o dashboard, basta rodar o comando abaixo na raiz do projeto:

```bash
docker compose up --build
```

Após o processo de inicialização, o dashboard estará disponível em: **[http://localhost:8501](https://www.google.com/search?q=http://localhost:8501)**

-----

## 🏗️ Arquitetura do Projeto

O sistema é composto por três camadas principais:

1.  **Banco de Dados (PostgreSQL):** Armazenamento relacional com esquema definido (PK/FK).
2.  **Processo Gerador (Python/SQLAlchemy):** Script que gera 10 anos de dados meteorológicos com distribuição realista e **semente fixa** (reprodutibilidade).
3.  **Dashboard (Streamlit/Pandas):** Interface interativa para análise de tendências, médias mensais e comparações entre cidades.

### Estrutura de Arquivos

  - `src/generator.py`: Lógica de criação do banco e geração de dados.
  - `src/app.py`: Interface visual e consultas SQL.
  - `docker-compose.yml`: Orquestração dos serviços.

-----

## 📊 Cidades Monitoradas

O projeto compara climas distintos para garantir análises variadas:

  * **Sudeste:** São Paulo (SP), Rio de Janeiro (RJ)
  * **Centro-Oeste:** Brasília (DF)
  * **Nordeste:** Salvador (BA), Maceió (AL), Recife (PE), Xique-Xique (BA)

-----

## 🛠️ Tecnologias Utilizadas

  * **Linguagem:** Python 3.10
  * **Banco de Dados:** PostgreSQL 15
  * **Bibliotecas Principais:** Pandas, SQLAlchemy, Streamlit, Plotly e Numpy.
  * **Infraestrutura:** Docker & Docker Compose.


-----
