import json
import os

CONFIG_FILE = "cameras.json"

def load_cameras():
    if not os.path.exists(CONFIG_FILE) or os.path.getsize(CONFIG_FILE) == 0:
        return []  # возвращаем пустой список, если файл пустой или отсутствует
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        print("⚠️ cameras.json повреждён — создаём новый")
        return []

def save_cameras(cameras):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cameras, f, ensure_ascii=False, indent=2) # говно а не реализация