# Extrator Equatorial Goiás (FastAPI)

## Objetivo
Serviço de extração inteligente de dados de faturas Equatorial Goiás, com IA (GPT-5) e integração direta com Bubble.

## Deploy no Render
1. Crie um repositório no GitHub.
2. Envie todos os arquivos desta pasta.
3. Vá para https://render.com → New + → Web Service → conecte ao GitHub.
4. Configure:
   - Environment: Python 3.12
   - Build Command: pip install -r requirements.txt
   - Start Command: uvicorn main:app --host 0.0.0.0 --port 10000
   - Variável: OPENAI_API_KEY = sua chave da OpenAI

Endpoint:  
https://extrator-equatorial-v1.onrender.com/extract
