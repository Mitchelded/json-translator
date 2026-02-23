import json
import os
from fastapi import FastAPI
from pydantic import BaseModel
from deep_translator import GoogleTranslator
from typing import List

CACHE_FILE = "server_cache.json"
TARGET_LANG = "ru"
SEP = "___SEP___"

app = FastAPI()
translator = GoogleTranslator(source="auto", target=TARGET_LANG)

# ======================
# CACHE
# ======================

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        CACHE = json.load(f)
else:
    CACHE = {}

def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(CACHE, f, ensure_ascii=False, indent=2)

# ======================
# REQUEST MODEL
# ======================

class TranslateRequest(BaseModel):
    texts: List[str]

# ======================
# TRANSLATE ENDPOINT
# ======================

@app.post("/translate")
def translate(req: TranslateRequest):

    results = []
    to_translate = []
    index_map = []

    # Проверка кэша
    for i, text in enumerate(req.texts):
        if text in CACHE:
            results.append(CACHE[text])
        else:
            results.append(None)
            to_translate.append(text)
            index_map.append(i)

    # Если есть новые строки
    if to_translate:
        combined = SEP.join(to_translate)
        translated = translator.translate(combined)
        split = translated.split(SEP)

        for orig, trans in zip(to_translate, split):
            CACHE[orig] = trans

        for idx, trans in zip(index_map, split):
            results[idx] = trans

        save_cache()

    return {"result": results}