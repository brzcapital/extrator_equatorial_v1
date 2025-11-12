from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import pdfplumber, tempfile, os
from openai import OpenAI

app = FastAPI(title="Extrator Equatorial Goiás", version="1.0")

# ✅ Chave segura via variável de ambiente (defina no Render)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("A variável OPENAI_API_KEY não está configurada no ambiente Render.")

client = OpenAI(api_key=api_key)

def extract_text_from_pdf(pdf_path):
    """Extrai texto bruto do PDF"""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text.strip()

@app.post("/extract")
async def extract_data(file: UploadFile = File(...)):
    """Extrai dados estruturados da fatura Equatorial Goiás"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        texto_extraido = extract_text_from_pdf(tmp_path)

        prompt = f"""
        Você é um extrator de dados de faturas de energia elétrica da Equatorial Goiás.
        Leia o texto abaixo e retorne um objeto JSON estruturado contendo todos os campos reconhecidos.
        Retorne apenas o JSON.
        Texto da fatura:
        {texto_extraido}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um especialista em leitura de faturas de energia elétrica."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )

        resultado = response.choices[0].message.content
        return JSONResponse(content={"resultado": resultado})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/health")
async def health_check():
    """Verifica se o servidor está ativo"""
    return {"status": "ok", "message": "API online e funcional"}
