from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import pdfplumber
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("brzcapital@gmail.com_wEH1luD5OlAmE0IkNAVlTiUR2ytUnCcfdEkgFxDWEJFYIQsuZxrJkQP1Qeo0ofZJ"))

import os
from datetime import datetime

app = FastAPI(title="Extrator Equatorial Goiás", version="1.0")

openai.api_key = os.getenv("brzcapital@gmail.com_wEH1luD5OlAmE0IkNAVlTiUR2ytUnCcfdEkgFxDWEJFYIQsuZxrJkQP1Qeo0ofZJ")

def extract_text_from_pdf(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

@app.post("/extract")
async def extract_data(file: UploadFile = File(...)):
    try:
        file_path = f"/tmp/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        text = extract_text_from_pdf(file_path)

        with open("prompt_equatorial_v1.txt", "r", encoding="utf-8") as f:
            base_prompt = f.read()

        messages = [
            {"role": "system", "content": base_prompt},
            {"role": "user", "content": text}
        ]

        response = client.chat.completions.create(
            model="gpt-5",
            messages=messages,
            temperature=0.2,
            max_tokens=2500
        )

        raw_output = response.choices[0].message.content.strip()

        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError:
            cleaned = raw_output.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)

        data["data_processamento"] = datetime.now().isoformat()
        data["fonte"] = file.filename

        return JSONResponse(content=data)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
