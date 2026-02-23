import os
import json
import json5
import re
import shutil
import requests
from tqdm import tqdm
import hashlib

def get_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()
# ===============================
# НАСТРОЙКИ
# ===============================

MODS_FOLDER = r"C:\Users\Mitchelde\Desktop\json-translator\Xtardew Valley-4399-3-2-0-1735946829"
SERVER_URL = "http://192.168.1.100:8000/translate"  # IP ПК
CREATE_BACKUP = False

# ===============================
# ПРОВЕРКИ
# ===============================

def contains_english(text):
    return re.search(r"[A-Za-z]", text) is not None

def should_skip_key(key):
    return key.lower() in ["action", "target", "logname", "id"]

# ===============================
# БАТЧ ПЕРЕВОД ЧЕРЕЗ СЕРВЕР
# ===============================

def batch_translate(texts):

    if not texts:
        return {}

    try:
        response = requests.post(
            SERVER_URL,
            json={"texts": texts},
            timeout=120
        )

        response.raise_for_status()

        data = response.json()["result"]

        return dict(zip(texts, data))

    except Exception as e:
        print("Server error:", e)
        return {t: t for t in texts}

# ===============================
# SPEAK ОБРАБОТКА
# ===============================

def extract_speak(text):
    pattern = r'speak\s+\w+\s+"([^"]+)"'
    return re.findall(pattern, text)

def replace_speak(text, translations):

    def repl(match):
        original = match.group(1)
        return match.group(0).replace(
            original,
            translations.get(original, original)
        )

    pattern = r'speak\s+\w+\s+"([^"]+)"'
    return re.sub(pattern, repl, text)

# ===============================
# СБОР ТЕКСТОВ
# ===============================

def collect_texts(obj, collected):

    if isinstance(obj, dict):
        for k, v in obj.items():
            if should_skip_key(k):
                continue
            collect_texts(v, collected)

    elif isinstance(obj, list):
        for item in obj:
            collect_texts(item, collected)

    elif isinstance(obj, str):
        if contains_english(obj):
            collected.append(obj)

# ===============================
# ПРИМЕНЕНИЕ ПЕРЕВОДА
# ===============================

def apply_translations(obj, translations):

    if isinstance(obj, dict):
        for k, v in obj.items():
            if should_skip_key(k):
                continue
            obj[k] = apply_translations(v, translations)

    elif isinstance(obj, list):
        return [apply_translations(i, translations) for i in obj]

    elif isinstance(obj, str):

        if "speak " in obj:
            speaks = extract_speak(obj)
            local = {s: translations.get(s, s) for s in speaks}
            return replace_speak(obj, local)

        if obj in translations:
            return translations[obj]

    return obj

# ===============================
# ПОИСК JSON
# ===============================

def find_json_files(folder):
    files = []

    for root, _, filenames in os.walk(folder):
        for f in filenames:
            if f.lower().endswith(".json") and f.lower() != "manifest.json":
                files.append(os.path.join(root, f))

    return files

# ===============================
# ОБРАБОТКА ФАЙЛА
# ===============================

def process_file(filepath):

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json5.load(f)
    except Exception as e:
        print(f"Ошибка в файле {filepath}: {e}")
        return

    texts = []
    collect_texts(data, texts)

    translations = batch_translate(texts)
    new_data = apply_translations(data, translations)

    if CREATE_BACKUP:
        shutil.copy(filepath, filepath + ".backup")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)

# ===============================
# MAIN
# ===============================

def main():

    files = find_json_files(MODS_FOLDER)

    print(f"Найдено JSON файлов: {len(files)}")

    for file in tqdm(files, desc="Перевод файлов"):
        process_file(file)

    print("Перевод завершён.")

if __name__ == "__main__":
    main()