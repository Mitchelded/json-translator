import os
import json
import json5
import re
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator
from tqdm import tqdm

# ===============================
# НАСТРОЙКИ
# ===============================

MODS_FOLDER = r"C:\Users\Mitchelde\Desktop\json-translator\Xtardew Valley-4399-3-2-0-1735946829"
TARGET_LANG = "ru"
THREADS = 4
CREATE_BACKUP = True
CACHE_FILE = "translation_cache.json"
LOG_FILE = "translation_errors.log"

translator = GoogleTranslator(source="auto", target=TARGET_LANG)
lock = threading.Lock()

# ===============================
# КЭШ
# ===============================

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        CACHE = json.load(f)
else:
    CACHE = {}

def save_cache():
    with lock:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(CACHE, f, ensure_ascii=False, indent=2)

# ===============================
# ЛОГ
# ===============================

def log_error(path, error):
    with lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\nFILE: {path}\nERROR: {error}\n")

# ===============================
# ПРОВЕРКИ
# ===============================

def contains_english(text):
    return re.search(r"[A-Za-z]", text) is not None

def should_skip_key(key):
    key = key.lower()
    return key in ["action", "target", "logname", "id"]

# ===============================
# БАТЧ ПЕРЕВОД
# ===============================

def batch_translate(texts):

    results = {}
    untranslated = []

    for t in texts:
        if t in CACHE:
            results[t] = CACHE[t]
        elif not contains_english(t):
            results[t] = t
        else:
            untranslated.append(t)

    if untranslated:
        try:
            combined = "\n<<<SEP>>>\n".join(untranslated)
            translated = translator.translate(combined)
            split = translated.split("\n<<<SEP>>>\n")

            for orig, trans in zip(untranslated, split):
                CACHE[orig] = trans
                results[orig] = trans

        except Exception as e:
            for t in untranslated:
                log_error("BATCH", str(e))
                results[t] = t

    return results

# ===============================
# EVENTS (перевод speak "")
# ===============================

def extract_speak(text):
    pattern = r'speak\s+\w+\s+"([^"]+)"'
    return re.findall(pattern, text)

def replace_speak(text, translations):
    def repl(match):
        original = match.group(1)
        return match.group(0).replace(original, translations.get(original, original))
    pattern = r'speak\s+\w+\s+"([^"]+)"'
    return re.sub(pattern, repl, text)

# ===============================
# РЕКУРСИВНАЯ ОБРАБОТКА JSON
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

def apply_translations(obj, translations):

    if isinstance(obj, dict):
        for k, v in obj.items():
            if should_skip_key(k):
                continue
            obj[k] = apply_translations(v, translations)

    elif isinstance(obj, list):
        return [apply_translations(i, translations) for i in obj]

    elif isinstance(obj, str):

        # Event?
        if "speak " in obj:
            speaks = extract_speak(obj)
            local = {s: translations.get(s, s) for s in speaks}
            return replace_speak(obj, local)

        if obj in translations:
            return translations[obj]

    return obj

# ===============================
# ПОИСК ВСЕХ JSON
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
        log_error(filepath, e)
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

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        list(tqdm(executor.map(process_file, files),
                  total=len(files),
                  desc="Общий прогресс (файлы)"))

    save_cache()
    print("Перевод завершён.")

if __name__ == "__main__":
    main()