import os
import re
import json
from datetime import datetime
from typing import Optional, List

import pdfplumber
from fastapi import FastAPI, File, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from openai import OpenAI

# ==============================
# Configurações básicas
# ==============================
APP_NAME = "Extrator Equatorial Goiás"
APP_VERSION = "1.1"

# OpenAI Client (API nova)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = client.chat.completions.create(...)

# Carrega prompt base uma vez
with open("prompt_equatorial_v1.txt", "r", encoding="utf-8") as f:
    BASE_PROMPT = f.read()

app = FastAPI(title=APP_NAME, version=APP_VERSION)

# ==============================
# CORS (ajuste a origem do seu Bubble)
# ==============================
BUBBLE_ORIGIN = os.getenv("BUBBLE_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[BUBBLE_ORIGIN] if BUBBLE_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# Utilidades
# ==============================
DATE_BR_REGEX = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")

def br_date_to_iso(text: str) -> str:
    """Converte datas dd/mm/aaaa para aaaa-mm-dd dentro de um texto."""
    def _repl(m):
        d, mth, y = m.groups()
        try:
            return datetime(int(y), int(mth), int(d)).strftime("%Y-%m-%d")
        except Exception:
            return m.group(0)
    return DATE_BR_REGEX.sub(_repl, text)

def normalize_numbers_in_json(obj):
    """
    Converte strings numéricas BR '1.234,56' -> 1234.56 e '1.234' -> 1234.
    Mantém strings não numéricas como estão.
    """
    def to_num(val: str):
        s = val.strip()
        # se tiver vírgula como decimal, converte
        if re.search(r"\d,\d", s):
            s = s.replace(".", "").replace(",", ".")
        else:
            # remove separador de milhar isolado
            s = s.replace(",", "")
        # tenta float
        try:
            return float(s)
        except Exception:
            return val

    if isinstance(obj, dict):
        return {k: normalize_numbers_in_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [normalize_numbers_in_json(v) for v in obj]
    elif isinstance(obj, str):
        # tenta interpretar como número
        return to_num(obj)
    else:
        return obj

def clean_possible_code_fences(s: str) -> str:
    s = s.strip()
    s = s.replace("```json", "").replace("```", "")
    return s.strip()

def extract_text_from_pdf(path: str, first_page_only: bool = False, page_limit: Optional[int] = None) -> str:
    text_parts: List[str] = []
    with pdfplumber.open(path) as pdf:
        pages = pdf.pages
        if first_page_only:
            pages = pages[:1]
        elif page_limit:
            pages = pages[:page_limit]
        for p in pages:
            t = p.extract_text() or ""
            text_parts.append(t)
    # Normaliza datas BR -> ISO para ajudar o modelo
    full_text = "\n".join(text_parts)
    full_text = br_date_to_iso(full_text)
    return full_text

# ==============================
# Endpoints de diagnóstico
# ==============================
@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"

@app.get("/version", response_class=PlainTextResponse)
def version():
    return f"{APP_NAME} v{APP_VERSION}"

# ==============================
# Endpoint principal
# ==============================
@app.post("/extract")
async def extract_data(
    file: UploadFile = File(...),
    first_page_only: bool = Query(True, description="Extrair somente a primeira página para economizar tokens"),
    page_limit: Optional[int] = Query(None, ge=1, le=10, description="Limite opcional de páginas (se first_page_only=False)")
):
    try:
        # Salva arquivo temporariamente
        tmp_path = f"/tmp/{file.filename}"
        with open(tmp_path, "wb") as f_out:
            f_out.write(await file.read())

        # Extrai texto
        text = extract_text_from_pdf(tmp_path, first_page_only=first_page_only, page_limit=page_limit)

        # Monta mensagens
        messages = [
            {"role": "system", "content": BASE_PROMPT},
            {"role": "user", "content": text[:120000]}  # corta hard-limit p/ evitar excesso (120k chars)
        ]

        # Chamada ao modelo (API nova) com timeout
        resp = client.chat.completions.create(
            model="gpt-5",
            messages=messages,
            temperature=0.2,
            max_tokens=2500,
            timeout=60
        )

        raw = (resp.choices[0].message.content or "").strip()
        raw = clean_possible_code_fences(raw)

        # Garante JSON
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # tentativa adicional: remover vírgulas penduradas antes de fechar objetos/listas
            raw2 = re.sub(r",\s*([}\]])", r"\1", raw)
            data = json.loads(raw2)

        # Pós-processamento: normalizar números e datas dentro do JSON
        data = normalize_numbers_in_json(data)

        # Metadados úteis
        data["_meta"] = {
            "fonte_arquivo": file.filename,
            "data_processamento": datetime.utcnow().isoformat() + "Z",
            "first_page_only": first_page_only,
            "page_limit": page_limit
        }

        return JSONResponse(content=data, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
