FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

EXPOSE 8501

# Executa o gerador (que espera o banco ligar) e depois o dashboard
CMD ["sh", "-c", "python src/generator.py && streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0"]
