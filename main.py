from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from openai import OpenAI
import pdfplumber
import os
import tempfile

# Inicializa o app FastAPI
app = FastAPI(title="Extrator Equatorial Goiás", version="1.0")

# Cliente OpenAI com a variável de ambiente configurada no Render
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Função para extrair texto de um PDF
def extract_text_from_pdf(pdf_path: str) -> str:
    texto = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            texto += page_text + "\n"
    return texto.strip()

# Endpoint principal para upload e extração
@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    try:
        # Cria um arquivo temporário no container
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        # Extrai o texto do PDF
        texto_extraido = extract_text_from_pdf(tmp_path)

        # Remove o arquivo após leitura
        os.remove(tmp_path)

        # Faz a chamada à API da OpenAI
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um extrator especializado de dados de faturas da Equatorial Goiás. "
                        "Sua tarefa é ler o texto abaixo e retornar um objeto JSON estruturado "
                        "com todos os campos definidos no modelo 'faturaequatorial'."
                    ),
                },
                {
                    "role": "user",
                    "content": texto_extraido,
                },
            ],
            temperature=0.2,
            max_tokens=2500,
        )

        # Retorna a resposta como JSON
        resultado = response.choices[0].message.content
        return JSONResponse(content={"resultado": resultado})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
