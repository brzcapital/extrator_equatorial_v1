from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from openai import OpenAI
import pdfplumber
import tempfile
import os

app = FastAPI(title="Extrator Equatorial Goiás", version="1.0")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text_from_pdf(pdf_path: str) -> str:
    texto = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texto += (page.extract_text() or "") + "\n"
    return texto.strip()

@app.get("/")
async def root():
    return {"status": "ok", "mensagem": "API Extrator Equatorial Goiás ativa 🚀"}

@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    try:
        # Salva PDF temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        # Extrai o texto
        texto_extraido = extract_text_from_pdf(tmp_path)
        os.remove(tmp_path)

        # Envia ao modelo
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um extrator especializado de dados de faturas da Equatorial Goiás. "
                        "Leia o texto e retorne um único objeto JSON estruturado com todos os campos esperados."
                    ),
                },
                {"role": "user", "content": texto_extraido},
            ],
            temperature=0.2,
            max_tokens=2000,
        )

        resultado = response.choices[0].message.content
        return JSONResponse(content={"resultado": resultado})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
